import unittest
from _client import TestClient

from main import app, _generate_jwt
from admin_portal import initialize_admin_and_notification_database


class AdminSettingsSecurityTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        initialize_admin_and_notification_database()
        self.admin_token = _generate_jwt("+8801745678901", "admin")
        self.donor_token = _generate_jwt("+8801712345678", "donor")

    def test_admin_dashboard_renders_settings_section(self):
        response = self.client.get(
            "/admin/dashboard",
            cookies={"access_token": self.admin_token},
        )
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('id="section-settings"', html)
        self.assertIn('id="adminSettingsForm"', html)
        self.assertIn('id="setting2fa"', html)
        self.assertIn('id="settingSmsLock"', html)
        self.assertIn('id="settingAutoModeration"', html)
        self.assertIn('id="settingSessionTimeout"', html)
        self.assertIn('id="settingMaxOtp"', html)
        self.assertIn('id="settingSmsProvider"', html)
        self.assertIn('id="adminPasswordForm"', html)
        self.assertIn('id="adminCurrentPassword"', html)
        self.assertIn('id="adminNewPassword"', html)
        self.assertIn('id="adminConfirmPassword"', html)
        self.assertIn('id="auditLogsTableBody"', html)

    def test_get_admin_settings(self):
        response = self.client.get(
            "/api/v1/admin/settings",
            cookies={"access_token": self.admin_token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("settings", data)
        self.assertIn("rbac_matrix", data)
        self.assertIsInstance(data["rbac_matrix"], list)
        self.assertGreaterEqual(len(data["rbac_matrix"]), 4)

    def test_update_admin_settings(self):
        payload = {
            "two_factor_auth": True,
            "session_timeout_minutes": 30,
            "max_otp_attempts": 4,
            "emergency_broadcast_lock": True,
            "auto_moderation_enabled": True,
            "sms_gateway_provider": "Greenweb Direct Gateway",
        }
        response = self.client.post(
            "/api/v1/admin/settings",
            cookies={"access_token": self.admin_token},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")

        # Verify get settings reflects update
        get_resp = self.client.get(
            "/api/v1/admin/settings",
            cookies={"access_token": self.admin_token},
        )
        get_data = get_resp.json()
        self.assertEqual(get_data["settings"]["session_timeout_minutes"], 30)
        self.assertEqual(get_data["settings"]["max_otp_attempts"], 4)
        self.assertEqual(get_data["settings"]["emergency_broadcast_lock"], 1)
        self.assertEqual(get_data["settings"]["sms_gateway_provider"], "Greenweb Direct Gateway")

    def test_change_admin_password_validation(self):
        # Short password (< 6 chars)
        response = self.client.post(
            "/api/v1/admin/settings/password",
            cookies={"access_token": self.admin_token},
            json={"current_password": "admin", "new_password": "123"},
        )
        self.assertEqual(response.status_code, 422)

        # Valid password
        valid_resp = self.client.post(
            "/api/v1/admin/settings/password",
            cookies={"access_token": self.admin_token},
            json={"current_password": "admin", "new_password": "newadminpassword123"},
        )
        self.assertEqual(valid_resp.status_code, 200)
        self.assertEqual(valid_resp.json()["status"], "success")

    def test_get_audit_logs_and_export(self):
        # 1. Fetch audit logs
        logs_resp = self.client.get(
            "/api/v1/admin/audit-logs?limit=20",
            cookies={"access_token": self.admin_token},
        )
        self.assertEqual(logs_resp.status_code, 200)
        logs_data = logs_resp.json()
        self.assertEqual(logs_data["status"], "success")
        self.assertIn("logs", logs_data)
        self.assertIsInstance(logs_data["logs"], list)

        # 2. Export audit logs
        export_resp = self.client.get(
            "/api/v1/admin/audit-logs/export",
            cookies={"access_token": self.admin_token},
        )
        self.assertEqual(export_resp.status_code, 200)
        export_data = export_resp.json()
        self.assertIn("audit_trail", export_data)
        self.assertIn("export_timestamp", export_data)


if __name__ == "__main__":
    unittest.main()
