import unittest

from fastapi.testclient import TestClient

from main import app


class AuthenticationLoginTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_login_page_renders(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        html = response.text.lower()
        self.assertIn("phone number", html)
        self.assertIn("password", html)
        self.assertIn("admin console", html)

    def test_donor_login_redirects_to_dashboard(self):
        response = self.client.post(
            "/login",
            data={
                "phone_number": "+8801712345678",
                "password": "secret123",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/donor/dashboard")

    def test_admin_login_redirects_to_admin_dashboard(self):
        response = self.client.post(
            "/login",
            data={
                "phone_number": "+8801745678901",
                "password": "admin123",
                "admin_console": "on",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/admin/dashboard")

    def test_invalid_credentials_show_error(self):
        response = self.client.post(
            "/login",
            data={
                "phone_number": "+8801712345678",
                "password": "wrongpass",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invalid credentials", response.text)

    def test_donor_login_with_random_otp_redirects_to_dashboard(self):
        response = self.client.post(
            "/login",
            data={
                "phone_number": "+8801712345678",
                "otp": "492019",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/donor/dashboard")

    def test_otp_api_login_returns_success(self):
        response = self.client.post(
            "/api/v1/auth/otp-login",
            json={"phone": "+8801712345678", "otp": "998877"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("donor/dashboard", data["redirect_url"])

    def test_otp_verification_page_renders(self):
        response = self.client.get("/otp-verification")
        self.assertEqual(response.status_code, 200)
        self.assertIn("OTP Verification", response.text)

