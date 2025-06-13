from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


def create_chrome_driver_with_logging(
        profile_path: str = "/tmp/selenium-profile",
        headless: bool = False,
        attach_to_debugger: bool = True,
        debugger_address: str = "127.0.0.1:9222",
) -> webdriver.Chrome:
    """
    Create a Chrome WebDriver instance with logging enabled.
    
    Args:
        profile_path (str): Path to Chrome profile directory. Defaults to "/tmp/selenium-profile".
        headless (bool): Whether to run Chrome in headless mode. Defaults to False.
        attach_to_debugger (bool): Whether to attach to an existing Chrome instance. Defaults to True.
        debugger_address (str): Address of the Chrome debugger. Defaults to "127.0.0.1:9222".
    
    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance
        
    Raises:
        WebDriverException: If ChromeDriver installation or browser launch fails
    """
    try:
        options = Options()
        options.add_argument(f"user-data-dir={profile_path}")
        options.add_argument("--start-maximized")

        # Attach to an already-running Chrome
        if attach_to_debugger:
            options.add_experimental_option("debuggerAddress", debugger_address)
            logger.info(f"🔗 Attaching to Chrome debugger at {debugger_address}")
        else:
            # Standard launch
            if headless:
                options.add_argument("--headless=new")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")

        # Enable browser log collection
        options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

        # Install and setup ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Log version information
        logger.info(f"🧭 Chrome version: {driver.capabilities['browserVersion']}")
        logger.info(f"🛠 Driver version: {driver.capabilities['chrome']['chromedriverVersion']}")

        return driver
    except Exception as e:
        logger.error(f"Failed to create Chrome WebDriver: {str(e)}")
        raise WebDriverException(f"Chrome WebDriver creation failed: {str(e)}")

def check_login_status(driver, base_url=None, timeout=5):
    """
    Check if user is logged in to sesh.fyi by looking for the user avatar in the navigation bar.
    
    Args:
        driver: Selenium WebDriver instance
        base_url: Optional URL to navigate to before checking (if None, assumes already on correct page)
        timeout: How long to wait for the avatar element (in seconds)
    
    Returns:
        bool: True if logged in, False otherwise
    """
    try:
        if base_url:
            driver.get(base_url)
            
        wait = WebDriverWait(driver, timeout)
        avatar = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".avatar-right-padding .is-rounded")))
        logger.info("✅ Successfully logged in to sesh.fyi")
        return True
    except TimeoutException:
        logger.error("❌ Not logged in to sesh.fyi")
        logger.info("Please log in to sesh.fyi and try again")
        return False

def wait_for_element(driver, selector, by=By.CSS_SELECTOR, timeout=10, clickable=False):
    """
    Wait for an element to be present and optionally clickable.
    
    Args:
        driver: Selenium WebDriver instance
        selector: Element selector
        by: Selector type (default: CSS_SELECTOR)
        timeout: How long to wait (in seconds)
        clickable: Whether to wait for element to be clickable
    
    Returns:
        WebElement: The found element
    """
    wait = WebDriverWait(driver, timeout)
    condition = EC.element_to_be_clickable if clickable else EC.presence_of_element_located
    return wait.until(condition((by, selector)))

def hide_tooltips(driver):
    """
    Hide any tooltips that might be blocking interactions.
    
    Args:
        driver: Selenium WebDriver instance
    """
    driver.execute_script("""
        document.querySelectorAll('.tooltip-v2').forEach(t => {
            t.style.display = 'none';
        });
    """)

def check_rate_limit(driver_or_event):
    """
    Check for rate limiting in both UI warnings and browser console.
    
    Args:
        driver_or_event: Either a Selenium WebDriver instance or a SeshDashboardEvent object
    
    Returns:
        bool: True if rate limited, False otherwise
    """
    # Get the driver instance
    driver = driver_or_event.driver if hasattr(driver_or_event, 'driver') else driver_or_event
    
    # Check UI warnings
    warning_keywords = ["too many", "slow down", "rate", "wait", "throttle", "requests"]
    warnings = driver.find_elements(By.CSS_SELECTOR, ".notification.is-warning")
    for w in warnings:
        if w.is_displayed():
            text = w.text.lower()
            logger.warning(f"⚠️ UI Warning: {text}")
            if any(keyword in text for keyword in warning_keywords):
                logger.error("🚫 Detected possible rate limiting.")
                return True

    # Check browser console logs
    try:
        logs = driver.get_log("browser")
        for entry in logs:
            if any(word in entry['message'].lower() for word in ["429", "throttle", "too many"]):
                logger.error(f"🚫 Detected rate limit from browser log: {entry['message']}")
                return True
    except:
        logger.info("ℹ️ Could not access browser logs (possibly unsupported driver)")
    
    return False

def retry_with_rate_limit_check(func, max_retries=2, delay=30):
    """
    Decorator to retry a function with rate limit checking.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    
    Returns:
        The result of the function if successful
    """
    def wrapper(self, *args, **kwargs):
        for attempt in range(max_retries + 1):
            try:
                return func(self, *args, **kwargs)
            except TimeoutException as e:
                if check_rate_limit(self.driver):
                    if attempt < max_retries:
                        logger.warning(f"⏸️ Rate limited, waiting {delay} seconds before retry...")
                        time.sleep(delay)
                        continue
                raise e
    return wrapper 