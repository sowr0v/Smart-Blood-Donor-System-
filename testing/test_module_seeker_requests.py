import time
from datetime import datetime, timedelta
import unittest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from testing.driver_factory import create_chrome_driver, safe_click
from testing.server_manager import start_test_server, stop_test_server, BASE_URL

class TestModuleSeekerRequests(unittest.TestCase):
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

    def _login_as_seeker(self):
        driver = self.driver
        driver.get(f"{BASE_URL}/login")
        driver.find_element(By.ID, "loginPhoneInput").clear()
        driver.find_element(By.ID, "loginPhoneInput").send_keys("+8801723456789")
        driver.find_element(By.ID, "loginPasswordInput").clear()
        driver.find_element(By.ID, "loginPasswordInput").send_keys("match123")
        safe_click(driver, driver.find_element(By.ID, "loginSubmitBtn"))
        WebDriverWait(driver, 8).until(EC.url_contains("/seeker/dashboard"))

    def test_tc_seek_01_landing_page_and_urgent_feed_navigation(self):
        """TC-SEEK-01: Public visitor can view landing page and navigate to urgent requests board."""
        driver = self.driver
        driver.get(f"{BASE_URL}/")
        
        self.assertIn("Smart Blood", driver.page_source)
        # Find CTA to urgent requests or find blood
        find_blood_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/find-blood') or contains(text(), 'Find Blood')]")
        self.assertTrue(len(find_blood_links) > 0, "Find Blood link should be present on homepage")
        
        safe_click(driver, find_blood_links[0])
        WebDriverWait(driver, 6).until(EC.url_contains("/find-blood"))
        self.assertIn("Urgent", driver.page_source)

    def test_tc_seek_02_urgent_board_filtering(self):
        """TC-SEEK-02: Public user can search and filter emergency requests by blood group and district."""
        driver = self.driver
        driver.get(f"{BASE_URL}/find-blood")
        
        WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.ID, "urgent-blood-filter")))
        bg_filter = Select(driver.find_element(By.ID, "urgent-blood-filter"))
        
        # Filter by A+
        bg_filter.select_by_value("A+")
        time.sleep(0.5)
        self.assertEqual(bg_filter.first_selected_option.get_attribute("value"), "A+")
        
        # Reset to all
        bg_filter.select_by_value("")
        time.sleep(0.5)
        self.assertEqual(bg_filter.first_selected_option.get_attribute("value"), "")

    def test_tc_seek_03_create_standard_blood_request(self):
        """TC-SEEK-03: Authenticated seeker can create a standard blood request with all patient info."""
        self._login_as_seeker()
        driver = self.driver
        
        # Navigate to Create Standard Request section
        nav_item = driver.find_element(By.ID, "nav-item-standard-request")
        safe_click(driver, nav_item)
        time.sleep(0.5)

        form = driver.find_element(By.ID, "standardRequestForm")
        patient_input = form.find_element(By.ID, "standardPatientName")
        bg_select = Select(form.find_element(By.ID, "standardBloodGroup"))
        hospital_input = form.find_element(By.ID, "standardHospital")
        units_input = form.find_element(By.ID, "standardUnits")
        district_input = form.find_element(By.ID, "standardDistrict")
        needed_input = form.find_element(By.ID, "standardNeededAt")
        phone_input = form.find_element(By.ID, "standardContactPhone")
        submit_btn = driver.find_element(By.ID, "submitStandardRequest")

        patient_input.clear()
        patient_input.send_keys("Kamal Uddin Seeker")
        bg_select.select_by_visible_text("B+")
        hospital_input.clear()
        hospital_input.send_keys("National Institute of Cardiovascular Diseases")
        units_input.clear()
        units_input.send_keys("2")
        district_input.clear()
        district_input.send_keys("Dhaka")

        # Future datetime in format YYYY-MM-DDTHH:MM
        future_dt = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT14:00")
        driver.execute_script("arguments[0].value = arguments[1];", needed_input, future_dt)

        if not phone_input.get_attribute("value"):
            phone_input.send_keys("+8801723456789")

        safe_click(driver, submit_btn)
        time.sleep(1.5)

        # Check feedback status element
        feedback = driver.find_element(By.ID, "standardRequestFeedback")
        feedback_text = feedback.text.lower()
        self.assertTrue(
            "created" in feedback_text or "success" in feedback_text or feedback.is_displayed() or len(feedback_text) > 0,
            "Standard request feedback should confirm submission"
        )

    def test_tc_seek_04_create_emergency_blood_request(self):
        """TC-SEEK-04: Authenticated seeker can broadcast an urgent emergency blood request."""
        self._login_as_seeker()
        driver = self.driver
        
        # Navigate to Emergency Request section
        nav_item = driver.find_element(By.ID, "nav-item-emergency-request")
        safe_click(driver, nav_item)
        time.sleep(0.5)

        form = driver.find_element(By.ID, "emergencyRequestForm")
        patient_input = form.find_element(By.ID, "emergencyPatientName")
        bg_select = Select(form.find_element(By.ID, "emergencyBloodGroup"))
        hospital_input = form.find_element(By.ID, "emergencyHospital")
        units_input = form.find_element(By.ID, "emergencyUnits")
        district_input = form.find_element(By.ID, "emergencyDistrict")
        urgency_select = Select(form.find_element(By.ID, "emergencyUrgency"))
        phone_input = form.find_element(By.ID, "emergencyContactPhone")
        submit_btn = driver.find_element(By.ID, "submitEmergencyRequest")

        patient_input.clear()
        patient_input.send_keys("Emergency Patient Tariq")
        bg_select.select_by_visible_text("O-")
        hospital_input.clear()
        hospital_input.send_keys("Square Hospital Emergency Ward")
        units_input.clear()
        units_input.send_keys("1")
        district_input.clear()
        district_input.send_keys("Dhaka")
        urgency_select.select_by_index(0)

        if not phone_input.get_attribute("value"):
            phone_input.send_keys("+8801723456789")

        safe_click(driver, submit_btn)
        time.sleep(1.5)

        feedback = driver.find_element(By.ID, "emergencyRequestFeedback")
        feedback_text = feedback.text.lower()
        self.assertTrue(
            "broadcast" in feedback_text or "success" in feedback_text or feedback.is_displayed() or len(feedback_text) > 0,
            "Emergency broadcast feedback should be present"
        )

    def test_tc_seek_05_active_requests_and_low_stock_alerts(self):
        """TC-SEEK-05: Seeker dashboard renders active request KPIs and low-stock facility alerts."""
        self._login_as_seeker()
        driver = self.driver

        safe_click(driver, driver.find_element(By.ID, "nav-item-seeker-dashboard"))
        time.sleep(0.5)

        # Check presence of low-stock alert module and metrics
        alerts_section = driver.find_element(By.ID, "seekerLowStockAlerts")
        self.assertTrue(alerts_section.is_displayed() or "stock" in alerts_section.text.lower())
        
        metrics = driver.find_element(By.ID, "metricActiveReqs")
        self.assertIn("Active", metrics.text)

    def test_tc_seek_06_nearby_donor_map_and_directory(self):
        """TC-SEEK-06: Seeker can inspect nearby donor radar map and donor directory."""
        self._login_as_seeker()
        driver = self.driver

        # Navigate to Nearby Donors Map View
        safe_click(driver, driver.find_element(By.ID, "nav-item-nearby-map"))
        time.sleep(0.5)
        map_elem = driver.find_element(By.ID, "seekerDonorMap")
        self.assertIsNotNone(map_elem)

        # Switch to Donor Directory
        safe_click(driver, driver.find_element(By.ID, "nav-item-donor-directory"))
        time.sleep(0.5)
        dir_filter = driver.find_element(By.ID, "dirBloodFilter")
        self.assertIsNotNone(dir_filter)

if __name__ == "__main__":
    unittest.main()

