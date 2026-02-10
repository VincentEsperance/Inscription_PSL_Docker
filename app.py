# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options

# def handler(event, context):
#     options = Options()
#     options.add_argument("--headless=new")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")

#     driver = webdriver.Chrome(options=options)
#     driver.get("https://www.google.com")
#     title = driver.title
#     driver.quit()

#     return {"title": title}

from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

delay = 100
url_login = 'https://sports.monportail.psl.eu/pegasus/index.php'
url_planning = 'https://sports.monportail.psl.eu/pegasus/index.php?com=courses_choices&job=load-calendrier-courses.html'
url_inscription = 'https://sports.monportail.psl.eu/pegasus/index.php?com=courses_choices&job=enregistrer-courses_choices'

options = Options()
options.binary_location = '/opt/headless-chromium'
options.add_argument('--headless')
options.add_argument('--no-sandbox')
# options.add_argument('--single-process')
options.add_argument('--disable-dev-shm-usage')



def test_element(_driver, _css_selector):
    try:
        btn = WebDriverWait(_driver, delay).until(EC.presence_of_element_located((By.CSS_SELECTOR, _css_selector)))
        btn.click()
    except :
        test_element(_driver, _css_selector)
    return btn

def handler(event, context):
    driver = webdriver.Chrome(options=options)
    driver.get(url_login)
    
    txtbox_login = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#inputLogin")))
    txtbox_login.send_keys('vincent.esperance@alumni.chimie-paristech.fr')
    
    txtbox_psw = driver.find_element(By.CSS_SELECTOR,"#inputPassword")
    txtbox_psw.send_keys('V.Esp6991')
    time.sleep(10)
    test_element(driver, "input.validation")
    
    driver.get(url_planning)
    time.sleep(10)
    test_element(driver, ".wc-next").text
    
    '''
    div_1 = test_element("#calendar > div > div.wc-scrollable-grid > table > tbody > tr.wc-grid-row-events > td.ui-state-default.wc-day-column.wc-day-column-first.wc-day-column-last.day-4 > div > div:nth-child(9)").text
    time.sleep(3)
    test_element("#cboxLoadedContent > div > div > button").text
    response_1 = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CSS_SELECTOR,"#swal2-content"))).text
    '''
    
    #Jeudi
    elements = WebDriverWait(driver, delay).until(EC.presence_of_all_elements_located((By.XPATH, f"//*[contains(text(), 'Badminton5-CSU J.Sarrailh 31 Avenue Georges Bernanos75005 PARIS')]")))
    lst_seances_bad = elements[1]
    lst_seances_bad.click()
    time.sleep(3)
    test_element(driver, "#cboxLoadedContent > div > div > button")
    response_1 = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CSS_SELECTOR,"#swal2-content"))).text
    
    driver.quit()

    response = {
        "statusCode : ": 200,
        "response : ": response_1
        }
        
    return response

