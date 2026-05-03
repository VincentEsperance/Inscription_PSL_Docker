import json
import logging
import os
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configuration via variables d'environnement
URL = "https://sports.monportail.psl.eu/pegasus/index.php"
USERNAME = os.environ.get("PEGASUS_USERNAME", "")
PASSWORD = os.environ.get("PEGASUS_PASSWORD", "")
ACTIVITY_LABEL = "Volley 3- CSU Jean Sarrailh 31 Avenue Bernanos75005 PARIS"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_logs = []


def log(msg: str):
    logger.info(msg)
    _logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def wait_for_page(page, selector_to_wait=None, timeout=30000):
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


def wait_for_frame(page, selector_to_wait, timeout=30000):
    """
    Attend qu'un selecteur soit present dans l'iframe pegasus_contenu.
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
            page.set_default_timeout(30000)

            # ----------------------------------------------------------------
            # ETAPE 1 : Connexion
            # ----------------------------------------------------------------
            log(f"Navigation vers {URL}")
            page.goto(URL, wait_until="domcontentloaded")
            wait_for_page(page, selector_to_wait="input.validation", timeout=30000)

            log("Remplissage du formulaire de connexion...")
            page.locator('input[type="text"]').first.fill(USERNAME)
            page.locator('input[type="password"]').fill(PASSWORD)

            log("Clic sur 'Se connecter'...")
            page.locator("input.validation[value='Se connecter']").click()
            wait_for_page(page, selector_to_wait=".title-text", timeout=30000)

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
            wait_for_frame(page, selector_to_wait="button.wc-next", timeout=30000)
            log("Page calendrier chargee.")

            # Entre dans l'iframe pour toutes les interactions calendrier
            frame = page.frame_locator("iframe#pegasus_contenu")

            # ----------------------------------------------------------------
            # ETAPE 4 : Semaine suivante
            # ----------------------------------------------------------------
            log("Passage a la semaine suivante...")
            frame.locator("button.wc-next").click()
            page.wait_for_timeout(2000)

            try:
                week_label = frame.locator("h1.wc-title").inner_text()
                log(f"Semaine affichee : {week_label.strip()}")
            except Exception:
                pass

            # ----------------------------------------------------------------
            # ETAPE 5 : Clic sur le creneau Volley du lundi
            # ----------------------------------------------------------------
            log(f"Recherche du creneau Volley du lundi...")
            # On cible uniquement la colonne day-1 (lundi) pour éviter les doublons
            slot = frame.locator(".wc-day-column-inner.day-1 .get-syllabus", has_text="Volley 3- CSU Jean Sarrailh").first
            slot.wait_for(timeout=30000)
            slot.click()
            page.wait_for_timeout(1200)
            log("Creneau clique, attente de la modale...")

            # ----------------------------------------------------------------
            # ETAPE 6 : Log du statut dans la modale
            # ----------------------------------------------------------------
            try:
                wait_for_frame(page, selector_to_wait="button.button-action", timeout=15000)
                modal_text = frame.locator("button.button-action").locator("..").inner_text()
                log(f"Contenu modale : {modal_text.strip()[:300]}")
            except Exception:
                log("(Impossible de lire la modale, on continue)")

            # ----------------------------------------------------------------
            # ETAPE 7 : Clic sur "M'inscrire" dans la modale
            # ----------------------------------------------------------------
            log("Clic sur le bouton M inscrire...")
            frame.get_by_role("button", name="M'inscrire").last.click()
            wait_for_page(page, timeout=35000)

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
