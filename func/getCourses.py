import requests, json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def get_data(endpoint=''):
    with open(config.COOKIES_FILE) as f:
        cookies = {c['name']: c['value'] for c in json.load(f)}
    url = f"{config.CANVAS_BASE_URL}/api/v1/courses{endpoint}"
    return requests.get(url, cookies=cookies, headers={'Accept': 'application/json'}).json()

def main():
    try:
        courses = [{'id': c['id'],
                   'name': c['name'],
                   'tabs': {t['label']: t['html_url'].replace(config.CANVAS_BASE_URL, '') for t in get_data(f"/{c['id']}/tabs")}}
                  for c in get_data()]
        data = {'base_url': config.CANVAS_BASE_URL, 'courses': courses}
        with open(config.COURSE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()