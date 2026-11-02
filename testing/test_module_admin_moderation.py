import time
import unittest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from testing.driver_factory import create_chrome_driver, safe_click
from testing.server_manager import start_test_server, stop_test_server, BASE_URL

class TestModuleAdminModeration(unittest.TestCase):
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

    def _login_as_admin(self):
        driver = self.driver
        driver.get(f"{BASE_URL}/login?admin_console=1")
        phone_input = driver.find_element(By.ID, "loginPhoneInput")
        pass_input = driver.find_element(By.ID, "loginPasswordInput")
        phone_input.clear()
        phone_input.send_keys("+8801745678901")
        pass_input.clear()
        pass_input.send_keys("admin123")

        admin_checks = driver.find_elements(By.ID, "adminConsoleCheckbox")
        if admin_checks and not admin_checks[0].is_selected():
            safe_click(driver, admin_checks[0])

        safe_click(driver, driver.find_element(By.ID, "loginSubmitBtn"))
        WebDriverWait(driver, 8).until(EC.url_contains("/admin/dashboard"))

    def _switch_admin_tab(self, nav_id, section_id):
        driver = self.driver
        btn = driver.find_element(By.ID, nav_id)
        safe_click(driver, btn)
        WebDriverWait(driver, 6).until(
            lambda d: "active" in d.find_element(By.ID, section_id).get_attribute("class")
        )
        time.sleep(0.4)

    def test_tc_admin_01_analytics_kpi_dashboard(self):
        """TC-ADMIN-01: Admin login directs to master console with live analytics KPI counters."""
        self._login_as_admin()
        driver = self.driver

        self.assertIn("/admin/dashboard", driver.current_url)
        analytics_sec = driver.find_element(By.ID, "section-analytics")
        self.assertTrue(analytics_sec.is_displayed())
        self.assertIn("Platform Master Analytics", analytics_sec.text)

    def test_tc_admin_02_kyc_verification_queue(self):
        """TC-ADMIN-02: Admin can access Donor KYC verification approval queue."""
        self._login_as_admin()
        driver = self.driver

        self._switch_admin_tab("nav-item-kyc", "section-kyc")

        kyc_section = driver.find_element(By.ID, "section-kyc")
        self.assertTrue(kyc_section.is_displayed())
        table_body = driver.find_element(By.ID, "kycTableBody")
        self.assertIsNotNone(table_body)

    def test_tc_admin_03_user_management_and_role_control(self):
        """TC-ADMIN-03: Admin can view registered users and role assignment table."""
        self._login_as_admin()
        driver = self.driver

        self._switch_admin_tab("nav-item-users", "section-users")

        users_section = driver.find_element(By.ID, "section-users")
        self.assertTrue(users_section.is_displayed())
        users_table = driver.find_element(By.ID, "usersTableBody")
        self.assertIsNotNone(users_table)

    def test_tc_admin_04_requests_moderation_queue(self):
        """TC-ADMIN-04: Admin can review urgent blood requests and duplicate detection queues."""
        self._login_as_admin()
        driver = self.driver

        self._switch_admin_tab("nav-item-requests", "section-requests")

        requests_section = driver.find_element(By.ID, "section-requests")
        self.assertTrue(requests_section.is_displayed())
        mod_table = driver.find_element(By.ID, "moderationRequestsTableBody")
        self.assertIsNotNone(mod_table)

    def test_tc_admin_05_stock_oversight_and_map(self):
        """TC-ADMIN-05: Admin can inspect regional facility blood stocks and geographic availability."""
        self._login_as_admin()
        driver = self.driver

        self._switch_admin_tab("nav-item-stock", "section-stock")

        stock_section = driver.find_element(By.ID, "section-stock")
        self.assertTrue(stock_section.is_displayed())

    def test_tc_admin_06_non_admin_access_blocked(self):
        """TC-ADMIN-06: Strict RBAC prevents non-admin accounts from accessing administrative portal."""
        driver = self.driver
        # 1. Login as regular donor
        driver.get(f"{BASE_URL}/login")
        driver.find_element(By.ID, "loginPhoneInput").send_keys("+8801712345678")
        driver.find_element(By.ID, "loginPasswordInput").send_keys("secret123")
        safe_click(driver, driver.find_element(By.ID, "loginSubmitBtn"))
        WebDriverWait(driver, 8).until(EC.url_contains("/donor/dashboard"))

        # 2. Attempt unauthorized navigation to /admin/dashboard
        driver.get(f"{BASE_URL}/admin/dashboard")
        time.sleep(1)

        # Expected: Non-admin redirected to /admin/login gateway
        self.assertIn("/admin/login", driver.current_url)

if __name__ == "__main__":
    unittest.main()
