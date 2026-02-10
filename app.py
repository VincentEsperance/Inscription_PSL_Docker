from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

delay = 100
url_login = 'https://sports.monportail.psl.eu/pegasus/index.php'
url_planning = 'https://sports.monportail.psl.eu/pegasus/index.php?com=courses_choices&job=load-calendrier-courses.html'
url_inscription = 'https://sports.monportail.psl.eu/pegasus/index.php?com=courses_choices&job=enregistrer-courses_choices'

# -----------------------------
#  OPTIONS CHROME (corrigées)
# -----------------------------
options = Options()
options.binary_location = '/opt/chrome/chrome'   # <-- correction
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--single-process')

# Répertoires nécessaires dans Lambda
options.add_argument('--user-data-dir=/tmp/user-data')
options.add_argument('--data-path=/tmp/data-path')
options.add_argument('--disk-cache-dir=/tmp/cache-dir')


# -----------------------------
#  FONCTION DE TEST (inchangée)
# -----------------------------
def test_element(_driver, _css_selector):
    try:
        btn = WebDriverWait(_driver, delay).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, _css_selector))
        )
        btn.click()
    except:
        test_element(_driver, _css_selector)  # boucle infinie conservée
    return btn


# -----------------------------
#  HANDLER LAMBDA (corrigé)
# -----------------------------
def handler(event, context):

    # IMPORTANT : driver créé ici (pas global)
    service = Service('/usr/bin/chromedriver')  # <-- correction
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url_login)

    txtbox_login = WebDriverWait(driver, delay).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#inputLogin"))
    )
    txtbox_login.send_keys('vincent.esperance@alumni.chimie-paristech.fr')

    txtbox_psw = driver.find_element(By.CSS_SELECTOR, "#inputPassword")
    txtbox_psw.send_keys('V.Esp6991')

    time.sleep(10)
    test_element(driver, "input.validation")

    driver.get(url_planning)
    time.sleep(10)
    test_element(driver, ".wc-next").text

    # Jeudi
    elements = WebDriverWait(driver, delay).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//*[contains(text(), 'Badminton5-CSU J.Sarrailh 31 Avenue Georges Bernanos75005 PARIS')]")
        )
    )
    lst_seances_bad = elements[0]
    lst_seances_bad.click()

    time.sleep(3)
    test_element(driver, "#cboxLoadedContent > div > div > button")

    response_1 = WebDriverWait(driver, delay).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#swal2-content"))
    ).text

    driver.quit()

    return {
        "statusCode": 200,
        "response": response_1
    }
