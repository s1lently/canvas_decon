"""
Status checker for Canvas LMS Automation GUI
Returns: 0 (red - no/fail), 1 (green - success/yes), 2 (yellow - maybe/invalid)
"""
import os
import json
import requests
import config

def _load_json_file(filepath):
    """Load and parse JSON file, return None if error"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, Exception):
        pass
    return None

def check_account_info():
    """Check if account_info.json exists and is valid"""
    data = _load_json_file(config.ACCOUNT_INFO_FILE)
    if data is None:
        return 0

    required_keys = {'account', 'password', 'otp_key'}
    if set(data.keys()) == required_keys and all(isinstance(v, str) and v for v in data.values()):
        return 1

    return 2


def check_cookie_validity():
    """Check if cookies.json exists and is valid"""
    from datetime import datetime, timedelta

    cookies = _load_json_file(config.COOKIES_FILE)
    if cookies is None:
        return 0

    # Check file age
    file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(config.COOKIES_FILE))
    if file_age > timedelta(hours=24):
        return 2

    # Validate format
    if not isinstance(cookies, list) or not cookies:
        return 2

    # Test with Canvas API
    try:
        cookie_dict = {c['name']: c['value'] for c in cookies}
        resp = requests.get(
            'https://psu.instructure.com/api/v1/users/self',
            cookies=cookie_dict,
            headers={'Accept': 'application/json'},
            timeout=5
        )
        return 1 if resp.status_code == 200 else 2
    except (requests.RequestException, Exception):
        return 2


def _check_json_data_file(filepath):
    """Generic checker for JSON data files (todos.json, course.json)"""
    data = _load_json_file(filepath)
    if data is None:
        return 0
    return 1 if isinstance(data, (list, dict)) and data else 0


def check_todo_list():
    """Check if todos.json exists and has valid content"""
    return _check_json_data_file(config.TODOS_FILE)


def check_network():
    """Check if network access to Canvas API works"""
    try:
        resp = requests.get('https://psu.instructure.com/api/v1/users/self', timeout=5)
        return 1 if resp.status_code in [200, 401, 403] else 2
    except requests.RequestException:
        return 0


def check_course_list():
    """Check if course.json exists and is valid"""
    return _check_json_data_file(os.path.join(os.path.dirname(__file__), 'course.json'))


def get_all_status():
    """Get all status indicators at once"""
    return {
        'account': check_account_info(),
        'cookie': check_cookie_validity(),
        'todos': check_todo_list(),
        'network': check_network(),
        'courses': check_course_list()
    }


if __name__ == '__main__':
    # Test all status checks
    status = get_all_status()
    status_names = {0: 'RED', 1: 'GREEN', 2: 'YELLOW'}

    print("Status Check Results:")
    print(f"Account Info: {status_names[status['account']]}")
    print(f"Cookie Valid: {status_names[status['cookie']]}")
    print(f"TODO List: {status_names[status['todos']]}")
    print(f"Network: {status_names[status['network']]}")
    print(f"Course List: {status_names[status['courses']]}")
