import json, time, random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
import getTotp # Import the new library

def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))

def human_click(driver, element):
    ActionChains(driver).move_to_element(element).pause(random.uniform(0.1, 0.3)).click().perform()

def get_cookies(account, password, otp_keys_data):
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--headless')
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    try:
        driver.get("https://psu.instructure.com/login")
        wait = WebDriverWait(driver, 30)
        
        human_type(wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))), account)
        human_click(driver, driver.find_element(By.CSS_SELECTOR, "input[type='submit']"))
        
        human_type(wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']"))), password)
        human_click(driver, driver.find_element(By.CSS_SELECTOR, "input[type='submit']"))
        
        start_time = time.time()
        while time.time() - start_time < 30:
            if "I can't use my Microsoft Authenticator" in driver.page_source:
                human_click(driver, driver.find_element(By.PARTIAL_LINK_TEXT, "I can't use my Microsoft Authenticator"))
                human_click(driver, wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Use a verification code')]"))))
                break
            elif "Use a verification code" in driver.page_source:
                human_click(driver, wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Use a verification code')]"))))
                break
            elif "Sorry, but we’re having trouble signing you in" in driver.page_source:
                time.sleep(1)
                continue
            else:
                time.sleep(0.5)
        else:
            raise Exception("2FA page timed out.")
        
        sso_success = False
        for attempt in range(3):
            token = getTotp.generate_token(otp_keys_data) # Pass the key data directly
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
                if "Sorry, but we’re having trouble signing you in" not in driver.page_source and attempt < 2:
                    raise Exception("SSO failed with an unexpected error.")
                driver.back()
                time.sleep(1)
                driver.back()
                time.sleep(1)
                human_click(driver, wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Use a verification code')]"))))
        if not sso_success:
            raise Exception("SSO submission failed after 3 retries.")
        
        cookies = driver.get_cookies()
        return cookies
    except Exception as e:
        print(f"An error occurred in get_cookies: {e}")
        driver.save_screenshot('error_screenshot.png')
        return None
    finally:
        driver.quit()
