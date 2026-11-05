import time
import unittest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from testing.driver_factory import create_chrome_driver, safe_click
from testing.server_manager import start_test_server, stop_test_server, BASE_URL

class TestModuleAuthRegistration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        start_test_server()
        cls.driver = create_chrome_driver(headless=True)

    @classmethod
    def tearDownClass(cls):
        if cls.driver:
            cls.driver.quit()

    def setUp(self):
        self.driver.delete_all_cookies()

    def test_tc_auth_01_individual_donor_registration(self):
        """TC-AUTH-01: Verify individual donor registration with valid details."""
        driver = self.driver
        unique_phone = f"+88017{int(time.time() * 1000) % 10000000:07d}"
        driver.get(f"{BASE_URL}/auth/register?role=donor")
        
        self.assertIn("Register", driver.title)
        
        # Fill individual registration form
        form = driver.find_element(By.ID, "form-individual")
        name_input = form.find_element(By.NAME, "name")
        phone_input = form.find_element(By.NAME, "phone")
        nid_input = form.find_element(By.NAME, "nid")
        bg_select = Select(form.find_element(By.NAME, "blood_group"))
        addr_input = form.find_element(By.NAME, "address")
        pw_input = form.find_element(By.NAME, "password")
        submit_btn = form.find_element(By.XPATH, ".//button[@type='submit']")

        name_input.send_keys("Test Donor Joy")
        phone_input.send_keys(unique_phone)
        nid_input.send_keys("19952691234567890")
        bg_select.select_by_visible_text("B+")
        addr_input.send_keys("Dhanmondi 32, Dhaka")
        pw_input.send_keys("DonorPass@123")
        safe_click(driver, submit_btn)

        # Expected: Success banner shown and redirect to /login
        WebDriverWait(driver, 8).until(
            lambda d: "/login" in d.current_url or d.find_element(By.ID, "registration-success-msg").is_displayed()
        )
        self.assertTrue("/login" in driver.current_url or "registration successful" in driver.page_source.lower())

    def test_tc_auth_02_organization_registration(self):
        """TC-AUTH-02: Verify institutional (Hospital / Blood Bank) registration."""
        driver = self.driver
        unique_phone = f"+88018{int(time.time() * 1000) % 10000000:07d}"
        driver.get(f"{BASE_URL}/auth/register?role=bank")
        
        # Switch to organization role if not selected
        role_select = Select(driver.find_element(By.ID, "role-select"))
        role_select.select_by_value("bank")
        time.sleep(0.5)

        form = driver.find_element(By.ID, "form-organization")
        org_name = form.find_element(By.NAME, "org_name")
        phone_input = form.find_element(By.NAME, "phone")
        manager_name = form.find_element(By.NAME, "manager_name")
        govt_reg = form.find_element(By.NAME, "govt_reg")
        addr_input = form.find_element(By.NAME, "address")
        pw_input = form.find_element(By.NAME, "password")
        loc_checkbox = form.find_element(By.NAME, "allow_location")
        if not loc_checkbox.is_selected():
            safe_click(driver, loc_checkbox)

        submit_btn = form.find_element(By.XPATH, ".//button[@type='submit']")

        org_name.send_keys("Apollo Central Blood Center")
        phone_input.send_keys(unique_phone)
        manager_name.send_keys("Dr. Mahbubur Rahman")
        govt_reg.send_keys("DGHS-BL-2026-99")
        addr_input.send_keys("Plot 81, Block E, Bashundhara, Dhaka")
        pw_input.send_keys("HospitalBank@123")
        safe_click(driver, submit_btn)

        WebDriverWait(driver, 8).until(
            lambda d: "/login" in d.current_url or d.find_element(By.ID, "registration-success-msg").is_displayed()
        )
        self.assertTrue("/login" in driver.current_url or "registration successful" in driver.page_source.lower())

    def test_tc_auth_03_reject_empty_required_fields(self):
        """TC-AUTH-03: Block incomplete registration attempt via form validation."""
        driver = self.driver
        driver.get(f"{BASE_URL}/auth/register?role=donor")
        
        form = driver.find_element(By.ID, "form-individual")
        submit_btn = form.find_element(By.XPATH, ".//button[@type='submit']")
        safe_click(driver, submit_btn)

        time.sleep(1)
        # Form submission blocked by client-side HTML5 validation, remains on register page
        self.assertIn("/auth/register", driver.current_url)

    def test_tc_auth_04_role_based_login_redirection(self):
        """TC-AUTH-04: Verify unified login routes donor, seeker, hospital, and admin to proper dashboards."""
        driver = self.driver

        test_roles = [
            ("+8801712345678", "secret123", False, "/donor/dashboard", "Donor"),
            ("+8801723456789", "match123", False, "/seeker/dashboard", "Seeker"),
            ("+8801734567890", "hospital123", False, "/hospital/dashboard", "Hospital"),
            ("+8801745678901", "admin123", True, "/admin/dashboard", "Admin"),
        ]

        for phone, password, is_admin, expected_path, role_name in test_roles:
            driver.delete_all_cookies()
            login_url = f"{BASE_URL}/login?admin_console=1" if is_admin else f"{BASE_URL}/login"
            driver.get(login_url)

            phone_input = driver.find_element(By.ID, "loginPhoneInput")
            pass_input = driver.find_element(By.ID, "loginPasswordInput")
            submit_btn = driver.find_element(By.ID, "loginSubmitBtn")

            phone_input.clear()
            phone_input.send_keys(phone)
            pass_input.clear()
            pass_input.send_keys(password)

            if is_admin:
                admin_check = driver.find_elements(By.ID, "adminConsoleCheckbox")
                if admin_check and not admin_check[0].is_selected():
                    safe_click(driver, admin_check[0])

            safe_click(driver, submit_btn)

            WebDriverWait(driver, 8).until(EC.url_contains(expected_path))
            self.assertIn(expected_path, driver.current_url, f"Failed for role {role_name}")

    def test_tc_auth_05_reject_invalid_credentials(self):
        """TC-AUTH-05: Reject invalid login attempt and display error."""
        driver = self.driver
        driver.get(f"{BASE_URL}/login")

        phone_input = driver.find_element(By.ID, "loginPhoneInput")
        pass_input = driver.find_element(By.ID, "loginPasswordInput")
        submit_btn = driver.find_element(By.ID, "loginSubmitBtn")

        phone_input.clear()
        phone_input.send_keys("+8801712345678")
        pass_input.clear()
        pass_input.send_keys("WrongPasswordXYZ")
        safe_click(driver, submit_btn)

        time.sleep(1)
        self.assertIn("/login", driver.current_url)
        self.assertTrue("invalid credentials" in driver.page_source.lower() or "alert" in driver.page_source.lower())

    def test_tc_auth_06_sms_otp_verification_page(self):
        """TC-AUTH-06: Verify SMS OTP Gateway verification page renders and processes OTP."""
        driver = self.driver
        driver.get(f"{BASE_URL}/otp-verification?phone=%2B8801712345678")
        
        self.assertIn("OTP Verification", driver.title)
        otp_inputs = driver.find_elements(By.CSS_SELECTOR, ".otp-inputs input")
        self.assertEqual(len(otp_inputs), 6, "Expected 6 OTP digit inputs")

        for idx, digit in enumerate("123456"):
            otp_inputs[idx].send_keys(digit)

        verify_btn = driver.find_element(By.ID, "verifyBtn")
        safe_click(driver, verify_btn)

        # Accept the success alert
        WebDriverWait(driver, 6).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        self.assertIn("OTP Verified Successfully", alert.text)
        alert.accept()

        WebDriverWait(driver, 6).until(EC.url_contains("/donor/dashboard"))
        self.assertIn("/donor/dashboard", driver.current_url)

    def test_tc_auth_07_unauthenticated_dashboard_redirects_to_login(self):
        """TC-AUTH-07: Unauthenticated access to role dashboards redirects to /login."""
        driver = self.driver
        protected_paths = [
            "/donor/dashboard",
            "/seeker/dashboard",
            "/hospital/dashboard",
            "/admin/dashboard",
        ]

        for path in protected_paths:
            driver.delete_all_cookies()
            driver.get(f"{BASE_URL}{path}")
            WebDriverWait(driver, 5).until(EC.url_contains("/login"))
            self.assertIn("/login", driver.current_url)

    def test_tc_auth_08_user_logout_invalidates_session(self):
        """TC-AUTH-08: Logging out clears session cookies and restricts dashboard access."""
        driver = self.driver
        # 1. Login
        driver.get(f"{BASE_URL}/login")
        driver.find_element(By.ID, "loginPhoneInput").send_keys("+8801712345678")
        driver.find_element(By.ID, "loginPasswordInput").send_keys("secret123")
        safe_click(driver, driver.find_element(By.ID, "loginSubmitBtn"))
        WebDriverWait(driver, 6).until(EC.url_contains("/donor/dashboard"))

        # 2. Click logout
        driver.get(f"{BASE_URL}/logout")
        WebDriverWait(driver, 6).until(EC.url_contains("/login"))

        # 3. Direct attempt to re-access dashboard should redirect to login
        driver.get(f"{BASE_URL}/donor/dashboard")
        WebDriverWait(driver, 6).until(EC.url_contains("/login"))
        self.assertIn("/login", driver.current_url)

if __name__ == "__main__":
    unittest.main()
