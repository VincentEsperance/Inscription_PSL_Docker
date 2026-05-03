import json
import logging
import os
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configuration via variables d'environnement
URL = "https://sports.monportail.psl.eu/pegasus/index.php"
USERNAME = os.environ.get("PEGASUS_USERNAME", "")
PASSWORD = os.environ.get("PEGASUS_PASSWORD", "")
ACTIVITY_LABEL = "Badminton5-CSU J.Sarrailh"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_logs = []

# Timeout standard en ms — 5 minutes pour absorber les pics de charge
TIMEOUT = 300000


def log(msg: str):
    logger.info(msg)
    _logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def wait_for_page(page, selector_to_wait=None, timeout=TIMEOUT):
    """
    Attend que la page soit chargee.
    Si un selecteur est fourni, attend que cet element soit present dans le DOM.
    Sinon, attend networkidle avec fallback sur domcontentloaded si le site est lent.
    """
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
        if selector_to_wait:
            page.wait_for_selector(selector_to_wait, timeout=timeout)
        else:
            page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeoutError:
        log("Chargement lent detecte, on continue quand meme...")


def wait_for_frame(page, selector_to_wait, timeout=TIMEOUT):
    """
    Attend qu'un selecteur soit present et visible dans l'iframe pegasus_contenu.
    """
    try:
        frame = page.frame_locator("iframe#pegasus_contenu")
        frame.locator(selector_to_wait).wait_for(timeout=timeout)
    except PlaywrightTimeoutError:
        log(f"Chargement lent dans l'iframe pour '{selector_to_wait}', on continue...")


def lambda_handler(event, context):
    _logs.clear()
    result = {"success": False, "message": "", "logs": []}

    try:
        with sync_playwright() as p:
            log("Lancement de Chromium (headless)...")
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                    "--disable-extensions",
                ],
            )
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.set_default_timeout(TIMEOUT)

            # ----------------------------------------------------------------
            # ETAPE 1 : Connexion
            # ----------------------------------------------------------------
            log(f"Navigation vers {URL}")
            page.goto(URL, wait_until="domcontentloaded")
            wait_for_page(page, selector_to_wait="input.validation")

            log("Remplissage du formulaire de connexion...")
            page.locator('input[type="text"]').first.fill(USERNAME)
            page.locator('input[type="password"]').fill(PASSWORD)

            log("Clic sur 'Se connecter'...")
            page.locator("input.validation[value='Se connecter']").click()
            wait_for_page(page, selector_to_wait=".title-text")

            body = page.inner_text("body")
            if "Bienvenue" not in body and "portail sportif" not in body.lower():
                raise Exception("Echec de connexion — verifier les identifiants.")
            log("Connexion reussie.")

            # ----------------------------------------------------------------
            # ETAPE 2 : Ouvrir le menu parent "M'inscrire aux seances"
            # ----------------------------------------------------------------
            log("Clic sur le menu parent 'M inscrire aux seances'...")
            page.locator(".title-text", has_text="M'inscrire aux séances").click()
            page.wait_for_timeout(800)

            # ----------------------------------------------------------------
            # ETAPE 3 : Clic sur le sous-menu "M'inscrire aux seances"
            # ----------------------------------------------------------------
            log("Clic sur le sous-menu 'M inscrire aux seances'...")
            page.locator(".menu-item", has_text="M'inscrire aux séances").click()
            wait_for_frame(page, selector_to_wait="button.wc-next")
            log("Page calendrier chargee.")

            # Entre dans l'iframe pour toutes les interactions calendrier
            frame = page.frame_locator("iframe#pegasus_contenu")

            # ----------------------------------------------------------------
            # ETAPE 4 : Semaine suivante (bouton wc-next dans l'iframe)
            # ----------------------------------------------------------------
            log("Passage a la semaine suivante...")
            frame.locator("button.wc-next").click()
            frame.locator(".wc-day-column-inner.day-2 .get-syllabus").first.wait_for(timeout=TIMEOUT)

            try:
                week_label = frame.locator("h1.wc-title").inner_text()
                log(f"Semaine affichee : {week_label.strip()}")
            except Exception:
                pass

            # ----------------------------------------------------------------
            # ETAPE 5 : Clic sur le creneau Badminton du mardi
            # ----------------------------------------------------------------
            log("Recherche du creneau Badminton du mardi...")
            slot = frame.locator(
                ".wc-day-column-inner.day-2 .get-syllabus",
                has_text=ACTIVITY_LABEL
            ).first
            slot.wait_for(timeout=TIMEOUT)
            slot.click()
            log("Creneau clique, attente de la modale...")

            # ----------------------------------------------------------------
            # ETAPE 6 : Attente et log du contenu de la modale
            # ----------------------------------------------------------------
            frame.get_by_role("button", name="M'inscrire").last.wait_for(timeout=TIMEOUT)

            try:
                modal_text = frame.locator("button.button-action").last.locator("..").inner_text()
                log(f"Contenu modale : {modal_text.strip()[:300]}")
            except Exception:
                log("(Impossible de lire la modale, on continue)")

            # ----------------------------------------------------------------
            # ETAPE 7 : Clic sur "M'inscrire" dans la modale
            # ----------------------------------------------------------------
            log("Clic sur le bouton M inscrire...")
            frame.get_by_role("button", name="M'inscrire").last.click()
            wait_for_page(page, timeout=TIMEOUT)

            # ----------------------------------------------------------------
            # ETAPE 8 : Message de confirmation
            # ----------------------------------------------------------------
            log("Lecture du message de confirmation...")
            try:
                body_text = frame.locator("body").inner_text().lower()
            except Exception:
                body_text = page.inner_text("body").lower()

            if "inscription prise en compte" in body_text:
                result["message"] = "Inscription prise en compte !"
                result["success"] = True
            elif "liste d'attente" in body_text:
                result["message"] = "Inscription en liste d'attente."
                result["success"] = True
            elif "deja inscrit" in body_text or "déjà inscrit" in body_text:
                result["message"] = "Vous etes deja inscrit a cette seance."
                result["success"] = True
            else:
                snippet = body_text[:600].replace("\n", " ")
                result["message"] = f"Message de confirmation non reconnu. Extrait : {snippet}"
                result["success"] = False

            log(result["message"])
            browser.close()

    except PlaywrightTimeoutError as e:
        msg = f"Timeout Playwright : {str(e)}"
        log(msg)
        result["message"] = msg
    except Exception as e:
        msg = f"Erreur : {str(e)}"
        log(msg)
        result["message"] = msg

    result["logs"] = _logs
    logger.info("=== RESULTAT FINAL ===\n" + json.dumps(result, ensure_ascii=False, indent=2))
    return result
