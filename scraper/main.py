from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
import json
import os
import sys
import traceback
from time import sleep

load_dotenv()


def _str_to_bool(x: str) -> bool:
    return str(x).strip().lower() in ("1", "true", "t", "yes", "y")


DEBUG = _str_to_bool(os.getenv("DEBUG", "False"))
BROWSER = os.getenv("BROWSER", "firefox").strip().lower()
USERNAME = os.getenv("DOCUMENTO", "")
PASSWORD = os.getenv("CONTRASENA", "")

LOGIN_URL = "https://bedelias.udelar.edu.uy/views/private/desktop/evaluarPrevias/evaluarPrevias02.xhtml?cid=2"


def _get_options(browser: str):
    if browser == "chrome":
        options = ChromeOptions()
        if not DEBUG:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return options
    # default firefox
    options = FirefoxOptions()
    if not DEBUG:
        options.add_argument("--headless")
    return options


def build_driver(browser: str) -> webdriver.Remote:
    browser = (browser or "firefox").strip().lower()
    if browser == "chrome":
        return webdriver.Chrome(options=_get_options("chrome"))
    # default to firefox for unknown values
    return webdriver.Firefox(options=_get_options("firefox"))


def hover_by_text(driver: webdriver.Remote, text: str):
    el = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.LINK_TEXT, text))
    )
    ActionChains(driver).move_to_element(el).perform()


def extract_table_info(table_element):
    """
    Extracts information from a table (and nested tables) into a list of row dicts.
    """
    table_data = []
    rows = table_element.find_elements(By.CSS_SELECTOR, "tbody tr")
    for row in rows:
        row_data = {}
        cells = row.find_elements(By.CSS_SELECTOR, "td")
        for idx, cell in enumerate(cells):
            nested_tables = cell.find_elements(By.CSS_SELECTOR, "table")
            if nested_tables:
                row_data[f"Column {idx + 1}"] = [extract_table_info(nt) for nt in nested_tables]
            else:
                txt = cell.text.strip()
                if txt:
                    row_data[f"Column {idx + 1}"] = txt
        if row_data:
            table_data.append(row_data)
    return table_data


def get_total_pages(driver: webdriver.Remote, wait: WebDriverWait) -> int:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    sleep(0.3)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class,'ui-paginator-last')]"))).click()
    sleep(0.3)
    active_anchor_xpath = "//a[contains(@class,'ui-paginator-page') and contains(@class,'ui-state-active')]"
    active = wait.until(EC.presence_of_element_located((By.XPATH, active_anchor_xpath)))
    total = int(active.text.strip())
    print(total)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='ui-paginator-first ui-state-default ui-corner-all']"))).click()
    return total


def get_previas(driver: webdriver.Remote, wait: WebDriverWait):
    print("--------------------------------")
    print("Getting previas...")
    print("--------------------------------")
    hover_by_text(driver, "PLANES DE ESTUDIO")
    link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Planes de estudio / Previas")))
    link.click()
    sleep(0.5)

    # Expand and open info
    wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@class='ui-row-toggler ui-icon ui-icon-circle-triangle-e']"))).click()
    sleep(0.3)
    wait.until(EC.element_to_be_clickable((By.XPATH, '//i[@class="pi  pi-info-circle"]'))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Sistema de previaturas"]'))).click()
    sleep(0.3)

    print("Getting total pages...")
    # Ensure paginator is in known state and get total pages
    total_pages = get_total_pages(driver, wait)
    print(f"Total pages detected: {total_pages}")

    data = {}
    print(total_pages)
    for current_page in range(1, total_pages + 1):
        sleep(0.1)
        rows_len = len(driver.find_elements(By.XPATH, '//tr[@class="ui-widget-content ui-datatable-even"]'))
        for i in range(rows_len):
            row = driver.find_elements(By.XPATH, '//tr[contains(@class, "ui-widget-content")]')[i]
            driver.find_elements(By.XPATH, f'//tr[contains(@class, "ui-widget-content")]/td[3]/a')[i].click()
        
            
            
    # Persist
    with open("previas_data.json", "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    print("Saved previas_data.json")


def get_materias(driver: webdriver.Remote, wait: WebDriverWait):
    hover_by_text(driver, "ESTUDIANTE")
    link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Evaluar previas")))
    link.click()

    total_pages = get_total_pages(driver, wait)
    data = []
    active_anchor_xpath = "//a[contains(@class,'ui-paginator-page') and contains(@class,'ui-state-active')]"

    for current_page in range(1, total_pages + 1):
        tbody = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "tbody.ui-datatable-data.ui-widget-content")
            )
        )
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            cell_data = [cell.text for cell in cells]
            if cell_data:
                data.append(cell_data)

        if current_page < total_pages:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class,'ui-paginator-next')]"))).click()
            wait.until(lambda d: d.find_element(By.XPATH, active_anchor_xpath).text.strip() == str(current_page + 1))

    cleaned_data = [list(t) for t in set(tuple(e) for e in data if e)]
    with open("table_data.json", "w", encoding="utf-8") as json_file:
        json.dump(cleaned_data, json_file, ensure_ascii=False, indent=2)
    print("Saved table_data.json")


def login_and_navigate(driver: webdriver.Remote, wait: WebDriverWait, username: str, password: str):
    print("Starting")
    driver.get(LOGIN_URL)
    username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
    username_field.send_keys(username)
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(password)
    login_button = driver.find_element(By.NAME, "_eventId_proceed")
    login_button.click()
    # Wait for a known menu link to indicate post-login
    wait.until(
        EC.presence_of_element_located(
            (By.LINK_TEXT, "PLANES DE ESTUDIO")
        )
    )


def main():
    if not USERNAME or not PASSWORD:
        print("ERROR: USERNAME or PASSWORD not set in environment.")
        sys.exit(1)

    driver = build_driver(BROWSER if BROWSER in ("chrome", "firefox") else "firefox")
    wait = WebDriverWait(driver, 60)
    try:
        login_and_navigate(driver, wait, USERNAME, PASSWORD)
        get_previas(driver, wait)
        # Optionally:
        # get_materias(driver, wait)
    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()
    finally:
        print("done")
        driver.quit()


if __name__ == "__main__":
    main()