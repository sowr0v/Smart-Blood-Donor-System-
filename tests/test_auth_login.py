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
