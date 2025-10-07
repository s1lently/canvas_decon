import requests, json

def get_data(endpoint=''):
    with open('cookies.json') as f:
        cookies = {c['name']: c['value'] for c in json.load(f)}
    url = f"https://psu.instructure.com/api/v1/courses{endpoint}"
    return requests.get(url, cookies=cookies, headers={'Accept': 'application/json'}).json()

def main():
    try:
        courses = [{'id': c['id'], 
                   'name': c['name'],
                   'tabs': {t['label']: t['html_url'].replace('https://psu.instructure.com', '') for t in get_data(f"/{c['id']}/tabs")}} 
                  for c in get_data()]
        data = {'base_url': 'https://psu.instructure.com', 'courses': courses}
        with open('course.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()