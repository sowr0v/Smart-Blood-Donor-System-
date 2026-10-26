import unittest
from fastapi.testclient import TestClient
from main import app, _generate_jwt, USERS


class AdminUserManagementTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.admin_phone = "+8801745678901"
        self.admin_token = _generate_jwt(self.admin_phone, "admin")
        self.client.cookies.set("access_token", self.admin_token)

        self.donor_phone = "+8801712345678"
        self.donor_token = _generate_jwt(self.donor_phone, "donor")

    def test_unauthorized_user_cannot_access_admin_api(self):
        non_admin_client = TestClient(app)
        non_admin_client.cookies.set("access_token", self.donor_token)

        response = non_admin_client.get("/api/v1/admin/users")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Administrative privileges required", response.json()["detail"])

    def test_admin_dashboard_renders_for_admin(self):
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("User Management &amp; Role Control", response.text)
        self.assertIn("Security &amp; Administrative Audit Trail", response.text)

    def test_admin_can_search_and_list_users(self):
        response = self.client.get("/api/v1/admin/users")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIsInstance(data["users"], list)
        self.assertGreaterEqual(len(data["users"]), 1)
        self.assertIn("metrics", data)

        # Search test
        search_res = self.client.get("/api/v1/admin/users?query=Ayesha")
        self.assertEqual(search_res.status_code, 200)
        results = search_res.json()["users"]
        self.assertTrue(any("Ayesha" in u["name"] for u in results))

    def test_admin_can_view_single_user_dossier(self):
        response = self.client.get(f"/api/v1/admin/users/{self.donor_phone}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["user"]["phone"], self.donor_phone)
        self.assertIn("audit_history", data)

    def test_admin_can_modify_user_role_and_audit_is_recorded(self):
        # Update donor to seeker
        payload = {"role": "seeker", "reason": "User requested role switch"}
        response = self.client.put(f"/api/v1/admin/users/{self.donor_phone}/role", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["role"], "seeker")

        # Verify audit logs recorded this
        audit_res = self.client.get("/api/v1/admin/audit-logs")
        self.assertEqual(audit_res.status_code, 200)
        logs = audit_res.json()["logs"]
        role_logs = [l for l in logs if l["target_phone"] == self.donor_phone and l["action"] == "ROLE_MODIFIED"]
        self.assertTrue(len(role_logs) > 0)
        self.assertIn("User requested role switch", role_logs[0]["details"])

        # Switch back to donor
        restore_payload = {"role": "donor", "reason": "Restoring original test role"}
        self.client.put(f"/api/v1/admin/users/{self.donor_phone}/role", json=restore_payload)

    def test_admin_prevented_from_demoting_self(self):
        payload = {"role": "donor", "reason": "Accidental self demotion"}
        response = self.client.put(f"/api/v1/admin/users/{self.admin_phone}/role", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot demote their own account", response.json()["detail"])

    def test_admin_can_modify_status_and_suspended_user_cannot_login(self):
        target_phone = "+8801723456789"  # seeker Nabil
        
        # Suspend user
        suspend_payload = {"status": "suspended", "reason": "Policy violation test"}
        res = self.client.put(f"/api/v1/admin/users/{target_phone}/status", json=suspend_payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["user"]["status"], "suspended")

        # Try logging in with suspended user credentials
        login_client = TestClient(app)
        login_res = login_client.post(
            "/login",
            data={"phone_number": target_phone, "password": "match123"},
            follow_redirects=False,
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("suspended", login_res.text.lower())

        # Reactivate user
        activate_payload = {"status": "active", "reason": "Appeal accepted"}
        activate_res = self.client.put(f"/api/v1/admin/users/{target_phone}/status", json=activate_payload)
        self.assertEqual(activate_res.status_code, 200)
        self.assertEqual(activate_res.json()["user"]["status"], "active")

    def test_admin_prevented_from_suspending_self(self):
        payload = {"status": "suspended", "reason": "Lockout test"}
        response = self.client.put(f"/api/v1/admin/users/{self.admin_phone}/status", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot suspend their own account", response.json()["detail"])

    def test_admin_can_create_new_user(self):
        test_new_phone = "+8801755112233"
        payload = {
            "phone": test_new_phone,
            "name": "Audit New User",
            "role": "hospital",
            "blood_group": "B+",
            "status": "active",
            "password": "Password12345",
        }
        res = self.client.post("/api/v1/admin/users", json=payload)
        # 200 or 409 if already exists
        if res.status_code == 200:
            self.assertEqual(res.json()["status"], "success")
            self.assertEqual(res.json()["user"]["role"], "hospital")
        else:
            self.assertEqual(res.status_code, 409)
