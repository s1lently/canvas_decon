import requests, json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config

def get_api(path):
    with open(config.COOKIES_FILE) as f:
        cookies = {c['name']: c['value'] for c in json.load(f)}
    
    url = f"https://psu.instructure.com{'/api/v1' if not path.startswith('/api') else ''}{path if path.startswith('/') else '/'+path}"
    r = requests.get(url, cookies=cookies, headers={'Accept': '*/*'})
    
    try:
        json.dump(r.json(), open('test.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    except:
        open('test.html', 'w', encoding='utf-8').write(r.text)

if __name__ == '__main__':
    get_api("courses/2418560/modules/5767693/items")
