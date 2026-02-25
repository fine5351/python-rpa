import logging
import os
import subprocess
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, SessionNotCreatedException

logger = logging.getLogger(__name__)

class WebDriverUtil:
    CHROME_DATA_DIR = "d:/work/workspace/java/rpa/chrome-data"

    @staticmethod
    def initialize_driver() -> webdriver.Chrome:
        options = Options()
        options.add_argument(f"user-data-dir={WebDriverUtil.CHROME_DATA_DIR}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-allow-origins=*")

        service = Service(ChromeDriverManager().install())

        try:
            return webdriver.Chrome(service=service, options=options)
        except SessionNotCreatedException as e:
            logger.warning(f"Chrome Driver start failed. Attempting to kill locked Chrome instance...: {e}")
            try:
                # Same command as Java to terminate locked Chrome instance
                cmd = f'wmic process where "name=\'chrome.exe\' and commandline like \'%chrome-data%\'" call terminate'
                subprocess.run(cmd, shell=True, capture_output=True)
                
                # Try to remove the lock file
                lock_file = os.path.join(WebDriverUtil.CHROME_DATA_DIR, "SingletonLock")
                if os.path.exists(lock_file):
                    os.remove(lock_file)
                time.sleep(2)
            except Exception as ex:
                logger.error(f"Failed to cleanup locked Chrome profile: {ex}")
            
            # Retry initializing driver
            return webdriver.Chrome(service=service, options=options)

    @staticmethod
    def find_element(driver: webdriver.Chrome, step_name: str, by: str, value: str, element_name: str, timeout: int = 5) -> WebElement:
        while True:
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                logger.info(f"已找到 {element_name} : {value}")
                return element
            except TimeoutException:
                logger.info(f"步驟 : {step_name}, 持續尋找中 {element_name}...")
                time.sleep(2)

    @staticmethod
    def find_clickable_element(driver: webdriver.Chrome, step_name: str, by: str, value: str, element_name: str, timeout: int = 5) -> WebElement:
        while True:
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((by, value))
                )
                return element
            except TimeoutException:
                logger.info(f"步驟 : {step_name}, 持續尋找中 {element_name}...")
                time.sleep(2)

    @staticmethod
    def dispatch_click_events(driver: webdriver.Chrome, element: WebElement):
        script = """
            var evt1 = new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window});
            var evt2 = new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window});
            var evt3 = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});
            arguments[0].dispatchEvent(evt1);
            arguments[0].dispatchEvent(evt2);
            arguments[0].dispatchEvent(evt3);
        """
        driver.execute_script(script, element)
