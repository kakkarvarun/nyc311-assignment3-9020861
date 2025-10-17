import os, time
import pytest
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
    driver.find_element(By.NAME, "start").send_keys("2023-01-01")
    driver.find_element(By.NAME, "end").send_keys("2023-01-31")
    Select(driver.find_element(By.NAME, "borough")).select_by_visible_text("BROOKLYN")
    driver.find_element(By.NAME, "complaint").send_keys("Noise")
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    time.sleep(1)
    assert "Results" in driver.page_source
    assert "No results" not in driver.page_source

def test_negative_search(driver):
    driver.get(f"{BASE_URL}/")
    driver.find_element(By.NAME, "start").send_keys("2023-01-01")
    driver.find_element(By.NAME, "end").send_keys("2023-01-02")
    Select(driver.find_element(By.NAME, "borough")).select_by_visible_text("STATEN ISLAND")
    driver.find_element(By.NAME, "complaint").send_keys("THIS_SHOULD_NOT_MATCH")
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    time.sleep(1)
    assert "No results" in driver.page_source

def test_aggregate(driver):
    driver.get(f"{BASE_URL}/aggregate/borough")
    assert "Complaints per Borough" in driver.page_source
