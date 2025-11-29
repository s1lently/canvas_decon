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


def main(progress=None):
    """Fetch courses and tabs

    Args:
        progress: TaskProgress instance (optional)
    """
    if progress:
        progress.update(progress=0, status="Fetching courses...")
    print("Fetching courses...")

    try:
        raw_courses = get_data()
        total = len(raw_courses)
        if progress:
            progress.update(progress=20, status=f"Found {total} courses")
        print(f"Found {total} courses")

        courses = []
        for i, c in enumerate(raw_courses):
            tabs = get_data(f"/{c['id']}/tabs")
            courses.append({
                'id': c['id'],
                'name': c['name'],
                'tabs': {t['label']: t['html_url'].replace(config.CANVAS_BASE_URL, '') for t in tabs}
            })
            pct = 20 + int((i + 1) / total * 70)
            if progress:
                progress.update(progress=pct, status=f"Processing {i+1}/{total}")
            print(f"\r  Processing: {i+1}/{total}", end='', flush=True)

        data = {'base_url': config.CANVAS_BASE_URL, 'courses': courses}
        with open(config.COURSE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        if progress:
            progress.finish(f"Saved {total} courses")
        print(f"\n✓ Saved {total} courses")

    except Exception as e:
        if progress:
            progress.fail(str(e))
        print(f"Error: {e}")


if __name__ == '__main__':
    main()