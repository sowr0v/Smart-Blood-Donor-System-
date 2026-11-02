import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def create_chrome_driver(headless: bool = True) -> webdriver.Chrome:
    """Creates and returns an instrumented Chrome WebDriver instance."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    return driver

def wait_for_element(driver: webdriver.Chrome, by: By, value: str, timeout: int = 10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def wait_for_clickable(driver: webdriver.Chrome, by: By, value: str, timeout: int = 10):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    )

def wait_for_url_contains(driver: webdriver.Chrome, snippet: str, timeout: int = 10):
    return WebDriverWait(driver, timeout).until(
        EC.url_contains(snippet)
    )

def safe_click(driver: webdriver.Chrome, element):
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.2)
        driver.execute_script("arguments[0].click();", element)

