from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv
import json
import os
load_dotenv()


driver = webdriver.FirefoxD()
from time import sleep

username = os.getenv("USERNAME")  # tu user
passsword = os.getenv("PASSWORD")  # Tu contra

print("Starting")


def hoverByText(text):
    estudiante_button = driver.find_element(By.LINK_TEXT, text)
    actions = ActionChains(driver)
    actions.move_to_element(estudiante_button).perform()


def click_next_button(element, max_retries=10, retry_delay=1):
    for _ in range(max_retries):
        try:
            sleep(retry_delay)  # Wait before attempting to click
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, element)))
            next_button.click()
            return True  # Successfully clicked the button
        except Exception as e:
            # Log or handle the exception if needed
            print(f"Attempt failed: {e}")
    return False  # Failed after all retries


def extract_table_info(table_element):
    """
    Recursively extracts information from a table and its nested tables into a dictionary.

    :param table_element: The WebElement of the table to extract data from.
    :return: A dictionary containing table data.
    """
    table_data = []

    # Extract headers if available

    rows = table_element.find_elements(By.CSS_SELECTOR, "tbody tr")

    for row in rows:
        row_data = {}
        cells = row.find_elements(By.CSS_SELECTOR, "td")

        # If no headers, use index as keys
        for idx, cell in enumerate(cells):
            if cell.text.strip():
                row_data[f"Column {idx + 1}"] = cell.text.strip()

        table_data.append(row_data)

        # Handle nested tables within the cell
        nested_tables = row.find_elements(By.CSS_SELECTOR, "table")

    return table_data


def get_previas():
    print("HOLDING")
    hoverByText("PLANES DE ESTUDIO")
    link = wait.until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Planes de estudio / Previas"))
    )
    link.click()
    data = {}
    sleep(3)

    element = "//div[@class='ui-row-toggler ui-icon ui-icon-circle-triangle-e']"
    wait.until(EC.element_to_be_clickable((By.XPATH, element))).click()

    element = '//img[@src="/javax.faces.resource/default/img/info_small.png.xhtml"]'
    wait.until(EC.element_to_be_clickable((By.XPATH, element))).click()
    sleep(3)
    element = '//span[text()="Sistema de previaturas"]'
    wait.until(EC.element_to_be_clickable((By.XPATH, element))).click()
    sleep(2)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    click_next_button("//span[@class='ui-icon ui-icon-seek-end']")
    sleep(2)
    number_pages = int(
        wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//span[@class='ui-paginator-page ui-state-default ui-corner-all ui-state-active']",
                )
            )
        ).text
    )
    click_next_button("//span[@class='ui-icon ui-icon-seek-first']")
    sleep(2)

    for page_number in range(2, number_pages):
        sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        tbody = driver.find_element(
            By.XPATH, '//tbody[@class="ui-datatable-data ui-widget-content"]'
        )

        # Find all rows in the tbody
        rows = tbody.find_elements(By.XPATH, ".//tr")

        # Iterate over each row
        for index, _ in enumerate(rows):
            # Extract all cells (td) in the current row
            tbody = driver.find_element(
                By.XPATH, '//tbody[@class="ui-datatable-data ui-widget-content"]'
            )
            sleep(2)

            row = tbody.find_elements(By.XPATH, ".//tr")[index]
            cells = row.find_elements(By.XPATH, ".//td")

            # Collect cell text
            cell_texts = [cell.text for cell in cells]

            # Print row information

            data[cell_texts[0]] = {}
            # Find and click the "Ver más" link if it exists
            link = row.find_element(By.XPATH, './/a[text()="Ver más"]')
            link.click()

            sleep(2)
            while (
                len(
                    driver.find_elements(
                        By.CSS_SELECTOR, "span.ui-tree-toggler.ui-icon.ui-icon-plus"
                    )
                )
                != 0
            ):
                element = driver.find_elements(
                    By.CSS_SELECTOR, "span.ui-tree-toggler.ui-icon.ui-icon-plus"
                )[0]
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                # Iterate over each element and click
                element.click()
                # Optionally wait to see the effect of the click
                sleep(1)  # Adjust time as needed

            main_tables = driver.find_elements(By.CSS_SELECTOR, "table")

            # Extract information from each main table

            print()
            print()

            print()

            for idx, main_table in enumerate(main_tables):
                table_info = extract_table_info(main_table)
                print()

                print()
                print()

                print(f"Table {idx + 1}: {table_info}")

            sleep(2)
            wait.until(
                EC.element_to_be_clickable((By.XPATH, '//span[text()="Volver"]'))
            ).click()
            sleep(2)
            print(data)

        sleep(2)
        click_next_button("//span[@class='ui-icon ui-icon-seek-next']")
        sleep(2)


def get_materias():
    hoverByText("ESTUDIANTE")
    link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Evaluar previas")))
    link.click()
    data = []
    sleep(3)
    click_next_button("//span[@class='ui-icon ui-icon-seek-end']")
    number_pages = int(
        wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//span[@class='ui-paginator-page ui-state-default ui-corner-all ui-state-active']",
                )
            )
        ).text
    )
    click_next_button("//span[@class='ui-icon ui-icon-seek-first']")
    sleep(2)
    for page_number in range(2, number_pages):
        tbody = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "tbody.ui-datatable-data.ui-widget-content")
            )
        )

        rows = tbody.find_elements(By.TAG_NAME, "tr")

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            cell_data = [cell.text for cell in cells]
            data.append(cell_data)
        sleep(2)
        click_next_button("//span[@class='ui-icon ui-icon-seek-next']")
        sleep(2)

    cleaned_data = [list(t) for t in set(tuple(e) for e in data if e)]
    with open("table_data.json", "w") as json_file:
        json.dump(cleaned_data, json_file, indent=4)


try:
    driver.get(
        "https://bedelias.udelar.edu.uy/views/private/desktop/evaluarPrevias/evaluarPrevias02.xhtml?cid=2"
    )
    wait = WebDriverWait(driver, 60)
    username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))

    username_field.send_keys(username)
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(passsword)

    login_button = driver.find_element(By.NAME, "_eventId_proceed")
    login_button.click()
    sleep(4)

    get_previas()


except Exception as e:
    print("ERROR:", e)
finally:
    print("done")
    sleep(30)
    driver.quit()
