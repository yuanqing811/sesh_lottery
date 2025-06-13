# the purpose of this script is to test if I can add event participants to the list of attendees

# I would like to write a script that automates scheduled data download like the event csv file
# Write scripts that automatically import the exported CSV files into your database.
# 1. Scheduled Exports:
# Set up a schedule to export data from Sesh Bot at regular intervals.
# 2. Automated Import Scripts:
# Write scripts that automatically import the exported CSV files into your database.
# identify the chrome session

# /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/Library/Application Support/Google/Chrome/SeleniumProfile"
# go to sesh.fyi and login

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from sesh_dashboard.selenium_utils import (
    create_chrome_driver_with_logging,
    check_login_status,
    wait_for_element,
    hide_tooltips,
    check_rate_limit,
    retry_with_rate_limit_check
)
from sesh_dashboard.utils import chunk_list


class SeshDashboardEvent:
    def __init__(self, server_id):
        self.base_url = f'https://sesh.fyi/dashboard/{server_id}'
        self.profile_path = "/tmp/selenium-profile"  # macOS example
        self.driver = create_chrome_driver_with_logging(profile_path=self.profile_path)

    def is_logged_into_sesh(self):
        """Check if user is logged in to sesh.fyi"""
        return check_login_status(self.driver, self.base_url)

    def hide_tooltips(self):
        self.driver.execute_script("""
          document.querySelectorAll('.tooltip-v2').forEach(t => {
            t.style.display = 'none';
          });
        """)

    def check_browser_logs_for_rate_limit(self):
        # Optional: Add Console Log Detection (Chrome Only)
        try:
            logs = self.driver.get_log("browser")
            for entry in logs:
                if any(word in entry['message'].lower() for word in ["429", "throttle", "too many"]):
                    print("🚫 Detected rate limit from browser log:", entry['message'])
                    return True
        except:
            print("ℹ️ Could not access browser logs (possibly unsupported driver)")
        return False

    def check_UI_warning_for_rate_limit(self):
        warning_keywords = ["too many", "slow down", "rate", "wait", "throttle", "requests"]

        warnings = self.driver.find_elements(By.CSS_SELECTOR, ".notification.is-warning")
        for w in warnings:
            if w.is_displayed():
                text = w.text.lower()
                print(f"⚠️ UI Warning: {text}")
                if any(keyword in text for keyword in warning_keywords):
                    print("🚫 Detected possible rate limiting.")
                    return True
        return False

    def is_rate_limited(self):
        # 1️⃣ Check UI warnings
        if self.check_UI_warning_for_rate_limit():
            return True

        # 2️⃣ Check browser console logs (Chrome only)
        rate_limited = self.check_browser_logs_for_rate_limit()
        return rate_limited

    @retry_with_rate_limit_check
    def open_add_user_modal(self, modal_name, retries=2):
        if modal_name not in ['Attendee', 'Lottery']:
            raise Exception(f'unknown group {modal_name}')

        print(f"Looking for Add button for {modal_name} list...")
        
        # Try different selectors for the Add button
        selectors = [
            f"//span[contains(., '{modal_name}')]/ancestor::div[contains(@class, 'items-center')]/div//span[text()='Add']",  # Original selector
            f"//span[text()='Add' and ancestor::div[contains(., '{modal_name}')]]",  # Simpler XPath
            f"//button[contains(., 'Add {modal_name}')]",  # Button with text
            f"//span[text()='Add']"  # Any Add span
        ]

        add_span = None
        for selector in selectors:
            try:
                print(f"Trying selector: {selector}")
                add_span = wait_for_element(
                    self.driver,
                    selector,
                    by=By.XPATH,
                    clickable=True,
                    timeout=5
                )
                if add_span:
                    print(f"Found Add button with selector: {selector}")
                    break
            except TimeoutException:
                continue

        if not add_span:
            print("❌ Could not find Add button. Available elements:")
            elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Add') or contains(text(), 'Attendee') or contains(text(), 'Lottery')]")
            for elem in elements:
                print(f"Element text: {elem.text}")
            raise TimeoutException("Could not find Add button")

        # 2. Hover over the span (to trigger tooltips, dropdowns, or React events)
        ActionChains(self.driver).move_to_element(add_span).perform()
        time.sleep(0.5)  # Small pause for any hover UI

        # 3. Hide any tooltips that may have appeared
        hide_tooltips(self.driver)

        # 4. Dispatch a JS mouse click to trigger React modal
        self.driver.execute_script("""
            arguments[0].dispatchEvent(new MouseEvent('click', {
                bubbles: true, cancelable: true, view: window
            }));
        """, add_span)

        # 5. Wait for the modal to open and become active
        modal = wait_for_element(
            self.driver,
            "div.modal.is-active",
            timeout=10
        )
        print("✅ Modal Opened Successfully!")
        return modal

    def prompt_to_select_multiple_options(self, option_texts):
        # print all the options and ask the user to select
        print("🔍 ✅ Multiple Options found:")
        for i, option_text in enumerate(option_texts):
            print(f"  [{i}] {option_text}")

        # Step 5: Prompt user for selection
        while True:
            try:
                selection = int(input("👉 Enter the number of the option to select: "))
                if 0 <= selection < len(option_texts):
                    # Re-locate the dropdown options to avoid stale reference
                    fresh_options = self.driver.find_elements(By.CSS_SELECTOR, "div.sesh-dropdown__option")
                    fresh_options[selection].click()
                    print(f"✅ Selected: {option_texts[selection]}")
                    break
                else:
                    print(f"❌ Invalid selection. Enter a number from 0 to {len(option_texts) - 1}.")
            except ValueError:
                print("⚠️ Please enter a valid number.")

    def add_users_from_modal(self, list_name, users):
        """
        Select users from the Sesh "Add Users" modal using Selenium.
        1. Open the modal
        2. Type a user's name
        3. Wait for the dropdown options
        4. Select the matching user
        Repeat as needed
        """
        print(users)
        modal = self.open_add_user_modal(list_name)

        # Find the input box inside the modal
        input_box = wait_for_element(
            modal,
            "input.sesh-dropdown__input",
            clickable=True
        )
        self.driver.execute_script("arguments[0].focus();", input_box)

        for user in users:
            # 1. Clear search text
            input_box.clear()
            time.sleep(0.2)

            # 2. Type a user's name
            input_box.send_keys(user)
            print(f'Entered user: {user}')

            # 3. Wait for the dropdown option(s) to appear
            try:
                options = wait_for_element(
                    self.driver,
                    "div.sesh-dropdown__option",
                    timeout=10
                )
            except TimeoutException:
                print(f"❌ No dropdown options available (zero matches) for {user}")
                raise

            # Find all dropdown options
            options = self.driver.find_elements(By.CSS_SELECTOR, "div.sesh-dropdown__option")
            option_texts = [opt.text.strip() for opt in options]

            # Handle different cases
            if not options:
                print(f"❌ No options available for {user}")
            elif len(options) == 1:
                if option_texts[0] == user:
                    print(f"✅ Selected: {option_texts[0]}")
                    options[0].click()
                else:
                    print(f"⚠️ No exact match for '{user}', "
                          f"selecting first option: {option_texts[0]}")
            else:   # multiple options
                found_match = False
                for i, option_text in enumerate(option_texts):
                    if option_text == user:
                        options[i].click()
                        found_match = True
                        break

                if not found_match:
                    # print all the options and ask the user to select
                    self.prompt_to_select_multiple_options(option_texts)

        # Visually confirm by printing selected users
        selected = modal.find_elements(By.CSS_SELECTOR, ".sesh-dropdown__multi-value__label")
        print([s.text for s in selected])

        self.submit_and_close_modal()

    @retry_with_rate_limit_check
    def submit_and_close_modal(self):
        # Find the modal
        modal = wait_for_element(
            self.driver,
            "div.modal.is-active",
            timeout=10
        )

        # Find and click the "Add Users" button
        add_user_button = wait_for_element(
            modal,
            ".//button[.//span[contains(text(),'Add Users')]]",
            by=By.XPATH,
            clickable=True
        )

        # Click the button via JavaScript
        self.driver.execute_script("arguments[0].click();", add_user_button)
        time.sleep(1)  # Wait for the modal to close

    def add_users_to_list(self, event_id, list_name, users, debug=True):
        """Add users to a specific list in an event"""
        if debug:
            print(f"Adding {len(users)} users to {list_name} list in event {event_id}")
        
        # Navigate to the event page
        self.driver.get(f"{self.base_url}/events/attendees/{event_id}")
        time.sleep(2)  # Wait for page load
        
        # Add users through the modal
        self.add_users_from_modal(list_name, users)

    def add_attendees_to_event(self, event_id, attendees, list_name='Attendee', debug=True):
        """Add attendees to an event"""
        if debug:
            print(f"Adding {len(attendees)} attendees to event {event_id}")
        
        # Add attendees in chunks to avoid rate limiting
        for chunk in chunk_list(attendees, 5):
            self.add_users_to_list(event_id, list_name, chunk, debug)
            time.sleep(2)  # Small delay between chunks


if __name__ == '__main__':
    import yaml

    with open("output/Clinic_sesh_dashboard_data.yaml", "r") as f:
        events = list(yaml.safe_load_all(f))
        for event in events:
            server_id = event['server_id']
            event_id = event['event_id']
            add_to_lottery = event['add_to_lottery']
            add_to_attendee = event['add_to_attendee']
            sesh_event_add_attendees = SeshDashboardEvent(server_id=server_id)
            if add_to_lottery:
                sesh_event_add_attendees.add_attendees_to_event(
                    event_id=event_id, 
                    attendees=add_to_lottery,
                    list_name='Lottery'
                )
            if add_to_attendee:
                sesh_event_add_attendees.add_attendees_to_event(
                    event_id=event_id,
                    attendees=add_to_attendee,
                    list_name='Attendee'
                )
