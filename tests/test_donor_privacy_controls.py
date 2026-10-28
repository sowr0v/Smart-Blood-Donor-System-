import unittest
from fastapi.testclient import TestClient

from main import app, _generate_jwt, initialize_auth_database


class DonorPrivacyControlsTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        initialize_auth_database()
        self.donor_phone = "+8801712345678"
        self.donor_token = _generate_jwt(self.donor_phone, "donor")

    def test_donor_dashboard_renders_privacy_controls_card(self):
        response = self.client.get(
            "/donor/dashboard?preview=1",
            cookies={"access_token": self.donor_token},
        )
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('id="card-privacy-controls"', html)
        self.assertIn("Profile Visibility &amp; Contact Privacy Controls", html)
        self.assertIn('id="settingAllowHospitalCall"', html)
        self.assertIn('id="settingMaskPublicPhone"', html)
        self.assertIn('id="settingPublicDirectory"', html)
        self.assertIn('id="settingShowBadges"', html)
        self.assertIn('id="settingShareDirectContact"', html)
        self.assertIn('id="privacyPreviewBox"', html)
        self.assertIn('id="btnSavePrivacyControls"', html)

    def test_get_donor_privacy_settings(self):
        response = self.client.get(
            "/api/v1/donor/privacy-settings",
            cookies={"access_token": self.donor_token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("privacy_controls", data)
        p = data["privacy_controls"]
        self.assertIn("allow_hospital_calls", p)
        self.assertIn("mask_public_phone", p)
        self.assertIn("public_directory", p)
        self.assertIn("show_badges", p)
        self.assertIn("share_direct_contact", p)

    def test_update_donor_privacy_settings(self):
        payload = {
            "allow_hospital_calls": False,
            "mask_public_phone": True,
            "public_directory": False,
            "show_badges": False,
            "share_direct_contact": True,
            "phone_visibility": "hidden",
        }
        response = self.client.post(
            "/api/v1/donor/privacy-settings",
            cookies={"access_token": self.donor_token},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["privacy_controls"]["allow_hospital_calls"], False)
        self.assertEqual(data["privacy_controls"]["public_directory"], False)
        self.assertEqual(data["privacy_controls"]["show_badges"], False)
        self.assertEqual(data["privacy_controls"]["share_direct_contact"], True)

        # Verify persistent read
        get_resp = self.client.get(
            "/api/v1/donor/privacy-settings",
            cookies={"access_token": self.donor_token},
        )
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertEqual(get_data["privacy_controls"]["public_directory"], False)
        self.assertEqual(get_data["privacy_controls"]["allow_hospital_calls"], False)

    def test_donor_settings_includes_privacy(self):
        response = self.client.get(
            "/api/v1/donor/settings",
            cookies={"access_token": self.donor_token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("settings", data)
        self.assertIn("privacy_controls", data)


if __name__ == "__main__":
    unittest.main()
