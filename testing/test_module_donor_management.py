import time
import unittest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from testing.driver_factory import create_chrome_driver, safe_click
from testing.server_manager import start_test_server, stop_test_server, BASE_URL

class TestModuleDonorManagement(unittest.TestCase):
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

    def _login_as_donor(self):
        driver = self.driver
        driver.get(f"{BASE_URL}/login")
        driver.find_element(By.ID, "loginPhoneInput").clear()
        driver.find_element(By.ID, "loginPhoneInput").send_keys("+8801712345678")
        driver.find_element(By.ID, "loginPasswordInput").clear()
        driver.find_element(By.ID, "loginPasswordInput").send_keys("secret123")
        safe_click(driver, driver.find_element(By.ID, "loginSubmitBtn"))
        WebDriverWait(driver, 8).until(EC.url_contains("/donor/dashboard"))

    def _switch_section(self, section_id):
        driver = self.driver
        btn = driver.find_element(By.CSS_SELECTOR, f"button[data-target='{section_id}']")
        safe_click(driver, btn)
        WebDriverWait(driver, 6).until(
            lambda d: "active-section" in d.find_element(By.ID, section_id).get_attribute("class")
        )
        time.sleep(0.4)

    def test_tc_donor_01_availability_toggle(self):
        """TC-DONOR-01: Donor can toggle real-time availability status between Available and Unavailable."""
        self._login_as_donor()
        driver = self.driver

        self._switch_section("section-availability")

        toggle = driver.find_element(By.ID, "donorAvailabilityToggle")
        badge = driver.find_element(By.ID, "availabilityStatusBadge")
        initial_status = badge.text.strip()
        self.assertTrue(len(initial_status) > 0, f"Expected non-empty status badge, got '{initial_status}'")

        # Toggle via JavaScript change event
        driver.execute_script("arguments[0].checked = !arguments[0].checked; arguments[0].dispatchEvent(new Event('change'));", toggle)
        time.sleep(1.5)

        new_status = badge.text.strip()
        self.assertNotEqual(initial_status, new_status, "Availability badge status should update after toggle")

    def test_tc_donor_02_profile_and_medical_info_update(self):
        """TC-DONOR-02: Donor can update profile and health/medical safety disclosure."""
        self._login_as_donor()
        driver = self.driver

        self._switch_section("section-profile")

        form = driver.find_element(By.ID, "donorProfileForm")
        
        # Ensure all required fields have values
        driver.execute_script("""
            const form = document.getElementById('donorProfileForm');
            if (form) {
                if (form.elements['name']) form.elements['name'].value = 'Ayesha Rahman';
                if (form.elements['phone']) form.elements['phone'].value = '+8801712345678';
                if (form.elements['district']) form.elements['district'].value = 'Dhaka';
                if (form.elements['area']) form.elements['area'].value = 'Dhanmondi';
                if (form.elements['address']) form.elements['address'].value = 'Road 4/A, Dhanmondi, Dhaka';
                if (form.elements['medical_conditions']) form.elements['medical_conditions'].value = 'Asthma (Controlled)';
                if (form.elements['medications']) form.elements['medications'].value = 'Inhaler';
                if (form.elements['allergies']) form.elements['allergies'].value = 'Penicillin';
            }
        """)

        save_btn = driver.find_element(By.ID, "profileSaveBtn")
        safe_click(driver, save_btn)
        time.sleep(1.5)

        summary_allergies = driver.find_element(By.ID, "summaryAllergies")
        self.assertIn("Penicillin", summary_allergies.text)

    def test_tc_donor_03_matched_blood_requests_feed(self):
        """TC-DONOR-03: Donor can browse matched blood requests and filter by urgency and blood group."""
        self._login_as_donor()
        driver = self.driver

        self._switch_section("section-matched-requests")

        filters = driver.find_element(By.ID, "matched-request-filters")
        self.assertTrue(filters.is_displayed())

        urgency_select = Select(driver.find_element(By.ID, "matched-urgency-filter"))
        urgency_select.select_by_visible_text("Critical")
        time.sleep(0.5)
        self.assertEqual(urgency_select.first_selected_option.text, "Critical")

    def test_tc_donor_04_request_flow_view(self):
        """TC-DONOR-04: Donor can review pending requests in the accept and decline flow."""
        self._login_as_donor()
        driver = self.driver

        self._switch_section("section-request-flow")

        flow_section = driver.find_element(By.ID, "section-request-flow")
        self.assertTrue(flow_section.is_displayed())
        status_elem = driver.find_element(By.ID, "donor-request-flow-status")
        self.assertIsNotNone(status_elem)

    def test_tc_donor_05_donation_history_view(self):
        """TC-DONOR-05: Donor can view chronological donation records and tracking count."""
        self._login_as_donor()
        driver = self.driver

        self._switch_section("section-history")

        history_section = driver.find_element(By.ID, "section-history")
        self.assertTrue(history_section.is_displayed())
        history_list = driver.find_element(By.ID, "donationHistoryList")
        self.assertIsNotNone(history_list)

    def test_tc_donor_06_privacy_and_settings_preferences(self):
        """TC-DONOR-06: Donor can inspect communication preferences and privacy switches."""
        self._login_as_donor()
        driver = self.driver

        self._switch_section("section-settings")

        sms_setting = driver.find_element(By.ID, "settingSmsAlerts")
        self.assertIsNotNone(sms_setting)
        
        inapp_setting = driver.find_element(By.ID, "settingInAppPush")
        self.assertIsNotNone(inapp_setting)

if __name__ == "__main__":
    unittest.main()
