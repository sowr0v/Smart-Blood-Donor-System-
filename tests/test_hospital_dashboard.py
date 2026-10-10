import unittest
from fastapi.testclient import TestClient
from main import app, _generate_jwt


class HospitalBloodBankPortalTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        token = _generate_jwt("+8801734567890", "hospital")
        self.client.post("/api/v1/hospital/settings/reset", cookies={"access_token": token})

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

    def test_hospital_settings_section_renders_form_and_live_preview(self):
        token = _generate_jwt("+8801734567890", "hospital")
        response = self.client.get("/hospital/dashboard", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify section container and heading
        self.assertIn('id="section-hospital-settings"', html)
        self.assertIn("Hospital Portal Settings & Facility Profile", html)
        self.assertIn('id="facilitySettingsForm"', html)

        # Verify form inputs
        self.assertIn('id="facilityName"', html)
        self.assertIn('id="facilityType"', html)
        self.assertIn('id="facilityLicense"', html)
        self.assertIn('id="facilityDirectorName"', html)
        self.assertIn('id="facilityHotline"', html)
        self.assertIn('id="facilityAddress"', html)
        self.assertIn('id="facilityColdTemp"', html)
        self.assertIn('id="facilityChairs"', html)
        self.assertIn('id="facilityComponentChips"', html)

        # Verify toggles
        self.assertIn('id="toggleApheresis"', html)
        self.assertIn('id="toggleUltraFreezer"', html)
        self.assertIn('id="toggleNatScreening"', html)
        self.assertIn('id="toggleContinuousShift"', html)
        self.assertIn('id="toggleAutoSos"', html)
        self.assertIn('id="toggleInterFacility"', html)
        self.assertIn('id="toggleAudioSiren"', html)
        self.assertIn('id="toggleSmsAlerts"', html)
        self.assertIn('id="toggleDailyAudit"', html)
        self.assertIn('id="toggle2FA"', html)
        self.assertIn('id="toggleMaintenance"', html)

        # Verify Live preview card
        self.assertIn("Live Network Profile Card", html)
        self.assertIn('id="previewFacilityName"', html)
        self.assertIn('id="previewLicenseNo"', html)
        self.assertIn('id="previewDirector"', html)
        self.assertIn('id="previewColdTemp"', html)
        self.assertIn('id="btnSaveFacilitySettings"', html)
        self.assertIn('id="btnResetFacilitySettings"', html)
        self.assertIn('id="btnExportAccreditation"', html)

    def test_get_hospital_settings_api(self):
        token = _generate_jwt("+8801734567890", "hospital")
        resp = self.client.get("/api/v1/hospital/settings", cookies={"access_token": token})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        settings = data["settings"]
        self.assertIn("Dhaka General Hospital", settings["facility_name"])
        self.assertIn("license_no", settings)
        self.assertIn("components", settings)
        self.assertIn("cold_storage_temp", settings)

        # Blood Bank API returns blood bank defaults
        bank_token = _generate_jwt("+8801734567891", "bank")
        resp_bank = self.client.get("/api/v1/hospital/settings", cookies={"access_token": bank_token})
        self.assertEqual(resp_bank.status_code, 200)
        data_bank = resp_bank.json()
        self.assertIn("Red Crescent Blood Bank", data_bank["settings"]["facility_name"])

    def test_save_and_persist_hospital_settings_api(self):
        token = _generate_jwt("+8801734567890", "hospital")
        payload = {
            "phone": "+8801734567890",
            "facility_name": "Dhaka Central Super Specialized Hospital",
            "facility_type": "Tertiary Care Teaching Hospital",
            "license_no": "DGHS-SUPER-2026-99",
            "est_year": "1999",
            "director_name": "Prof. Dr. Shamsul Alam",
            "director_title": "Director General of Transfusion Services",
            "hotline": "+880 1711-002233",
            "email": "transfusion@superhospital.gov.bd",
            "address": "Pragati Sarani, Kuril, Dhaka",
            "division": "Dhaka",
            "area": "Kuril",
            "gps_coords": "23.8103° N, 90.4125° E",
            "landmark": "Near Kuril Flyover",
            "phlebotomy_chairs": 16,
            "components": ["PRBC", "Platelets", "FFP", "Cryo", "Whole Blood", "Apheresis"],
            "apheresis_active": True,
            "cold_storage_temp": "3.6°C",
            "ultra_freezer_active": True,
            "nat_screening": True,
            "continuous_shift": True,
            "low_stock_threshold": 10,
            "auto_sos_dispatch": True,
            "inter_facility_network": True,
            "audio_siren": True,
            "sms_doctor_alerts": True,
            "daily_inventory_audit": True,
            "two_factor_auth": True,
            "maintenance_mode": False,
        }

        # POST updated settings
        save_resp = self.client.post("/api/v1/hospital/settings", json=payload, cookies={"access_token": token})
        self.assertEqual(save_resp.status_code, 200)
        save_data = save_resp.json()
        self.assertEqual(save_data["status"], "success")
        self.assertEqual(save_data["settings"]["facility_name"], "Dhaka Central Super Specialized Hospital")
        self.assertEqual(save_data["settings"]["phlebotomy_chairs"], 16)

        # GET confirms updated settings
        get_resp = self.client.get("/api/v1/hospital/settings", cookies={"access_token": token})
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["settings"]["facility_name"], "Dhaka Central Super Specialized Hospital")
        self.assertEqual(get_resp.json()["settings"]["director_name"], "Prof. Dr. Shamsul Alam")

        # HTML dashboard reflects updated facility name
        dash_resp = self.client.get("/hospital/dashboard", cookies={"access_token": token})
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn("Dhaka Central Super Specialized Hospital", dash_resp.text)

    def test_reset_hospital_settings_api(self):
        token = _generate_jwt("+8801734567890", "hospital")
        reset_resp = self.client.post("/api/v1/hospital/settings/reset", cookies={"access_token": token})
        self.assertEqual(reset_resp.status_code, 200)
        data = reset_resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("DGHS certified baseline", data["message"])
        self.assertIn("Dhaka General Hospital", data["settings"]["facility_name"])

