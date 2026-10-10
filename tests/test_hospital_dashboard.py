import unittest
from fastapi.testclient import TestClient
from main import app, _generate_jwt


class HospitalBloodBankPortalTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_unauthenticated_hospital_dashboard_redirects_to_login(self):
        response = self.client.get("/hospital/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/login", response.headers.get("location"))

    def test_hospital_login_redirects_to_hospital_dashboard(self):
        response = self.client.post(
            "/login",
            data={
                "phone_number": "+8801734567890",
                "password": "hospital123",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/hospital/dashboard")
        self.assertIn("access_token", response.cookies)

    def test_blood_bank_login_redirects_to_hospital_dashboard(self):
        response = self.client.post(
            "/login",
            data={
                "phone_number": "+8801734567891",
                "password": "bloodbank123",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/hospital/dashboard")
        self.assertIn("access_token", response.cookies)

    def test_hospital_registration_api_distinct_role(self):
        unique_phone = "+8801711998877"
        payload = {
            "name": "Ibn Sina Specialized Hospital",
            "phone": unique_phone,
            "password": "passHospital1",
            "role": "hospital",
            "address": "Dhanmondi, Dhaka",
        }
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["role"], "hospital")
        self.assertEqual(data["redirect_url"], "/login?registered=1")

        # Explicit login works and directs to hospital dashboard
        login_resp = self.client.post(
            "/login",
            data={"phone_number": unique_phone, "password": "passHospital1"},
            follow_redirects=False,
        )
        self.assertEqual(login_resp.status_code, 303)
        self.assertEqual(login_resp.headers.get("location"), "/hospital/dashboard")

    def test_blood_bank_registration_api_distinct_role(self):
        unique_phone = "+8801722887766"
        payload = {
            "name": "Sandhani National Blood Bank",
            "phone": unique_phone,
            "password": "passBloodBank1",
            "role": "bank",
            "address": "Dhaka Medical College Campus",
        }
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["role"], "bank")
        self.assertEqual(data["redirect_url"], "/login?registered=1")

        # Explicit login works and directs to hospital dashboard with bank role
        login_resp = self.client.post(
            "/login",
            data={"phone_number": unique_phone, "password": "passBloodBank1"},
            follow_redirects=False,
        )
        self.assertEqual(login_resp.status_code, 303)
        self.assertEqual(login_resp.headers.get("location"), "/hospital/dashboard")

    def test_hospital_dashboard_renders_all_six_sidebar_sections_for_hospital(self):
        token = _generate_jwt("+8801734567890", "hospital")
        response = self.client.get("/hospital/dashboard", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify role title and facility name
        self.assertIn("Hospital Portal", html)
        self.assertIn("Dhaka General Hospital", html)

        # Verify all 6 sidebar navigation buttons
        self.assertIn('id="nav-item-hospital-master"', html)
        self.assertIn('id="nav-item-donor-search"', html)
        self.assertIn('id="nav-item-stock-matrix"', html)
        self.assertIn('id="nav-item-stock-alerts"', html)
        self.assertIn('id="nav-item-blood-allocation"', html)
        self.assertIn('id="nav-item-hospital-settings"', html)

        # Verify all 6 corresponding content sections
        self.assertIn('id="section-hospital-master"', html)
        self.assertIn('id="section-donor-search"', html)
        self.assertIn('id="section-stock-matrix"', html)
        self.assertIn('id="section-stock-alerts"', html)
        self.assertIn('id="section-blood-allocation"', html)
        self.assertIn('id="section-hospital-settings"', html)

        # Verify sidebar labels match user requirement
        self.assertIn("Hospital Portal Master Dashboard", html)
        self.assertIn("Hospital Donor Search & Direct Outreach", html)
        self.assertIn("Blood Stock Inventory Matrix Management", html)
        self.assertIn("Low Blood Stock Alerts & Reorder Triggers", html)
        self.assertIn("Hospital Institutional Blood Request & Allocation", html)
        self.assertIn("Hospital Portal Settings & Facility Profile", html)

    def test_hospital_dashboard_renders_dynamic_role_for_blood_bank(self):
        token = _generate_jwt("+8801734567891", "bank")
        response = self.client.get("/hospital/dashboard", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Dynamic role name for blood bank
        self.assertIn("Blood Bank Portal", html)
        self.assertIn("Red Crescent Blood Bank", html)
        self.assertIn("Licensed Blood Center", html)

        # All 6 sections exist
        self.assertIn('id="section-hospital-master"', html)
        self.assertIn('id="section-donor-search"', html)
        self.assertIn('id="section-stock-matrix"', html)
        self.assertIn('id="section-stock-alerts"', html)
        self.assertIn('id="section-blood-allocation"', html)
        self.assertIn('id="section-hospital-settings"', html)

        # Dynamic section headings for blood bank
        self.assertIn("Blood Bank Portal Master Dashboard", html)
        self.assertIn("Blood Bank Donor Search & Direct Outreach", html)
        self.assertIn("Blood Bank Institutional Blood Request & Allocation", html)
        self.assertIn("Blood Bank Portal Settings & Facility Profile", html)

    def test_demo_query_param_renders_portal(self):
        resp_hosp = self.client.get("/hospital/dashboard?demo=1")
        self.assertEqual(resp_hosp.status_code, 200)
        self.assertIn("Hospital Portal", resp_hosp.text)

        resp_bank = self.client.get("/hospital/dashboard?demo=1&role=bank")
        self.assertEqual(resp_bank.status_code, 200)
        self.assertIn("Blood Bank Portal", resp_bank.text)

    def test_cross_role_redirection_with_hospital_and_bank(self):
        hosp_token = _generate_jwt("+8801734567890", "hospital")
        donor_token = _generate_jwt("+8801712345678", "donor")
        seeker_token = _generate_jwt("+8801723456789", "seeker")

        # Donor trying to access hospital dashboard -> redirected to donor dashboard
        resp1 = self.client.get("/hospital/dashboard", cookies={"access_token": donor_token}, follow_redirects=False)
        self.assertEqual(resp1.status_code, 303)
        self.assertEqual(resp1.headers.get("location"), "/donor/dashboard")

        # Seeker trying to access hospital dashboard -> redirected to seeker dashboard
        resp2 = self.client.get("/hospital/dashboard", cookies={"access_token": seeker_token}, follow_redirects=False)
        self.assertEqual(resp2.status_code, 303)
        self.assertEqual(resp2.headers.get("location"), "/seeker/dashboard")

        # Hospital trying to access donor dashboard -> redirected to hospital dashboard
        resp3 = self.client.get("/donor/dashboard", cookies={"access_token": hosp_token}, follow_redirects=False)
        self.assertEqual(resp3.status_code, 303)
        self.assertEqual(resp3.headers.get("location"), "/hospital/dashboard")

        # Hospital trying to access seeker dashboard -> redirected to hospital dashboard
        resp4 = self.client.get("/seeker/dashboard", cookies={"access_token": hosp_token}, follow_redirects=False)
        self.assertEqual(resp4.status_code, 303)
        self.assertEqual(resp4.headers.get("location"), "/hospital/dashboard")

    def test_auth_status_returns_hospital_dashboard_url(self):
        hosp_token = _generate_jwt("+8801734567890", "hospital")
        resp_hosp = self.client.get("/api/v1/auth/status", cookies={"access_token": hosp_token})
        self.assertEqual(resp_hosp.status_code, 200)
        data_hosp = resp_hosp.json()
        self.assertTrue(data_hosp["is_authenticated"])
        self.assertEqual(data_hosp["role"], "hospital")
        self.assertEqual(data_hosp["dashboard_url"], "/hospital/dashboard")

        bank_token = _generate_jwt("+8801734567891", "bank")
        resp_bank = self.client.get("/api/v1/auth/status", cookies={"access_token": bank_token})
        self.assertEqual(resp_bank.status_code, 200)
        data_bank = resp_bank.json()
        self.assertTrue(data_bank["is_authenticated"])
        self.assertEqual(data_bank["role"], "bank")
        self.assertEqual(data_bank["dashboard_url"], "/hospital/dashboard")

    def test_registration_page_uses_manager_name_not_manager_number(self):
        response = self.client.get("/auth/register")
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn("Manager Name", html)
        self.assertIn('name="manager_name"', html)
        self.assertNotIn("Manager Number", html)
        self.assertNotIn('name="manager_number"', html)

    def test_hospital_registration_stores_and_displays_manager_name(self):
        from main import _get_user_by_phone
        unique_phone = "+8801799112233"
        payload = {
            "name": "Apollo Specialized Care",
            "org_name": "Apollo Specialized Care",
            "phone": unique_phone,
            "password": "passApollo123",
            "role": "hospital",
            "address": "Bashundhara R/A, Dhaka",
            "govt_reg": "REG-HOSP-789",
            "manager_name": "Dr. Tariqul Anam",
        }
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 200)
        user_record = _get_user_by_phone(unique_phone)
        self.assertIsNotNone(user_record)
        self.assertEqual(user_record["manager_name"], "Dr. Tariqul Anam")
