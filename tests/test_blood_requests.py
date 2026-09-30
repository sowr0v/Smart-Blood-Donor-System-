import unittest
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from main import app


class BloodRequestsTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_homepage_contains_regional_request_feed_and_filter(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="blood-requests"', response.text)
        self.assertIn('id="blood-group-filter"', response.text)
        self.assertIn("Farmgate", response.text)

    def test_feed_api_filters_by_blood_group(self):
        response = self.client.get("/api/blood-requests", params={"blood_group": "A+"})
        self.assertEqual(response.status_code, 200)
        requests = response.json()
        self.assertTrue(requests)
        self.assertTrue(all(item["blood_group"] == "A+" for item in requests))
        self.assertTrue(all("contact_phone" not in item for item in requests))
        self.assertTrue(all({"hospital", "area", "units", "status", "posted_at"} <= item.keys() for item in requests))

    def test_invalid_session_cookie_cannot_open_contact_details(self):
        self.client.cookies.set("access_token", "not-a-valid-token")
        response = self.client.get("/requests/req-001/connect", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["location"].startswith("/login?next="))

    def test_connect_prompts_login_and_continues_after_authentication(self):
        response = self.client.get("/requests/req-001/connect", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        login_url = urlparse(response.headers["location"])
        self.assertEqual(login_url.path, "/login")
        next_url = parse_qs(login_url.query)["next"][0]

        login_page = self.client.get(response.headers["location"])
        self.assertEqual(login_page.status_code, 200)
        self.assertIn('name="next_url"', login_page.text)
        self.assertIn('/auth/register?role=donor', login_page.text)

        login_response = self.client.post(
            "/login",
            data={
                "phone_number": "+8801712345678",
                "password": "secret123",
                "next_url": next_url,
            },
            follow_redirects=False,
        )
        self.assertEqual(login_response.status_code, 303)
        self.assertEqual(login_response.headers["location"], next_url)

        contact_response = self.client.get(next_url)
        self.assertEqual(contact_response.status_code, 200)
        self.assertIn("Donor contact details", contact_response.text)
