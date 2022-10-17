import base64
import io
from datetime import datetime

from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from dashboardPage import DashboardPage
from logger_assistant import *


class Selenium:
    def __init__(self, id: str, hours=3):
        self.id = id
        self.dashboard_indicator_url = 'https://.../htm/m_details.htm?meas_id=' + id
        self.hours = int(hours)
        self.sleep = {3: 10, 24: 15, 168: 30}
        self.graphic = None
        if int(hours) == 3:
            self.custom_graphic_url = f"https://.../hs_report.jsp?report=PORTAL&id={id}" \
                                      f"&sha=1&ev=1&th=1&hours={hours}&agg=1m"
        elif int(hours) == 24:
            self.custom_graphic_url = f"https://.../hs_report.jsp?report=PORTAL&id={id}" \
                                      f"&sha=1&ev=1&th=1&hours={hours}&agg=5m"
        elif int(hours) == 168:
            self.custom_graphic_url = f"https://.../hs_report.jsp?report=PORTAL&id={id}" \
                                      f"&sha=1&ev=1&th=1&hours={hours}&agg=1h"
        self.errors = []
        self.image = None

        self.script_location = get_script_location()
        self.script_name = get_script_name()
        self.screenshot_location = make_and_get_screenshot_location(self.script_location)
        self.now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.logs_paths = make_and_get_logs_path()

        self.driver = False
        options = webdriver.FirefoxOptions()
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--headless")
        options.add_argument('--log-level=3')
        options.add_argument('--ignore-certificate-sppki-list')
        options.add_argument('--ignore-ssl-errors')
        executable_path = "geckodriver"
        self.driver = webdriver.Firefox(firefox_options=options, executable_path=executable_path)

    def get_image(self, graphic_option_value=None):
        if self.driver:
            self.driver.set_page_load_timeout(20)
            self.driver.get(self.dashboard_indicator_url)
            time.sleep(10)
            self.driver.set_window_size(1910, 1001)
            if graphic_option_value:
                w = WebDriverWait(self.driver, 10)
                diagram_hours = w.until(EC.presence_of_element_located((By.XPATH, '//*[@id="diagram_hours"]')))
                diagram_hours.click()
                diagram_hours_option = w.until(EC.presence_of_element_located((By.XPATH,
                                                                               f'//*[@id="diagram_hours"]'
                                                                               f'/option[{graphic_option_value}]')))
                diagram_hours_option.click()
                time.sleep(5)
            base64_png = self.driver.get_screenshot_as_base64()
            png = self.driver.get_screenshot_as_png()
            self.image = Image.open(io.BytesIO(png))
            screenshot_name = f"{self.id}_{self.now}.png"
            self.driver.save_screenshot(str(self.screenshot_location / screenshot_name))

            return base64_png

    def get_custom_graphic_image(self):
        if self.driver:
            self.driver.set_page_load_timeout(2)
            self.driver.get(self.custom_graphic_url)
            self.driver.set_window_size(1024, 600)
            time.sleep(self.sleep.get(self.hours, 10))
            base64_png = self.driver.get_screenshot_as_base64()
            png = self.driver.get_screenshot_as_png()
            self.image = Image.open(io.BytesIO(png))
            screenshot_name = f"custom_{self.id}_{self.now}.png"
            self.driver.save_screenshot(str(self.screenshot_location / screenshot_name))
            return base64_png

    def get_graphic(self):
        self.graphic = DashboardPage(self.image).get_graphic()
        graphic_name = f"graphic_{self.id}_{self.now}.png"
        self.graphic.save(self.screenshot_location / graphic_name)
        buffered = io.BytesIO()
        self.graphic.save(buffered, format="PNG")
        graphic_64_encode = base64.b64encode(buffered.getvalue())
        return graphic_64_encode

    def get_statuses(self):
        self.graphic = DashboardPage(self.image).get_statuses()
        graphic_name = f"statuses_{self.id}_{self.now}.png"
        self.graphic.save(self.screenshot_location / graphic_name)
        buffered = io.BytesIO()
        self.graphic.save(buffered, format="PNG")
        graphic_64_encode = base64.b64encode(buffered.getvalue())
        return graphic_64_encode

    def get_custom_graphic(self):
        self.graphic = DashboardPage(self.image).get_custom_graphic()
        graphic_name = f"custom_graphic_{self.id}_{self.now}.png"
        self.graphic.save(self.screenshot_location / graphic_name)
        buffered = io.BytesIO()
        self.graphic.save(buffered, format="PNG")
        graphic_64_encode = base64.b64encode(buffered.getvalue())
        return graphic_64_encode

    def quit(self):
        self.driver.quit()
