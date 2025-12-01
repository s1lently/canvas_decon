"""Canvas cookie retrieval via Selenium login"""
import json, time, random, sys, os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from func import logTotp


def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))


def human_click(driver, element):
    ActionChains(driver).move_to_element(element).pause(random.uniform(0.1, 0.3)).click().perform()


def get_cookies(account, password, otp_key, progress=None):
    """Get cookies via Selenium login

    Args:
        progress: TaskProgress instance (optional)
    """
    if progress:
        progress.update(progress=5, status="Starting browser...")
    print("Starting browser...")

    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    try:
        if progress:
            progress.update(progress=10, status="Loading login page...")
        driver.get("https://psu.instructure.com/login")
        wait = WebDriverWait(driver, 30)

        if progress:
            progress.update(progress=20, status="Entering account...")
        human_type(wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))), account)
        human_click(driver, driver.find_element(By.CSS_SELECTOR, "input[type='submit']"))

        if progress:
            progress.update(progress=30, status="Entering password...")
        human_type(wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']"))), password)
        human_click(driver, driver.find_element(By.CSS_SELECTOR, "input[type='submit']"))

        # Check if manual 2FA mode (otp_key == "loginself")
        manual_mode = (otp_key == "loginself")

        if manual_mode:
            if progress:
                progress.update(progress=40, status="Manual 2FA - complete in browser")
            print("\n" + "="*80)
            print("MANUAL 2FA MODE ENABLED")
            print("="*80)
            print("Please complete the 2FA verification in the browser window.")
            print("The script will wait for you to reach the Canvas dashboard...")
            print("="*80 + "\n")

            try:
                wait_long = WebDriverWait(driver, 300)
                wait_long.until(EC.presence_of_element_located((By.ID, "dashboard")))
                if progress:
                    progress.update(progress=80, status="Dashboard detected!")
                print("[SUCCESS] Login completed! Dashboard detected.")
                sso_success = True
            except TimeoutException:
                raise Exception("Timed out waiting for manual 2FA completion (5 minutes)")
        else:
            if progress:
                progress.update(progress=40, status="Waiting for 2FA page...")
            start_time = time.time()
            while time.time() - start_time < 30:
                if "I can't use my Microsoft Authenticator" in driver.page_source:
                    human_click(driver, driver.find_element(By.PARTIAL_LINK_TEXT, "I can't use my Microsoft Authenticator"))
                    human_click(driver, wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Use a verification code')]"))))
                    break
                elif "Use a verification code" in driver.page_source:
                    human_click(driver, wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Use a verification code')]"))))
                    break
                elif "Sorry, but we're having trouble signing you in" in driver.page_source:
                    time.sleep(1)
                    continue
                else:
                    time.sleep(0.5)
            else:
                raise Exception("2FA page timed out.")

            sso_success = False
            for attempt in range(3):
                if progress:
                    progress.update(progress=50 + attempt * 10, status=f"TOTP attempt {attempt+1}/3...")
                token = logTotp.generate_token(otp_key)
                if not token:
                    time.sleep(5)
                    continue
                try:
                    human_type(wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='tel']"))), token)
                except TimeoutException:
                    driver.back()
                    time.sleep(1)
                    continue
                human_click(driver, wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='idSubmit_SAOTCC_Continue']"))))
                try:
                    WebDriverWait(driver, 20).until(EC.any_of(
                        EC.presence_of_element_located((By.ID, "dashboard")),
                        EC.presence_of_element_located((By.ID, "idBtn_Back"))
                    ))
                    if len(driver.find_elements(By.ID, "idBtn_Back")) > 0:
                        human_click(driver, driver.find_element(By.ID, "idBtn_Back"))
                    wait.until(EC.presence_of_element_located((By.ID, "dashboard")))
                    sso_success = True
                    break
                except TimeoutException:
                    if "Sorry, but we're having trouble signing you in" not in driver.page_source and attempt < 2:
                        raise Exception("SSO failed with an unexpected error.")
                    driver.back()
                    time.sleep(1)
                    driver.back()
                    time.sleep(1)
                    human_click(driver, wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Use a verification code')]"))))
            if not sso_success:
                raise Exception("SSO submission failed after 3 retries.")

        if progress:
            progress.update(progress=85, status="Getting cookies...")
        cookies = driver.get_cookies()
        return cookies
    except Exception as e:
        print(f"An error occurred in get_cookies: {e}")
        driver.save_screenshot('error_screenshot.png')
        return None
    finally:
        driver.quit()


def main(progress=None):
    """Main function to get cookies and save to cookies.json"""
    if progress:
        progress.update(progress=0, status="Reading config...")

    try:
        with open(config.ACCOUNT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            account_info = json.load(f)
    except FileNotFoundError:
        err = f"{config.ACCOUNT_CONFIG_FILE} not found"
        if progress:
            progress.fail(err)
        print(f"Error: {err}")
        return
    except json.JSONDecodeError:
        err = f"Invalid JSON in {config.ACCOUNT_CONFIG_FILE}"
        if progress:
            progress.fail(err)
        print(f"Error: {err}")
        return

    account = account_info.get('account')
    password = account_info.get('password')
    otp_key = account_info.get('otp_key')

    if not all([account, password, otp_key]):
        err = "Missing required fields (account, password, otp_key)"
        if progress:
            progress.fail(err)
        print(f"Error: {err}")
        return

    if otp_key == "loginself":
        print(f"Logging in with account: {account} (Manual 2FA mode)")
    else:
        print(f"Logging in with account: {account}")

    cookies = get_cookies(account, password, otp_key, progress=progress)

    if cookies:
        if progress:
            progress.update(progress=95, status="Saving cookies...")
        with open(config.COOKIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2)
        if progress:
            progress.finish("Cookies saved!")
        print(f"Cookies saved successfully to {config.COOKIES_FILE}")
    else:
        err = "Failed to get cookies"
        if progress:
            progress.fail(err)
        print(err)


if __name__ == "__main__":
    main()
