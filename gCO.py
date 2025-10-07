import requests, json

def get_data(endpoint=''):
    with open('cookies.json') as f:
        cookies = {c['name']: c['value'] for c in json.load(f)}
    url = f"https://psu.instructure.com/api/v1/courses{endpoint}"
    return requests.get(url, cookies=cookies, headers={'Accept': 'application/json'}).json()

def main():
    try:
        courses = get_data()
        for course in courses:
            print(f"\n{'='*80}")
            print(f"Course: {course.get('name', 'Unknown')} (ID: {course.get('id')})")
            print(f"{'='*80}")
            tabs = get_data(f"/{course['id']}/tabs")
            print(json.dumps(tabs, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()

