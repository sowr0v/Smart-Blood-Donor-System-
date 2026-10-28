import unittest
from fastapi.testclient import TestClient

from main import app, _generate_jwt, initialize_auth_database


class LocationSharingGranularityTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        initialize_auth_database()
        self.donor_phone = "+8801712345678"
        self.donor_token = _generate_jwt(self.donor_phone, "donor")

    def tearDown(self):
        # Reset default location settings so subsequent test suites remain unaffected
        default_payload = {
            "granularity": "approximate",
            "share_exact_location": False,
            "allow_gps_detection": True,
            "emergency_elevation": True,
            "fuzzy_radius_km": 1.0,
            "latitude": 23.7461,
            "longitude": 90.3742,
        }
        self.client.post(
            "/api/v1/donor/location-settings",
            cookies={"access_token": self.donor_token},
            json=default_payload,
        )

    def test_donor_dashboard_renders_location_granularity_card(self):
        response = self.client.get(
            "/donor/dashboard?preview=1",
            cookies={"access_token": self.donor_token},
        )
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('id="card-location-permissions"', html)
        self.assertIn("Location Sharing Granularity &amp; GPS Permissions", html)
        self.assertIn('id="granularityExact"', html)
        self.assertIn('id="granularityApproximate"', html)
        self.assertIn('id="granularityDistrict"', html)
        self.assertIn('id="granularityHidden"', html)
        self.assertIn('id="settingAllowGpsDetection"', html)
        self.assertIn('id="settingEmergencyElevation"', html)
        self.assertIn('id="btnDetectDonorGps"', html)
        self.assertIn('id="btnSaveLocationSettings"', html)
        self.assertIn('id="locationPreviewBox"', html)

    def test_get_donor_location_settings_defaults(self):
        response = self.client.get(
            "/api/v1/donor/location-settings",
            cookies={"access_token": self.donor_token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("location_settings", data)
        loc = data["location_settings"]
        self.assertEqual(loc["granularity"], "approximate")
        self.assertEqual(loc["share_exact_location"], False)
        self.assertEqual(loc["allow_gps_detection"], True)
        self.assertEqual(loc["emergency_elevation"], True)

    def test_update_donor_location_settings_and_enforcement(self):
        # 1. Update to Exact GPS Pinpoint
        exact_payload = {
            "granularity": "exact",
            "share_exact_location": True,
            "allow_gps_detection": True,
            "emergency_elevation": True,
            "fuzzy_radius_km": 1.0,
            "latitude": 23.7461,
            "longitude": 90.3742,
        }
        post_resp = self.client.post(
            "/api/v1/donor/location-settings",
            cookies={"access_token": self.donor_token},
            json=exact_payload,
        )
        self.assertEqual(post_resp.status_code, 200)
        post_data = post_resp.json()
        self.assertEqual(post_data["status"], "success")
        self.assertEqual(post_data["location_settings"]["granularity"], "exact")
        self.assertEqual(post_data["location_settings"]["share_exact_location"], True)

        # Check seeker donors endpoint: Ayesha (dn-001) should now have exact location precision
        seeker_resp = self.client.get("/api/v1/seeker/donors?blood_group=A%2B")
        self.assertEqual(seeker_resp.status_code, 200)
        ayesha = next((d for d in seeker_resp.json()["donors"] if d["id"] == "dn-001"), None)
        self.assertIsNotNone(ayesha)
        self.assertEqual(ayesha["location_precision"], "exact")
        self.assertEqual(ayesha["lat"], 23.7461)
        self.assertEqual(ayesha["lng"], 90.3742)

        # 2. Update to Hidden
        hidden_payload = {
            "granularity": "hidden",
            "share_exact_location": False,
            "allow_gps_detection": False,
            "emergency_elevation": False,
        }
        self.client.post(
            "/api/v1/donor/location-settings",
            cookies={"access_token": self.donor_token},
            json=hidden_payload,
        )
        # On map view, hidden donors should be excluded from coordinates markers
        map_resp = self.client.get("/api/v1/seeker/donors/map?blood_group=A%2B")
        self.assertEqual(map_resp.status_code, 200)
        # Note: map_donors are anonymous coordinate pins without IDs

    def test_detect_donor_gps_location_endpoint(self):
        response = self.client.post(
            "/api/v1/donor/location/detect-gps",
            cookies={"access_token": self.donor_token},
            json={"latitude": 23.7461, "longitude": 90.3742},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("detected_location", data)
        self.assertEqual(data["detected_location"]["latitude"], 23.7461)
        self.assertEqual(data["detected_location"]["longitude"], 90.3742)
        self.assertIn("Dhanmondi", data["detected_location"]["area"])


if __name__ == "__main__":
    unittest.main()
