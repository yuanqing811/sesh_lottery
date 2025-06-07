import logging
import os
import time
from datetime import datetime
from utils import create_chrome_driver_with_logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException

# Set up logging
logging.basicConfig(level=logging.INFO)

class CSVDownloader:
    def __init__(self, server_id,
                 profile_path="/tmp/selenium-profile",  # macOS example
                 download_dir="/Users/qingyuan/Downloads",
                 timeout=30):

        self.server_id = server_id
        self.url = f'https://sesh.fyi/dashboard/{self.server_id}/events?view=list'
        self.download_dir = download_dir
        self.timeout = timeout
        self.profile_path = profile_path
        self.logger = logging.getLogger(__name__)

    def _setup_driver(self, profile_path):
        """Setup Chrome driver with proper configuration"""
        driver = create_chrome_driver_with_logging(profile_path=profile_path)
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": self.download_dir
        })
        return driver

    def wait_for_file_size_stable(self, file_path, stability_time=3, check_interval=0.5, timeout=30):
        """
        Wait for file size to remain stable for a specified duration.
        
        Args:
            file_path: Path to the file to monitor
            stability_time: How long the size should remain unchanged (in seconds)
            check_interval: How often to check the file size (in seconds)
        
        Returns:
            bool: True if file size stabilized, False if timeout
        """
        self.logger.info(f"Waiting for file size to stabilize: {file_path}")
        last_size = -1
        stable_start = None
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                current_size = os.path.getsize(file_path)
                if current_size == last_size:
                    if stable_start is None:
                        stable_start = time.time()
                    elif time.time() - stable_start >= stability_time:
                        self.logger.info(f"File size stabilized at {current_size} bytes")
                        return True
                else:
                    stable_start = None
                    self.logger.info(f"File size changed: {last_size} -> {current_size} bytes")
                last_size = current_size
                time.sleep(check_interval)
            except FileNotFoundError:
                time.sleep(check_interval)
        self.logger.error("File size did not stabilize within timeout")
        return False

    def wait_and_rename_download(self,
                               original_suffix=".csv",
                               timeout=30,
                               stability_time=3):
        """Wait for download to complete and rename the file"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        new_filename = f"events_{self.server_id}_{date_str}.csv"
        self.logger.info(f"Waiting for download to complete (timeout: {self.timeout}s)")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            files = [f for f in os.listdir(self.download_dir) if
                     f.endswith(original_suffix) and not f.endswith(".crdownload")]
            if files:
                # Sort files by modification time (newest first)
                files.sort(key=lambda x: os.path.getmtime(os.path.join(self.download_dir, x)), reverse=True)
                old_path = os.path.join(self.download_dir, files[0])
                if self.wait_for_file_size_stable(old_path, stability_time):
                    new_path = os.path.join(self.download_dir, new_filename)
                    os.rename(old_path, new_path)
                    print(f"✅ Renamed file to: {new_filename}")
                    return new_path
                else:
                    self.logger.error("File size did not stabilize within timeout")
                    return None
            time.sleep(1)
        
        self.logger.error("❌ Timed out waiting for download to complete")
        return None

    def run(self):
        """Execute the CSV download process"""
        driver = None
        try:
            driver = self._setup_driver(self.profile_path)
            self.logger.info(f"Opening URL: {self.url}")
            driver.get(self.url)
            self.logger.info("Waiting for page to load...")
            time.sleep(5)
            self.logger.info(f"Current page title: {driver.title}")
            self.logger.info(f"Current URL: {driver.current_url}")
            self.logger.info("Looking for Download CSV button")
            wait = WebDriverWait(driver, 10)
            try:
                export_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Download CSV')]")))
                self.logger.info("Found Download CSV button")
            except TimeoutException:
                self.logger.error("Could not find Download CSV button. Available buttons:")
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for button in buttons:
                    self.logger.info(f"Button text: {button.text}")
                raise
            self.logger.info("Clicking Download CSV button")
            export_button.click()
            time.sleep(5)
            print("✅ CSV Exported Successfully!")
            result_path = self.wait_and_rename_download()  # <== Rename step
            if result_path:
                return {"success": True, "file_path": result_path}
            else:
                return {"success": False, "error": "Download timed out"}
        except TimeoutException:
            self.logger.error("❌ Timed out waiting for elements on the page")
            return {"success": False, "error": "Element timeout"}
        except WebDriverException as e:
            self.logger.error(f"❌ WebDriver error: {str(e)}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            if driver:
                driver.quit()


if __name__ == '__main__':
    papc_server_id = '1059745565136654406'
    csv_downloader = CSVDownloader(
        server_id=papc_server_id,
        download_dir='/Users/qingyuan/Sandbox/PAPC_lottery/test_data'
    )
    result = csv_downloader.run()
    print(f'Download result: {result}')
