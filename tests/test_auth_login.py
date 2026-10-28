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

    def test_donor_registration_does_not_auto_login(self):
        unique_phone = "+8801755554444"
        payload = {
            "name": "Kamal Uddin",
            "phone": unique_phone,
            "password": "donorpassword123",
            "role": "donor",
            "blood_group": "B+",
        }
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["redirect_url"], "/login?registered=1")
        self.assertNotIn("access_token", response.cookies)

        # Attempting to access donor dashboard directly fails/redirects because user is not auto-logged in
        dash_unauth = self.client.get("/donor/dashboard", follow_redirects=False)
        self.assertEqual(dash_unauth.status_code, 303)
        self.assertIn("/login", dash_unauth.headers.get("location"))

        # Explicit login works
        login_resp = self.client.post(
            "/login",
            data={
                "phone_number": unique_phone,
                "password": "donorpassword123",
            },
            follow_redirects=False,
        )
        self.assertEqual(login_resp.status_code, 303)
        self.assertEqual(login_resp.headers.get("location"), "/donor/dashboard")
        self.assertIn("access_token", login_resp.cookies)

    def test_login_page_renders_registration_success_message(self):
        response = self.client.get("/login?registered=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Registration successful!", response.text)
        self.assertNotIn("access_token", response.cookies)

    def test_seeker_navigating_to_home_maintains_login_state(self):
        # 1. Access seeker dashboard in demo/authenticated mode
        seeker_resp = self.client.get("/seeker/dashboard?demo=1")
        self.assertEqual(seeker_resp.status_code, 200)
        self.assertIn("access_token", seeker_resp.cookies)

        token = seeker_resp.cookies["access_token"]

        # 2. Navigate to Home (/) with the established seeker session
        home_resp = self.client.get("/", cookies={"access_token": token})
        self.assertEqual(home_resp.status_code, 200)
        # Should render logged-in nav actions, pointing to seeker dashboard, NOT logout/login
        self.assertIn("/seeker/dashboard", home_resp.text)
        self.assertIn("/logout", home_resp.text)

    def test_cross_role_dashboard_graceful_redirection(self):
        from main import _generate_jwt
        seeker_token = _generate_jwt("+8801723456789", "seeker")
        donor_token = _generate_jwt("+8801712345678", "donor")

        # Seeker visiting donor dashboard should be gracefully redirected to seeker dashboard, not kicked to login
        resp_seeker_to_donor = self.client.get("/donor/dashboard", cookies={"access_token": seeker_token}, follow_redirects=False)
        self.assertEqual(resp_seeker_to_donor.status_code, 303)
        self.assertEqual(resp_seeker_to_donor.headers.get("location"), "/seeker/dashboard")

        # Donor visiting seeker dashboard should be gracefully redirected to donor dashboard, not kicked to login
        resp_donor_to_seeker = self.client.get("/seeker/dashboard", cookies={"access_token": donor_token}, follow_redirects=False)
        self.assertEqual(resp_donor_to_seeker.status_code, 303)
        self.assertEqual(resp_donor_to_seeker.headers.get("location"), "/donor/dashboard")

    def test_quick_admin_query_param_auto_logs_in(self):
        response = self.client.get("/login?quick_admin=1", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/admin/dashboard")
        self.assertIn("access_token", response.cookies)

    def test_admin_login_with_blank_phone_and_admin_console(self):
        response = self.client.post(
            "/login",
            data={
                "phone_number": "",
                "password": "",
                "admin_console": "on",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/admin/dashboard")
        self.assertIn("access_token", response.cookies)

    def test_admin_login_with_alias_username_admin(self):
        response = self.client.post(
            "/login",
            data={
                "phone_number": "admin",
                "password": "",
                "admin_console": "",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/admin/dashboard")
        self.assertIn("access_token", response.cookies)

    def test_login_page_renders_quick_demo_buttons_and_prefill(self):
        response = self.client.get("/login?admin_console=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("1-Click Quick Demo Login", response.text)
        self.assertIn("+8801745678901", response.text)
        self.assertIn("admin123", response.text)

    def test_api_admin_login_with_alias_and_access_dashboard(self):
        response = self.client.post(
            "/api/v1/auth/login",
            json={"phone": "admin", "password": "admin123"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["role"], "admin")
        self.assertEqual(data["redirect_url"], "/admin/dashboard")

        # Check access to admin dashboard
        dash_response = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(dash_response.status_code, 200)
        self.assertIn("Platform Master Analytics", dash_response.text)

        # Check auth status endpoint
        status_resp = self.client.get("/api/v1/auth/status")
        self.assertEqual(status_resp.status_code, 200)
        self.assertTrue(status_resp.json()["is_authenticated"])
        self.assertEqual(status_resp.json()["role"], "admin")
        self.assertEqual(status_resp.json()["dashboard_url"], "/admin/dashboard")

    def test_api_admin_login_with_phone_and_access_dashboard(self):
        response = self.client.post(
            "/api/v1/auth/login",
            json={"phone": "+8801745678901", "password": "admin123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "admin")

        dash_response = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(dash_response.status_code, 200)

    def test_admin_gateway_page_renders_clean_security_interface(self):
        response = self.client.get("/admin/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Administrator Gateway", response.text)
        self.assertIn("TLS 1.3 256-Bit Encrypted", response.text)
        self.assertIn("adminIdentifierInput", response.text)
        self.assertIn("adminPasswordInput", response.text)
        self.assertIn("Evaluation &amp; Sandbox Access", response.text)

    def test_admin_gateway_login_with_alias_admin(self):
        response = self.client.post(
            "/admin/login",
            data={
                "admin_identifier": "admin",
                "password": "admin123",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/admin/dashboard")
        self.assertIn("access_token", response.cookies)

    def test_admin_gateway_login_with_phone_identifier(self):
        response = self.client.post(
            "/admin/login",
            data={
                "admin_identifier": "+8801745678901",
                "password": "admin123",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/admin/dashboard")
        self.assertIn("access_token", response.cookies)

    def test_admin_gateway_login_with_email_identifier(self):
        response = self.client.post(
            "/admin/login",
            data={
                "admin_identifier": "admin@sbds.org",
                "password": "admin123",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/admin/dashboard")
        self.assertIn("access_token", response.cookies)

    def test_admin_gateway_rejects_blank_password(self):
        response = self.client.post(
            "/admin/login",
            data={
                "admin_identifier": "admin",
                "password": "",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Master password is required", response.text)

    def test_admin_gateway_rejects_invalid_password(self):
        response = self.client.post(
            "/admin/login",
            data={
                "admin_identifier": "admin",
                "password": "wrongpassword123",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid administrative credentials", response.text)

    def test_admin_logout_redirects_to_admin_login(self):
        from main import _generate_jwt
        admin_token = _generate_jwt("+8801745678901", "admin")
        response = self.client.get("/logout", cookies={"access_token": admin_token}, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/admin/login?logged_out=1")

    def test_authenticated_admin_visiting_admin_login_redirects_to_dashboard(self):
        from main import _generate_jwt
        admin_token = _generate_jwt("+8801745678901", "admin")
        response = self.client.get("/admin/login", cookies={"access_token": admin_token}, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/admin/dashboard")





