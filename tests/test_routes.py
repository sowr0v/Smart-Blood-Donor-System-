import unittest

from fastapi.testclient import TestClient

from main import app


class LandingPageRoutesTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_homepage_contains_hero_ctas(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text.lower()
        self.assertIn("find blood", html)
        self.assertIn("become a donor", html)
        self.assertIn("100% free", html)

    def test_find_blood_route_exists(self):
        response = self.client.get("/find-blood")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Find Blood", response.text)

    def test_donor_registration_route_preselects_donor(self):
        response = self.client.get("/auth/register?role=donor")
        self.assertEqual(response.status_code, 200)
        self.assertIn("donor", response.text.lower())
        self.assertIn("register", response.text.lower())
