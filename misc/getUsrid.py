import json
import requests

def test_api():
    # Load cookies
    with open('cookies.json', 'r') as f:
        cookies = {c['name']: c['value'] for c in json.load(f)}
    
    # Setup session
    session = requests.Session()
    for name, value in cookies.items():
        session.cookies.set(name, value, domain='psu.instructure.com')
    
    # Test: GET /api/v1/users/self
    resp = session.get("https://psu.instructure.com/api/v1/users/self")
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_api()
