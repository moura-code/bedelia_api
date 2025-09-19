

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from time import sleep


class UseTable():
    
    def get_total_pages(self) -> int:
        """Get the total number of pages in the paginator."""
        self.scroll_to_bottom()
        self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@class,'ui-paginator-last')]")
            )
        ).click()
        active_anchor_xpath = "//a[contains(@class,'ui-paginator-page') and contains(@class,'ui-state-active')]"
        # TODO: remover esse sleep
        sleep(0.2)
        active = self.wait.until(
            EC.presence_of_element_located((By.XPATH, active_anchor_xpath))
        )
        
        total = int(active.text.strip())
        self.logger.info(f"Total pages: {total}")
        self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//a[@class='ui-paginator-first ui-state-default ui-corner-all']",
                )
            )
        ).click()
        self.total_pages = total
        return total

    def go_to_page(self, page: int):
        if (
            self.wait_for_element_to_be_visible((
                By.XPATH,
                '//a[contains(@class, "ui-state-active")]',
            )).get_attribute("aria-label")
            == f"Page {page}"
        ):
            return
        if page > 10:
            self.scroll_to_element_and_click(self.wait_for_element_to_be_clickable((By.XPATH, f'//a[contains(@class,"ui-paginator-last")]')))
            self.wait_for_page_to_load()

        self.scroll_to_element_and_click(self.wait_for_element_to_be_clickable((By.XPATH, f'//a[@aria-label="Page {page}"]')))
        self.wait_for_page_to_load()
