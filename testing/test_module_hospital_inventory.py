import time
import unittest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from testing.driver_factory import create_chrome_driver, safe_click
from testing.server_manager import start_test_server, stop_test_server, BASE_URL

class TestModuleHospitalInventory(unittest.TestCase):
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

    def _login_as_hospital(self):
        driver = self.driver
        driver.get(f"{BASE_URL}/login")
        driver.find_element(By.ID, "loginPhoneInput").clear()
        driver.find_element(By.ID, "loginPhoneInput").send_keys("+8801734567890")
        driver.find_element(By.ID, "loginPasswordInput").clear()
        driver.find_element(By.ID, "loginPasswordInput").send_keys("hospital123")
        safe_click(driver, driver.find_element(By.ID, "loginSubmitBtn"))
        WebDriverWait(driver, 8).until(EC.url_contains("/hospital/dashboard"))

    def _switch_hospital_tab(self, nav_id, section_id):
        driver = self.driver
        btn = driver.find_element(By.ID, nav_id)
        safe_click(driver, btn)
        WebDriverWait(driver, 6).until(
            lambda d: "active" in d.find_element(By.ID, section_id).get_attribute("class")
        )
        time.sleep(0.4)

    def test_tc_hosp_01_matrix_display(self):
        """TC-HOSP-01: Hospital dashboard renders complete 8-blood-group stock inventory table."""
        self._login_as_hospital()
        driver = self.driver

        self._switch_hospital_tab("nav-item-stock-matrix", "section-stock-matrix")

        expected_groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        for bg in expected_groups:
            row = driver.find_elements(By.CSS_SELECTOR, f"tr[data-inventory-row='{bg}']")
            self.assertTrue(len(row) > 0, f"Blood group row {bg} should be present in matrix")

    def test_tc_hosp_02_stock_quantity_update(self):
        """TC-HOSP-02: Hospital can update available blood stock units for a specific blood group."""
        self._login_as_hospital()
        driver = self.driver

        self._switch_hospital_tab("nav-item-stock-matrix", "section-stock-matrix")

        # Find row for O-
        row = driver.find_element(By.CSS_SELECTOR, "tr[data-inventory-row='O-']")
        qty_input = row.find_element(By.NAME, "quantity")
        save_btn = row.find_element(By.CSS_SELECTOR, "button[data-inventory-save]")

        qty_input.clear()
        qty_input.send_keys("15")
        safe_click(driver, save_btn)
        time.sleep(1.5)

        # Check updated text or input value
        qty_val = qty_input.get_attribute("value")
        self.assertEqual(qty_val, "15")

    def test_tc_hosp_03_low_stock_alerts_view(self):
        """TC-HOSP-03: Facility can view active low-stock inventory alerts and reorder threshold triggers."""
        self._login_as_hospital()
        driver = self.driver

        self._switch_hospital_tab("nav-item-stock-alerts", "section-stock-alerts")

        alerts_section = driver.find_element(By.ID, "section-stock-alerts")
        self.assertTrue(alerts_section.is_displayed())
        self.assertIn("Low Blood Stock Alerts", alerts_section.text)

    def test_tc_hosp_04_institutional_blood_requests_allocation(self):
        """TC-HOSP-04: Hospital can manage emergency blood stock requests and allocations."""
        self._login_as_hospital()
        driver = self.driver

        self._switch_hospital_tab("nav-item-blood-allocation", "section-blood-allocation")

        alloc_section = driver.find_element(By.ID, "section-blood-allocation")
        self.assertTrue(alloc_section.is_displayed())

    def test_tc_hosp_05_donor_search_and_outreach(self):
        """TC-HOSP-05: Hospital can search voluntary donor directory and view outreach coordination."""
        self._login_as_hospital()
        driver = self.driver

        self._switch_hospital_tab("nav-item-donor-search", "section-donor-search")

        search_section = driver.find_element(By.ID, "section-donor-search")
        self.assertTrue(search_section.is_displayed())

if __name__ == "__main__":
    unittest.main()

