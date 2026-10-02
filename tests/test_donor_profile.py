import unittest
from fastapi.testclient import TestClient

from main import app, _generate_jwt


class DonorProfileTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_donor_profile_api_returns_profile(self):
        token = _generate_jwt("+8801712345678", "donor")
        response = self.client.get("/api/v1/donor/profile", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["profile"]["phone"], "+8801712345678")
        self.assertIn("blood_group", data["profile"])

    def test_donor_profile_update_validates_and_saves(self):
        token = _generate_jwt("+8801712345678", "donor")
        payload = {
            "name": "Ayesha Rahman",
            "phone": "+8801712345678",
            "email": "ayesha.rahman@example.com",
            "blood_group": "A+",
            "district": "Dhaka",
            "area": "Dhanmondi",
            "address": "House 18, Road 7, Dhanmondi",
            "last_donation": "2026-01-14",
            "medical_conditions": "No major medical issues",
            "medications": "None",
            "allergies": "Penicillin",
            "fitness_status": "Eligible",
        }
        response = self.client.post(
            "/api/v1/donor/profile",
            json=payload,
            cookies={"access_token": token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["profile"]["blood_group"], "A+")
        self.assertEqual(data["profile"]["area"], "Dhanmondi")

    def test_donor_profile_rejects_invalid_blood_group(self):
        token = _generate_jwt("+8801712345678", "donor")
        response = self.client.post(
            "/api/v1/donor/profile",
            json={
                "name": "Ayesha Rahman",
                "phone": "+8801712345678",
                "blood_group": "Z+",
                "district": "Dhaka",
                "area": "Dhanmondi",
                "address": "House 18, Road 7, Dhanmondi",
            },
            cookies={"access_token": token},
        )
        self.assertEqual(response.status_code, 422)
