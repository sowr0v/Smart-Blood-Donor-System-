import unittest
from _client import TestClient

from main import app, _generate_jwt, initialize_auth_database


class DonorPrivacyControlsTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        initialize_auth_database()
        self.donor_phone = "+8801712345678"
        self.donor_token = _generate_jwt(self.donor_phone, "donor")

    def tearDown(self):
        # Reset default privacy settings so subsequent test suites remain unaffected
        default_payload = {
            "allow_hospital_calls": True,
            "mask_public_phone": True,
            "public_directory": True,
            "show_badges": True,
            "share_direct_contact": False,
            "phone_visibility": "hospital_only",
        }
        self.client.post(
            "/api/v1/donor/privacy-settings",
            cookies={"access_token": self.donor_token},
            json=default_payload,
        )

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

    def test_update_donor_privacy_settings_and_enforcement(self):
        # 1. Update privacy controls: unlist from directory and enable masking
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

        # 2. Check seeker directory: donor with public_directory=False should be excluded
        seeker_resp = self.client.get("/api/v1/seeker/donors")
        self.assertEqual(seeker_resp.status_code, 200)
        seeker_donors = seeker_resp.json()["donors"]
        # dn-001 corresponds to +8801712345678 (Ayesha Rahman)
        self.assertFalse(any(d["id"] == "dn-001" for d in seeker_donors))

        # 3. Re-enable public directory but keep direct contact disabled
        enable_dir_payload = {
            "allow_hospital_calls": True,
            "mask_public_phone": True,
            "public_directory": True,
            "show_badges": True,
            "share_direct_contact": False,
            "phone_visibility": "hospital_only",
        }
        self.client.post(
            "/api/v1/donor/privacy-settings",
            cookies={"access_token": self.donor_token},
            json=enable_dir_payload,
        )
        seeker_resp2 = self.client.get("/api/v1/seeker/donors")
        seeker_donors2 = seeker_resp2.json()["donors"]
        ayesha = next((d for d in seeker_donors2 if d["id"] == "dn-001"), None)
        self.assertIsNotNone(ayesha)

        # Seeker cannot access direct contact when share_direct_contact is False
        seeker_token = _generate_jwt("+8801723456789", "seeker")
        denied_contact = self.client.post(
            "/api/v1/seeker/donors/dn-001/contact",
            cookies={"access_token": seeker_token},
        )
        self.assertEqual(denied_contact.status_code, 403)

        # 4. Enable direct contact: seeker can now retrieve contact
        allow_contact_payload = {
            "allow_hospital_calls": True,
            "mask_public_phone": False,
            "public_directory": True,
            "show_badges": True,
            "share_direct_contact": True,
            "phone_visibility": "public",
        }
        self.client.post(
            "/api/v1/donor/privacy-settings",
            cookies={"access_token": self.donor_token},
            json=allow_contact_payload,
        )
        allowed_contact = self.client.post(
            "/api/v1/seeker/donors/dn-001/contact",
            cookies={"access_token": seeker_token},
        )
        self.assertEqual(allowed_contact.status_code, 200)
        self.assertEqual(allowed_contact.json()["donor"]["phone"], self.donor_phone)

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
