from selenium import webdriver
import json
import time

driver = webdriver.Chrome()

try:
    with open('cookies.json', 'r') as f:
        cookies = json.load(f)
    
    for cookie in cookies:
        driver.execute_cdp_cmd('Network.setCookie', {
            'name': cookie['name'], 'value': cookie['value'], 'domain': cookie['domain'],
            'path': cookie.get('path', '/'), 'httpOnly': cookie.get('httpOnly', False),
            'secure': cookie.get('secure', False), 'sameSite': cookie.get('sameSite', 'Lax'),
            'expires': cookie.get('expiry', int(time.time()) + 86400)
        })
    
    driver.get("https://psu.instructure.com/")
    print("✓ Canvas已打开，按Ctrl+C关闭")
    
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    driver.quit()

