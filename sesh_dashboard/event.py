# the purpose of this script is to test if I can add event participants to the list of attendees

# I would like to write a script that automates scheduled data download like the event csv file
# Write scripts that automatically import the exported CSV files into your database.
# 1. Scheduled Exports:
# Set up a schedule to export data from Sesh Bot at regular intervals.
# 2. Automated Import Scripts:
# Write scripts that automatically import the exported CSV files into your database.
# identify the chrome session

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from sesh_dashboard.utils import create_chrome_driver_with_logging, chunk_list


class SeshDashboardEvent:
    def __init__(self, server_id):
        self.base_url = f'https://sesh.fyi/dashboard/{server_id}'
        self.profile_path = "/tmp/selenium-profile"  # macOS example
        self.driver = create_chrome_driver_with_logging(profile_path=self.profile_path)

    def is_logged_into_sesh(self):
        try:
            # Look for a UI element that only appears when logged in
            self.driver.get(self.base_url)

            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".navbar-user-avatar"))
            )
            return True
        except:
            return False

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

    def open_add_user_modal(self, modal_name, retries=2):
        if modal_name not in ['Attendee', 'Lottery']:
            raise Exception(f'unknown group {modal_name}')

        # Simulate hovering over the “Add” button (a span) and then trigger a click to open the modal
        # — reliably, even in React.

        # 1. Wait for the "Add" span near the "modal_name" text to appear
        wait = WebDriverWait(self.driver, 10)

        for attempt in range(retries + 1):
            try:
                add_span_html = f"//span[contains(., '{modal_name}')]/ancestor::div[contains(@class, 'items-center')]/div//span[text()='Add']"
                add_span = wait.until(EC.presence_of_element_located((
                    By.XPATH, add_span_html
                )))

                # 2. Hover over the span (to trigger tooltips, dropdowns, or React events)
                ActionChains(self.driver).move_to_element(add_span).perform()

                # Small pause for any hover UI, such as tooltip, to activate and render fully
                time.sleep(0.5)

                # 3. Force-hide any tooltip that may have appeared
                # Sesh (like many modern UIs) attaches tooltips to the DOM separately and
                # overlays them with a z-index. Even if the tooltip is not visibly “blocking”
                # the button, it may still consume mouse events like click.
                self.hide_tooltips()

                # 4. Dispatch a JS mouse click to trigger React modal
                self.driver.execute_script("""
                  arguments[0].dispatchEvent(new MouseEvent('click', {
                    bubbles: true, cancelable: true, view: window
                  }));
                """, add_span)

                # 4. Wait for the modal to open
                # First wait for the modal container to appear (even before it's active)
                wait.until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, "div.modal"
                    ))
                )

                # Then wait for it to become active
                modal = wait.until(
                    EC.visibility_of_element_located((
                        By.CSS_SELECTOR, "div.modal.is-active"
                    ))
                )
                print("✅ Modal Opened Successfully!")
                return modal
            except TimeoutException:
                print(f"⚠️ Modal failed to open (attempt {attempt + 1})")
                if self.is_rate_limited():
                    print("⏸️ Pausing 30 seconds to recover from rate limit...")
                    time.sleep(30)

                time.sleep(0.5)
        print(f"❌ Modal failed to open after {retries} attempts. — possible lockout or throttling, giving up...")
        return None

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
        Select users from the Sesh “Add Users” modal using Selenium.
        1. Open the modal
        2. Type a user’s name
        3. Wait for the dropdown options
        4. Select the matching user
        Repeat as needed
        """

        modal = self.open_add_user_modal(list_name)

        # Find the input box inside the modal
        input_box = modal.find_element(By.CSS_SELECTOR, "input.sesh-dropdown__input")
        self.driver.execute_script("arguments[0].focus();", input_box)
        wait = WebDriverWait(self.driver, 10)

        for user in users:
            # 1. Clear search text (safe — won't touch selected users)
            input_box.clear()  # OR input_box.send_keys(Keys.CONTROL + "a", Keys.DELETE)
            time.sleep(0.2)

            # 2. Type a user's name
            input_box.send_keys(user)
            print(f'Entered user: {user}')

            # 3. Wait for the dropdown option(s) to appear
            try:
                wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, "div.sesh-dropdown__option"
                )))
            except TimeoutException:
                print(f"❌ No dropdown options available (zero matches) for {user}")
                raise

            # Find all dropdown options
            options = self.driver.find_elements(By.CSS_SELECTOR, "div.sesh-dropdown__option")
            option_texts = [opt.text.strip() for opt in options]

            # Step 2: Try to locate at least one option
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

    def submit_and_close_modal(self):
        # 🔍 Step 1: Find the modal (already opened before this step)
        modal = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.modal.is-active"))
        )

        # 🧭 Step 2: Locate and click the "Add Users" button inside the modal
        try:
            add_user_button = WebDriverWait(modal, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    # ".//span[text()='Add Users']/ancestor::button"
                    ".//button[.//span[contains(text(),'Add Users')]]"
                ))
            )

            # 🖱️ Step 3: Click the button via JavaScript (React-safe)
            # This avoids issues with overlays or animation transitions.
            self.driver.execute_script("arguments[0].click();", add_user_button)
            print("✅ Clicked 'Add Users'")
        except:
            print("❌ Could not find or click 'Add Users' button")
            raise

        # 2. Wait for modal to disappear
        wait = WebDriverWait(self.driver, 10)
        try:
            wait.until(
                EC.invisibility_of_element_located((
                    By.CSS_SELECTOR, "div.modal.is-active"
                ))
            )
            print("✅ Modal closed successfully")
            return
        except:
            print("❌ Modal did not close after submitting")

        # if modal is not already closed
        modal_close = modal.find_element(By.CSS_SELECTOR, "button.modal-close")
        self.driver.execute_script("arguments[0].click();", modal_close)
        print("❎ Modal close button clicked.")

        # Wait until the modal is no longer visible
        try:
            wait.until(
                EC.invisibility_of_element_located((
                    By.CSS_SELECTOR, "div.modal.is-active"
                ))
            )
            print("✅ Modal has been closed.")
        except:
            print("❌ Modal did not close after submitting")
            raise

    def add_users_to_list(self, event_id, list_name, users, debug=True):
        event_url = f'{self.base_url}/events/attendees/{event_id}'
        try:
            # Step 1: Open the Sesh Dashboard event list page
            self.driver.get(event_url)

            # Wait until the page is loaded (optional but recommended)
            self.driver.implicitly_wait(10)

            batches = chunk_list(users, 5)
            for i, batch in enumerate(batches, 1):
                print(f"Batch {i}: {batch}")
                self.add_users_from_modal(list_name, batch)

        except Exception as e:
            print("❌ Error:", e)
        finally:
            if not debug:
                self.driver.quit()

    def add_attendees_to_event(self, event_id, attendees, debug=True):
        self.add_users_to_list(event_id=event_id, list_name='Attendee', users=attendees, debug=debug)


if __name__ == '__main__':
    import yaml

    with open("../output/Clinic_sesh_dashboard_data.yaml", "r") as f:
        events = list(yaml.safe_load_all(f))
        for event in events:
            server_id = event['server_id']
            event_id = event['event_id']
            add_to_lottery = event['add_to_lottery']
            add_to_attendee = event['add_to_attendee']
            sesh_event_add_attendees = SeshDashboardEvent(server_id=server_id)
            sesh_event_add_attendees.add_users_to_list(event_id=event_id,
                                                       users=add_to_lottery,
                                                       list_name='Lottery')
            sesh_event_add_attendees.add_users_to_list(event_id=event_id,
                                                       users=add_to_attendee,
                                                       list_name='Attendee')
