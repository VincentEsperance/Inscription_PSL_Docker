from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
import traceback
import datetime

delay = 480
MAX_RETRIES = 3

url_login = 'https://sports.monportail.psl.eu/pegasus/index.php'
url_planning = 'https://sports.monportail.psl.eu/pegasus/index.php?com=courses_choices&job=load-calendrier-courses.html'
url_inscription = 'https://sports.monportail.psl.eu/pegasus/index.php?com=courses_choices&job=enregistrer-courses_choices'

# -----------------------------
# OPTIONS CHROME
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
# LOGGER
# -----------------------------
_log = []
_t0 = None

def log(msg):
    """Enregistre un message horodaté dans _log et l'affiche dans CloudWatch."""
    global _t0
    now = datetime.datetime.utcnow()
    if _t0 is None:
        _t0 = now
    elapsed = round((now - _t0).total_seconds(), 2)
    entry = f"[+{elapsed:>7.2f}s] {msg}"
    _log.append(entry)
    print(entry)          # → CloudWatch Logs

def reset_log():
    global _log, _t0
    _log = []
    _t0 = None

def get_log():
    return list(_log)


# -----------------------------
# HELPERS
# -----------------------------
def test_element(driver, css_selector, retries=5):
    log(f"test_element: attente de '{css_selector}'")
    for i in range(retries):
        try:
            btn = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
            )
            btn.click()
            log(f"test_element: '{css_selector}' cliqué (tentative {i+1})")
            return btn
        except Exception as e:
            log(f"test_element: échec tentative {i+1} — {e}")
            time.sleep(2)

    raise TimeoutException(f"Element {css_selector} introuvable après {retries} tentatives")


def safe_get(driver, url, retries=3):
    log(f"safe_get: chargement de {url}")
    for i in range(retries):
        try:
            driver.get(url)
            log(f"safe_get: page chargée (tentative {i+1})")
            return
        except Exception as e:
            log(f"safe_get: échec tentative {i+1} — {e}")
            time.sleep(3)
    raise Exception(f"Impossible de charger {url} après {retries} tentatives")


# -----------------------------
# HANDLER
# -----------------------------
def handler(event, context):

    for attempt in range(MAX_RETRIES):

        reset_log()
        log(f"=== Tentative {attempt + 1}/{MAX_RETRIES} ===")
        driver = None

        try:
            # --- Init driver ---
            log("Init ChromeDriver")
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)
            log("ChromeDriver démarré")

            # --- Login page ---
            safe_get(driver, url_login)

            log("Attente champ login (#inputLogin)")
            txtbox_login = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#inputLogin"))
            )
            log("Champ login trouvé, saisie identifiant")
            txtbox_login.send_keys('vincent.esperance@alumni.chimie-paristech.fr')

            log("Saisie mot de passe")
            txtbox_psw = driver.find_element(By.CSS_SELECTOR, "#inputPassword")
            txtbox_psw.send_keys('V.Esp6991')

            # --- Submit login ---
            log("Attente bouton validation (input.validation clickable)")
            WebDriverWait(driver, delay).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input.validation"))
            )
            log("Bouton validation clickable, clic")
            test_element(driver, "input.validation")

            # --- Attente post-login ---
            log("Attente body après login")
            WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            log("Body présent après login")

            # --- Page planning ---
            log(f"Navigation vers planning: {url_planning}")
            driver.get(url_planning)

            log("Attente bouton .wc-next sur la page planning")
            WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".wc-next"))
            )
            log("Bouton .wc-next trouvé, clic")
            test_element(driver, ".wc-next")

            # --- Recherche cours Badminton ---
            log("Recherche des éléments Badminton par XPath")
            elements = WebDriverWait(driver, delay).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//*[contains(text(), 'Badminton5-CSU J.Sarrailh 31 Avenue Georges Bernanos75005 PARIS')]")
                )
            )
            log(f"{len(elements)} élément(s) Badminton trouvé(s)")

            top_element = max(elements, key=lambda el: el.location['y'])
            log(f"Clic sur l'élément le plus haut (y={top_element.location['y']})")
            top_element.click()

            # --- Modal inscription ---
            log("Attente bouton dans modal (#cboxLoadedContent > div > div > button)")
            WebDriverWait(driver, delay).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#cboxLoadedContent > div > div > button")
                )
            )
            log("Bouton modal trouvé, clic")
            test_element(driver, "#cboxLoadedContent > div > div > button")

            # --- Réponse finale ---
            log("Attente message de confirmation (#swal2-content)")
            response_1 = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#swal2-content"))
            ).text
            log(f"Réponse reçue: {response_1!r}")

            driver.quit()
            log("Driver fermé — succès")

            return {
                "statusCode": 200,
                "response": response_1,
                "log": get_log()
            }

        except Exception as e:

            error_trace = traceback.format_exc()
            log(f"EXCEPTION: {e}")
            log(f"TRACE:\n{error_trace}")

            if driver:
                try:
                    driver.quit()
                    log("Driver fermé après exception")
                except:
                    log("Impossible de fermer le driver")

            if attempt == MAX_RETRIES - 1:
                return {
                    "statusCode": 500,
                    "error": str(e),
                    "trace": error_trace,
                    "log": get_log()
                }

            log(f"Pause 3s avant tentative suivante")
            time.sleep(3)

    return {
        "statusCode": 500,
        "error": "Erreur inconnue",
        "log": get_log()
    }