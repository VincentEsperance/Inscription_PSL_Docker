from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
import traceback

delay = 100
MAX_RETRIES = 3

url_login = 'https://sports.monportail.psl.eu/pegasus/index.php'
url_planning = 'https://sports.monportail.psl.eu/pegasus/index.php?com=courses_choices&job=load-calendrier-courses.html'
url_inscription = 'https://sports.monportail.psl.eu/pegasus/index.php?com=courses_choices&job=enregistrer-courses_choices'

# -----------------------------
# OPTIONS CHROME (identiques)
# -----------------------------
options = Options()
options.binary_location = '/opt/chrome/chrome'
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--single-process')

options.add_argument('--user-data-dir=/tmp/user-data')
options.add_argument('--data-path=/tmp/data-path')
options.add_argument('--disk-cache-dir=/tmp/cache-dir')


# -----------------------------
# VERSION CORRIGÉE test_element
# -----------------------------
def test_element(driver, css_selector, retries=5):
    for i in range(retries):
        try:
            btn = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
            )
            btn.click()
            return btn
        except Exception:
            time.sleep(2)

    raise TimeoutException(f"Element {css_selector} introuvable")


# -----------------------------
# HANDLER
# -----------------------------
def handler(event, context):

    for attempt in range(MAX_RETRIES):

        driver = None

        try:
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)

            driver.get(url_login)

            txtbox_login = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#inputLogin"))
            )
            txtbox_login.send_keys('vincent.esperance@alumni.chimie-paristech.fr')

            txtbox_psw = driver.find_element(By.CSS_SELECTOR, "#inputPassword")
            txtbox_psw.send_keys('V.Esp6991')

            # Remplace sleep(10)
            WebDriverWait(driver, delay).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input.validation"))
            )
            test_element(driver, "input.validation")

            # Petit délai court au lieu de 10s fixes
            WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            driver.get(url_planning)

            WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".wc-next"))
            )
            test_element(driver, ".wc-next")

            elements = WebDriverWait(driver, delay).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//*[contains(text(), 'Badminton5-CSU J.Sarrailh 31 Avenue Georges Bernanos75005 PARIS')]")
                )
            )

            top_element = min(elements, key=lambda el: el.location['y'])
            top_element.click()

            WebDriverWait(driver, delay).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#cboxLoadedContent > div > div > button")
                )
            )
            test_element(driver, "#cboxLoadedContent > div > div > button")

            response_1 = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#swal2-content"))
            ).text

            driver.quit()

            return {
                "statusCode": 200,
                "response": response_1
            }

        except Exception as e:

            error_trace = traceback.format_exc()

            if driver:
                try:
                    driver.quit()
                except:
                    pass

            if attempt == MAX_RETRIES - 1:
                return {
                    "statusCode": 500,
                    "error": str(e),
                    "trace": error_trace
                }

            time.sleep(3)

    return {
        "statusCode": 500,
        "error": "Erreur inconnue"
    }