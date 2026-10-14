import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
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
        self.assertIn('id="standardRequestForm"', html)
        self.assertIn('name="needed_at"', html)
        self.assertIn('id="standardRequestFeedback"', html)

        # 3. Create Emergency Blood Request
        self.assertIn("Create Emergency Blood Request", html)
        self.assertIn('id="section-emergency-request"', html)
        self.assertIn('id="nav-item-emergency-request"', html)
        self.assertIn('id="emergencyRequestForm"', html)
        self.assertIn('name="blood_group"', html)
        self.assertIn('name="district"', html)
        self.assertIn('name="urgency_level"', html)
        self.assertIn('id="emergencyRequestFeedback"', html)

        # 4. Nearby Donors Interactive Map View
        self.assertIn("Nearby Donors Interactive Map View", html)
        self.assertIn('id="section-nearby-map"', html)
        self.assertIn('id="nav-item-nearby-map"', html)

        # 5. Donor Directory Search & Proximity Filtering
        self.assertIn("Donor Directory Search &amp; Proximity Filtering", html)
        self.assertIn('id="section-donor-directory"', html)
        self.assertIn('id="nav-item-donor-directory"', html)
        self.assertIn('id="donorDirectoryGrid"', html)
        self.assertIn('id="dirBloodFilter"', html)

        # 6. Donor Public Profile & Credentials View
        self.assertIn("Donor Public Profile &amp; Credentials View", html)
        self.assertIn('id="section-donor-credentials"', html)
        self.assertIn('id="nav-item-donor-credentials"', html)
        self.assertIn('id="donorPublicProfile"', html)
        self.assertIn('class="donor-directory-grid" aria-live="polite"', html)
        self.assertNotIn('id="donorProfileBack"', html)

        # 7. Direct Contact Action (Call / WhatsApp CTA)
        self.assertIn("Direct Contact Action (Call / WhatsApp CTA)", html)
        self.assertIn('id="section-direct-contact"', html)
        self.assertIn('id="nav-item-direct-contact"', html)

        # 8. Real-Time In-App 1-on-1 Chat
        self.assertIn("Real-Time In-App 1-on-1 Chat", html)
        self.assertIn('id="section-seeker-chat"', html)
        self.assertIn('id="nav-item-seeker-chat"', html)
        self.assertIn('id="seekerChatMessages"', html)
        self.assertIn('id="seekerChatForm"', html)
        self.assertIn('id="seekerChatDonorSelect"', html)
        self.assertIn('id="seekerChatStart"', html)
        self.assertIn('id="seekerChatReport"', html)
        self.assertIn('id="seekerChatBlock"', html)

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
            "needed_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "contact_phone": "+8801723456789",
            "reason": "Scheduled Surgery",
        }
        token = _generate_jwt("+8801723456789", "seeker")
        response = self.client.post(
            "/api/v1/seeker/requests",
            json=payload,
            cookies={"access_token": token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["request"]["patient_name"], "Test Patient")
        self.assertEqual(data["request"]["blood_group"], "B+")
        self.assertFalse(data["request"]["is_emergency"])
        self.assertTrue(data["request"]["needed_at"])

        tracked = self.client.get("/api/v1/seeker/requests", cookies={"access_token": token})
        self.assertEqual(tracked.status_code, 200)
        saved_request = next(
            item for item in tracked.json()["requests"] if item["id"] == data["request"]["id"]
        )
        self.assertEqual(saved_request["needed_at"], data["request"]["needed_at"])
        self.assertEqual(saved_request["status"], "Active")

    def test_standard_blood_request_requires_seeker_session(self):
        response = self.client.post(
            "/api/v1/seeker/requests",
            json={
                "patient_name": "Test Patient",
                "blood_group": "B+",
                "hospital_name": "Test Hospital",
                "area": "Dhanmondi",
                "district": "Dhaka",
                "units": 1,
                "needed_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "contact_phone": "+8801723456789",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_standard_blood_request_rejects_past_required_time(self):
        payload = {
            "patient_name": "Test Patient",
            "blood_group": "B+",
            "hospital_name": "Test Hospital",
            "area": "Dhanmondi",
            "district": "Dhaka",
            "units": 1,
            "needed_at": "2000-01-01T12:00:00+06:00",
            "contact_phone": "+8801723456789",
        }
        token = _generate_jwt("+8801723456789", "seeker")
        response = self.client.post(
            "/api/v1/seeker/requests",
            json=payload,
            cookies={"access_token": token},
        )
        self.assertEqual(response.status_code, 422)

    def test_create_emergency_blood_broadcast_api(self):
        payload = {
            "patient_name": "Emergency Patient",
            "blood_group": "O-",
            "hospital_name": "DMCH ICU",
            "area": "Shahbagh",
            "district": "Dhaka",
            "units": 2,
            "urgency_level": "Code Red (Within 1 Hour)",
            "contact_phone": "+8801723456789",
        }
        token = _generate_jwt("+8801723456789", "seeker")
        cookies = {"access_token": token}
        with patch("main.sms_is_configured", return_value=False):
            response = self.client.post(
                "/api/v1/seeker/requests/emergency",
                json=payload,
                cookies=cookies,
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["broadcast_count"], data["notifications"]["matched_donors"])
        self.assertEqual(data["notifications"]["status"], "not_configured")
        self.assertTrue(data["request"]["is_emergency"])
        self.assertEqual(data["request"]["status"], "Active")
        self.assertEqual(data["request"]["units"], 2)

        tracked = self.client.get("/api/v1/seeker/requests", cookies=cookies)
        self.assertEqual(tracked.status_code, 200)
        saved_request = next(
            item for item in tracked.json()["requests"] if item["id"] == data["request"]["id"]
        )
        self.assertEqual(saved_request["urgency_level"], payload["urgency_level"])
        self.assertEqual(saved_request["status"], "Active")

    def test_emergency_blood_request_requires_seeker_session(self):
        response = self.client.post(
            "/api/v1/seeker/requests/emergency",
            json={
                "patient_name": "Emergency Patient",
                "blood_group": "O-",
                "hospital_name": "DMCH ICU",
                "area": "Shahbagh",
                "contact_phone": "+8801723456789",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_emergency_blood_request_validates_required_blood_group(self):
        token = _generate_jwt("+8801723456789", "seeker")
        response = self.client.post(
            "/api/v1/seeker/requests/emergency",
            cookies={"access_token": token},
            json={
                "patient_name": "Emergency Patient",
                "blood_group": "X+",
                "hospital_name": "DMCH ICU",
                "area": "Shahbagh",
                "contact_phone": "+8801723456789",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_seeker_donors_search_and_filter(self):
        response = self.client.get("/api/v1/seeker/donors?blood_group=A+&radius_km=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        for donor in data["donors"]:
            self.assertEqual(donor["blood_group"], "A+")
            self.assertLessEqual(donor["distance_km"], 10)

    def test_seeker_donor_list_and_detail_obscure_restricted_coordinates(self):
        list_response = self.client.get("/api/v1/seeker/donors?blood_group=A%2B")
        detail_response = self.client.get("/api/v1/seeker/donors/dn-001")

        self.assertEqual((list_response.json()["donors"][0]["lat"], list_response.json()["donors"][0]["lng"]), (23.75, 90.37))
        self.assertEqual((detail_response.json()["donor"]["lat"], detail_response.json()["donor"]["lng"]), (23.75, 90.37))

    def test_seeker_donor_map_filters_and_hides_restricted_location_details(self):
        donor_records = [
            {
                "id": "private-donor",
                "name": "Private Donor",
                "phone": "+8801700000000",
                "blood_group": "A+",
                "district": "Dhaka",
                "area": "Dhanmondi",
                "lat": 23.7461,
                "lng": 90.3742,
                "distance_km": 1.2,
                "is_available": True,
            },
            {
                "blood_group": "A+",
                "area": "Mirpur",
                "district": "Dhaka",
                "lat": 23.8,
                "lng": 90.36,
                "distance_km": 2,
                "is_available": False,
            },
            {
                "blood_group": "O+",
                "area": "Gulshan",
                "district": "Dhaka",
                "lat": 23.79,
                "lng": 90.42,
                "distance_km": 1,
                "is_available": True,
            },
        ]
        with patch("main.SEEKER_MOCK_DONORS", donor_records):
            response = self.client.get("/api/v1/seeker/donors/map?blood_group=A%2B&radius_km=5")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        donor = data["donors"][0]
        self.assertEqual(donor["blood_group"], "A+")
        self.assertEqual(donor["location_precision"], "approximate")
        self.assertEqual((donor["lat"], donor["lng"]), (23.75, 90.37))
        self.assertNotIn("name", donor)
        self.assertNotIn("phone", donor)
        self.assertNotIn("id", donor)

    def test_seeker_donor_map_returns_exact_location_only_with_explicit_sharing(self):
        donor_records = [{
            "blood_group": "O-",
            "area": "Dhanmondi",
            "district": "Dhaka",
            "lat": 23.7461,
            "lng": 90.3742,
            "distance_km": 1.2,
            "is_available": True,
            "share_exact_location": True,
        }]
        with patch("main.SEEKER_MOCK_DONORS", donor_records):
            response = self.client.get("/api/v1/seeker/donors/map")

        donor = response.json()["donors"][0]
        self.assertEqual(donor["location_precision"], "exact")
        self.assertEqual((donor["lat"], donor["lng"]), (23.7461, 90.3742))

    def test_seeker_donor_credentials_detail(self):
        response = self.client.get("/api/v1/seeker/donors/dn-001")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["donor"]["id"], "dn-001")
        self.assertEqual(data["donor"]["name"], "Ayesha Rahman")
        self.assertTrue(data["donor"]["is_verified"])
        self.assertEqual(data["donor"]["verification_status"], "verified")
        self.assertEqual(data["donor"]["blood_group"], "A+")
        self.assertTrue(data["donor"]["is_available"])
        self.assertEqual(data["donor"]["donation_count"], 8)
        for private_field in (
            "phone",
            "formatted_phone",
            "email",
            "address",
            "hemoglobin",
            "weight_bp",
            "screening",
            "medical_conditions",
            "reviews",
        ):
            self.assertNotIn(private_field, data["donor"])
        self.assertEqual((data["donor"]["lat"], data["donor"]["lng"]), (23.75, 90.37))

    def test_public_donor_profile_respects_name_and_history_privacy(self):
        donor = {
            "id": "private-donor",
            "name": "Private Name",
            "share_name": False,
            "public_identifier": "Donor 24",
            "blood_group": "O-",
            "area": "Mirpur",
            "district": "Dhaka",
            "is_available": False,
            "nid_verified": False,
            "total_donations": 4,
            "phone": "+8801700000000",
            "screening": "Private screening information",
        }
        with patch("main.SEEKER_MOCK_DONORS", [donor]):
            response = self.client.get("/api/v1/seeker/donors/private-donor")
            hidden_name_search = self.client.get(
                "/api/v1/seeker/donors",
                params={"query": "Private Name"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(hidden_name_search.json()["count"], 0)
        public_donor = response.json()["donor"]
        self.assertEqual(public_donor["name"], "Donor 24")
        self.assertFalse(public_donor["is_available"])
        self.assertEqual(public_donor["verification_status"], "not_verified")
        self.assertNotIn("donation_count", public_donor)
        self.assertNotIn("phone", public_donor)
        self.assertNotIn("screening", public_donor)

    def test_unknown_public_donor_profile_returns_not_found(self):
        response = self.client.get("/api/v1/seeker/donors/not-a-donor")
        self.assertEqual(response.status_code, 404)

    def test_public_donor_directory_does_not_expose_private_profile_fields(self):
        response = self.client.get("/api/v1/seeker/donors")
        self.assertEqual(response.status_code, 200)
        donor = response.json()["donors"][0]
        self.assertIn("name", donor)
        self.assertIn("blood_group", donor)
        self.assertIn("is_available", donor)
        self.assertIn("verification_status", donor)
        self.assertNotIn("phone", donor)
        self.assertNotIn("screening", donor)

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
        token = _generate_jwt("+8801723456789", "seeker")
        cookies = {"access_token": token}
        start_resp = self.client.post(
            "/api/v1/seeker/chat/conversations",
            json={"donor_id": "dn-001"},
            cookies=cookies,
        )
        self.assertEqual(start_resp.status_code, 200)
        self.assertEqual(start_resp.json()["thread"]["id"], "thread-ayesha")

        threads_resp = self.client.get("/api/v1/seeker/chat/threads", cookies=cookies)
        self.assertEqual(threads_resp.status_code, 200)
        threads = threads_resp.json()["threads"]
        self.assertGreaterEqual(len(threads), 1)

        send_resp = self.client.post(
            "/api/v1/seeker/chat/thread-ayesha/send",
            json={"text": "Hello Ayesha, please confirm your arrival time."},
            cookies=cookies,
        )
        self.assertEqual(send_resp.status_code, 200)
        data = send_resp.json()
        self.assertEqual(data["sent"]["text"], "Hello Ayesha, please confirm your arrival time.")
        self.assertTrue(data["sent"]["sent_at"])

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

    def test_seeker_settings_has_delete_account_danger_zone_and_modal(self):
        token = _generate_jwt("+8801723456789", "seeker")
        response = self.client.get("/seeker/dashboard", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify Danger Zone card exists in settings
        self.assertIn("Danger Zone: Delete Seeker Account", html)
        self.assertIn('id="dangerZoneSection"', html)
        self.assertIn('id="btnOpenDeleteAccountModal"', html)
        self.assertIn("Delete Account", html)

        # Verify Confirmation Modal elements
        self.assertIn('id="deleteAccountModal"', html)
        self.assertIn('id="deleteConfirmationInput"', html)
        self.assertIn('id="confirmDeleteAccountBtn"', html)
        self.assertIn('id="cancelDeleteAccountBtn"', html)

    def test_delete_seeker_account_api_flow(self):
        unique_phone = "+8801755554444"
        # Register new seeker
        reg_resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "name": "Delete Test Seeker",
                "phone": unique_phone,
                "password": "delpass1234",
                "role": "seeker",
            },
        )
        self.assertEqual(reg_resp.status_code, 200)

        # Generate seeker JWT token
        token = _generate_jwt(unique_phone, "seeker")

        # Call delete endpoint
        del_resp = self.client.delete("/api/v1/seeker/account", cookies={"access_token": token})
        self.assertEqual(del_resp.status_code, 200)
        data = del_resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("deleted", data["message"].lower())
        self.assertEqual(data["redirect_url"], "/login?account_deleted=1")

        # Verify redirected login page displays success banner
        login_view = self.client.get("/login?account_deleted=1")
        self.assertEqual(login_view.status_code, 200)
        self.assertIn("Your seeker account has been permanently deleted.", login_view.text)
