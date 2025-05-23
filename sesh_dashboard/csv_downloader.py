import os
import time
from datetime import datetime
from utils import create_chrome_driver_with_logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


class CSVDownloader:
    def __init__(self, server_id,
                 profile_path="/tmp/selenium-profile",  # macOS example
                 download_dir="/Users/qingyuan/Downloads"):

        self.server_id = server_id

        self.url = f'https://sesh.fyi/dashboard/{self.server_id}/events?view=list'
        self.download_dir = download_dir

        self.driver = create_chrome_driver_with_logging(profile_path=profile_path)
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": download_dir
        })

    def wait_and_rename_download(self,
                                 original_suffix=".csv",
                                 timeout=30):
        date_str = datetime.now().strftime("%Y-%m-%d")
        new_filename = f"events_{self.server_id}_{date_str}.csv"
        elapsed = 0
        while elapsed < timeout:
            files = [f for f in os.listdir(self.download_dir) if
                     f.endswith(original_suffix) and not f.endswith(".crdownload")]
            if files:
                old_path = os.path.join(self.download_dir, files[0])
                new_path = os.path.join(self.download_dir, new_filename)
                os.rename(old_path, new_path)
                print(f"✅ Renamed file to: {new_filename}")
                return
            time.sleep(1)
            elapsed += 1
        print("❌ Timed out waiting for download to complete.")

    def run(self):
        try:
            # Step 1: Open the Sesh Dashboard event list page
            self.driver.get(self.url)
            time.sleep(5)

            # Step 2: Navigate to the Export Button
            wait = WebDriverWait(self.driver, 10)
            export_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Download CSV')]")))
            export_button.click()
            time.sleep(5)
            print("✅ CSV Exported Successfully!")
            self.wait_and_rename_download()  # <== Rename step
        except Exception as e:
            raise("❌ Error:", e)


if __name__ == '__main__':
    papc_server_id = '1059745565136654406'
    csv_downloader = CSVDownloader(
        server_id=papc_server_id,
        download_dir='/Users/qingyuan/Sandbox/PAPC_lottery/test_data'
    )
    csv_downloader.run()
