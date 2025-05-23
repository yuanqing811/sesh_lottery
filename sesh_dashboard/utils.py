# the purpose of this script is to test if I can add event participants to the list of attendees

# I would like to write a script that automates scheduled data download like the event csv file
# Write scripts that automatically import the exported CSV files into your database.
# 1. Scheduled Exports:
# Set up a schedule to export data from Sesh Bot at regular intervals.
# 2. Automated Import Scripts:
# Write scripts that automatically import the exported CSV files into your database.
# identify the chrome session

import chromedriver_autoinstaller

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# Attach to an existing Chrome (launched with debugging port)
# 1. launch google chrome manually in debugging mode
# /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome
# --remote-debugging-port=9222 --user-data-dir="/tmp/selenium-profile"
# --disable-gpu --disable-software-rasterizer

def create_chrome_driver_with_logging(
        profile_path="/tmp/selenium-profile",
        headless=False,
        attach_to_debugger=True,
        debugger_address="127.0.0.1:9222",
):
    # 🔄 Auto-install matching ChromeDriver
    chromedriver_autoinstaller.install()

    options = Options()

    options.add_argument(f"user-data-dir={profile_path}")
    options.add_argument("--start-maximized")

    # Attach to an already-running Chrome (e.g. launched with --remote-debugging-port=9222)
    if attach_to_debugger:
        options.debugger_address = debugger_address
        print(f"🔗 Attaching to Chrome debugger at {debugger_address}")

    else:
        # Standard launch
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")

    # ✅ Enable browser log collection
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    driver = webdriver.Chrome(options=options)

    print(f"🧭 Chrome version: {driver.capabilities['browserVersion']}")
    print(f"🛠 Driver version: {driver.capabilities['chrome']['chromedriverVersion']}")

    return driver


def chunk_list(users, chunk_size=5):
    return [users[i:i + chunk_size] for i in range(0, len(users), chunk_size)]
