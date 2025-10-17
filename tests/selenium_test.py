import os, time
import pytest
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import Select



BASE_URL = os.getenv("APP_URL", "http://localhost:5000")

@pytest.fixture(scope="module")
def driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
    yield driver
    driver.quit()

def test_health(driver):
    driver.get(f"{BASE_URL}/health")
    assert "OK" in driver.page_source

def test_positive_search(driver):
    driver.get(f"{BASE_URL}/")

    # Set <input type="date"> via JS (more reliable in headless)
    driver.execute_script("document.querySelector('input[name=start]').value='2023-01-01'")
    driver.execute_script("document.querySelector('input[name=end]').value='2023-01-31'")

    # Select borough and complaint
    Select(driver.find_element(By.NAME, "borough")).select_by_visible_text("BROOKLYN")
    c = driver.find_element(By.NAME, "complaint")
    c.clear()
    c.send_keys("Noise")

    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()

# Wait for real navigation to /search (more reliable in headless)
WebDriverWait(driver, 10).until(EC.url_contains("/search"))
# Optional: also ensure the Results header has rendered
WebDriverWait(driver, 10).until(EC.text_to_be_present_in_element((By.TAG_NAME, "h1"), "Results"))

assert "Results" in driver.page_source
assert "No results" not in driver.page_source



def test_negative_search(driver):
    driver.get(f"{BASE_URL}/")

    driver.execute_script("document.querySelector('input[name=start]').value='2023-01-01'")
    driver.execute_script("document.querySelector('input[name=end]').value='2023-01-02'")

    Select(driver.find_element(By.NAME, "borough")).select_by_visible_text("STATEN ISLAND")
    c = driver.find_element(By.NAME, "complaint")
    c.clear()
    c.send_keys("THIS_SHOULD_NOT_MATCH")

    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()

WebDriverWait(driver, 10).until(EC.url_contains("/search"))
WebDriverWait(driver, 10).until(EC.text_to_be_present_in_element((By.TAG_NAME, "h1"), "Results"))

assert "No results" in driver.page_source



def test_aggregate(driver):
    driver.get(f"{BASE_URL}/aggregate/borough")
    assert "Complaints per Borough" in driver.page_source
