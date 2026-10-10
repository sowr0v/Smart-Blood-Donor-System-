import unittest
from fastapi.testclient import TestClient

from main import app, _generate_jwt


class SeekerDashboardTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_unauthorized_dashboard_redirects_to_login(self):
        response = self.client.get("/seeker/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/login?next=/seeker/dashboard", response.headers.get("location", ""))

    def test_preview_mode_allows_seeker_dashboard_view(self):
        response = self.client.get("/seeker/dashboard?preview=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Blood Seeker Portal", response.text)

    def test_authenticated_seeker_can_access_dashboard_with_all_sidebar_sections(self):
        token = _generate_jwt("+8801723456789", "seeker")
        response = self.client.get("/seeker/dashboard", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text

        # 1. Blood Seeker Personal Dashboard
        self.assertIn("Blood Seeker Personal Dashboard", html)
        self.assertIn('id="section-seeker-dashboard"', html)
        self.assertIn('id="nav-item-seeker-dashboard"', html)

        # 2. Create Standard Blood Request
        self.assertIn("Create Standard Blood Request", html)
        self.assertIn('id="section-standard-request"', html)
        self.assertIn('id="nav-item-standard-request"', html)

        # 3. Create Emergency Blood Request
        self.assertIn("Create Emergency Blood Request", html)
        self.assertIn('id="section-emergency-request"', html)
        self.assertIn('id="nav-item-emergency-request"', html)

        # 4. Nearby Donors Interactive Map View
        self.assertIn("Nearby Donors Interactive Map View", html)
        self.assertIn('id="section-nearby-map"', html)
        self.assertIn('id="nav-item-nearby-map"', html)

        # 5. Donor Directory Search & Proximity Filtering
        self.assertIn("Donor Directory Search &amp; Proximity Filtering", html)
        self.assertIn('id="section-donor-directory"', html)
        self.assertIn('id="nav-item-donor-directory"', html)

        # 6. Donor Public Profile & Credentials View
        self.assertIn("Donor Public Profile &amp; Credentials View", html)
        self.assertIn('id="section-donor-credentials"', html)
        self.assertIn('id="nav-item-donor-credentials"', html)

        # 7. Direct Contact Action (Call / WhatsApp CTA)
        self.assertIn("Direct Contact Action (Call / WhatsApp CTA)", html)
        self.assertIn('id="section-direct-contact"', html)
        self.assertIn('id="nav-item-direct-contact"', html)

        # 8. Real-Time In-App 1-on-1 Chat
        self.assertIn("Real-Time In-App 1-on-1 Chat", html)
        self.assertIn('id="section-seeker-chat"', html)
        self.assertIn('id="nav-item-seeker-chat"', html)

        # 9. Seeker Portal Settings & Preferences
        self.assertIn("Seeker Portal Settings &amp; Preferences", html)
        self.assertIn('id="section-seeker-settings"', html)
        self.assertIn('id="nav-item-seeker-settings"', html)

    def test_create_standard_blood_request_api(self):
        payload = {
            "patient_name": "Test Patient",
            "blood_group": "B+",
            "hospital_name": "Test Hospital",
            "area": "Dhanmondi",
            "district": "Dhaka",
            "units": 2,
            "contact_phone": "+8801723456789",
            "reason": "Scheduled Surgery",
            "is_emergency": False,
        }
        response = self.client.post("/api/v1/seeker/requests", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["request"]["patient_name"], "Test Patient")
        self.assertEqual(data["request"]["blood_group"], "B+")

    def test_create_emergency_blood_broadcast_api(self):
        payload = {
            "patient_name": "Emergency Patient",
            "blood_group": "O-",
            "hospital_name": "DMCH ICU",
            "area": "Shahbagh",
            "urgency_level": "Code Red (Within 1 Hour)",
            "contact_phone": "+8801723456789",
        }
        response = self.client.post("/api/v1/seeker/requests/emergency", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["broadcast_count"], 18)
        self.assertTrue(data["request"]["is_emergency"])

    def test_seeker_donors_search_and_filter(self):
        response = self.client.get("/api/v1/seeker/donors?blood_group=A+&radius_km=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        for donor in data["donors"]:
            self.assertEqual(donor["blood_group"], "A+")
            self.assertLessEqual(donor["distance_km"], 10)

    def test_seeker_donor_credentials_detail(self):
        response = self.client.get("/api/v1/seeker/donors/dn-001")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["donor"]["id"], "dn-001")
        self.assertEqual(data["donor"]["name"], "Ayesha Rahman")
        self.assertTrue(data["donor"]["nid_verified"])
        self.assertIn("Hepatitis", data["donor"]["screening"])

    def test_seeker_contact_log_flow(self):
        post_resp = self.client.post(
            "/api/v1/seeker/contact/log",
            json={
                "donor_name": "Tanvir Ahmed",
                "donor_phone": "+8801711223344",
                "blood_group": "O+",
                "contact_type": "call",
                "notes": "Direct call from speed dial",
            },
        )
        self.assertEqual(post_resp.status_code, 200)
        get_resp = self.client.get("/api/v1/seeker/contact/logs")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()
        self.assertGreaterEqual(data["count"], 1)

    def test_seeker_chat_thread_and_send(self):
        threads_resp = self.client.get("/api/v1/seeker/chat/threads")
        self.assertEqual(threads_resp.status_code, 200)
        threads = threads_resp.json()["threads"]
        self.assertGreaterEqual(len(threads), 2)

        send_resp = self.client.post(
            "/api/v1/seeker/chat/thread-ayesha/send",
            json={"text": "Hello Ayesha, please confirm your arrival time."},
        )
        self.assertEqual(send_resp.status_code, 200)
        data = send_resp.json()
        self.assertEqual(data["sent"]["text"], "Hello Ayesha, please confirm your arrival time.")
        self.assertIn("reply", data)

    def test_seeker_settings_save_and_fetch(self):
        save_resp = self.client.post(
            "/api/v1/seeker/settings",
            json={
                "full_name": "Nabil Hasan Updated",
                "phone": "+8801723456789",
                "default_hospital": "United Hospital",
                "sms_alerts": True,
                "push_alerts": True,
                "audio_siren": True,
                "default_radius": "20",
            },
        )
        self.assertEqual(save_resp.status_code, 200)
        self.assertEqual(save_resp.json()["settings"]["default_hospital"], "United Hospital")

        token = _generate_jwt("+8801723456789", "seeker")
        get_resp = self.client.get("/api/v1/seeker/settings", cookies={"access_token": token})
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["settings"]["full_name"], "Nabil Hasan Updated")

    def test_seeker_registration_route_preselects_seeker(self):
        response = self.client.get("/auth/register?role=seeker")
        self.assertEqual(response.status_code, 200)
        self.assertIn("seeker", response.text.lower())
        self.assertIn("register as a blood seeker", response.text.lower())

    def test_api_seeker_registration_links_to_dashboard(self):
        unique_phone = "+8801799998888"
        payload = {
            "name": "Sharmin Sultana",
            "phone": unique_phone,
            "password": "pass1234",
            "role": "seeker",
            "nid": "1990123456789",
            "blood_group": "AB+",
            "address": "Banani, Dhaka",
        }
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["role"], "seeker")
        self.assertEqual(data["redirect_url"], "/login?registered=1")
        self.assertNotIn("access_token", response.cookies)

        # Confirm user can log in explicitly via /login
        login_resp = self.client.post(
            "/login",
            data={
                "phone_number": unique_phone,
                "password": "pass1234",
            },
            follow_redirects=False,
        )
        self.assertEqual(login_resp.status_code, 303)
        self.assertEqual(login_resp.headers.get("location"), "/seeker/dashboard")
        self.assertIn("access_token", login_resp.cookies)

        dash_resp = self.client.get("/seeker/dashboard", cookies={"access_token": login_resp.cookies["access_token"]})
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn("Sharmin Sultana", dash_resp.text)
        self.assertIn("Blood Seeker Personal Dashboard", dash_resp.text)

    def test_form_seeker_registration_redirects_to_login(self):
        unique_phone = "+8801788887777"
        response = self.client.post(
            "/auth/register",
            data={
                "name": "Rakib Hasan",
                "phone": unique_phone,
                "password": "pass5678",
                "role": "seeker",
                "blood_group": "O+",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/login?registered=1")
        self.assertNotIn("access_token", response.cookies)

    def test_registered_seeker_login_redirects_to_seeker_dashboard_not_donor(self):
        unique_phone = "+8801766665555"
        # 1. Register as seeker
        reg_resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "name": "Mahir Seeker",
                "phone": unique_phone,
                "password": "seekerpass123",
                "role": "seeker",
            },
        )
        self.assertEqual(reg_resp.status_code, 200)

        # 2. Log in through /login form
        login_resp = self.client.post(
            "/login",
            data={
                "phone_number": unique_phone,
                "password": "seekerpass123",
            },
            follow_redirects=False,
        )
        self.assertEqual(login_resp.status_code, 303)
        self.assertEqual(login_resp.headers.get("location"), "/seeker/dashboard")
        self.assertNotEqual(login_resp.headers.get("location"), "/donor/dashboard")
