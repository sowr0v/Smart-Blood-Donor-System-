import unittest
from fastapi.testclient import TestClient

from main import app, _generate_jwt


class DonorDashboardTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_unauthorized_dashboard_redirects_to_login(self):
        response = self.client.get("/donor/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/login?next=/donor/dashboard", response.headers.get("location", ""))

    def test_preview_mode_allows_dashboard_view(self):
        response = self.client.get("/donor/dashboard?preview=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Donor Personal Dashboard", response.text)

    def test_authenticated_donor_can_access_dashboard(self):
        token = _generate_jwt("+8801712345678", "donor")
        response = self.client.get("/donor/dashboard", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify all 9 required sidebar items
        self.assertIn("Donor Availability", html)
        self.assertIn("Donor Profile & Medical Info", html)
        self.assertIn("Donation History", html)
        self.assertIn("Matched Blood Requests", html)
        self.assertIn("Accept & Decline Flow", html)
        self.assertIn("Request Details & Directions", html)
        self.assertIn("Donor In-App Chat", html)
        self.assertIn("Donor Reviews", html)
        self.assertIn("Settings & Preferences", html)

    def test_donor_availability_api(self):
        response = self.client.post(
            "/api/v1/donor/availability",
            json={"is_available": True, "radius_km": 15, "preferred_zones": ["Dhanmondi"]},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["is_available"])
        self.assertEqual(data["radius_km"], 15)

    def test_donor_respond_request_api(self):
        response = self.client.post(
            "/api/v1/donor/requests/req-001/respond",
            json={"action": "accept", "eta": "30 mins", "note": "On the way"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"], "accept")

    def test_logout_redirects_to_login(self):
        response = self.client.get("/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/login")

    def test_logged_in_user_visiting_home_shows_dashboard_and_logout(self):
        token = _generate_jwt("+8801712345678", "donor")
        response = self.client.get("/", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Dashboard", response.text)
        self.assertIn("Logout", response.text)

    def test_auth_status_api(self):
        token = _generate_jwt("+8801712345678", "donor")
        response = self.client.get("/api/v1/auth/status", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_authenticated"])
        self.assertEqual(data["role"], "donor")

