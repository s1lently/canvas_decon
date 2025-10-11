"""Debug: Get raw TODO data from Canvas API"""
import sys, os, json, requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def main():
    # Load cookies
    with open(config.COOKIES_FILE, 'r') as f:
        cookies = {c['name']: c['value'] for c in json.load(f)}

    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({'Accept': 'application/json+canvas-string-ids'})

    # Calculate date range (90 days)
    start = datetime.now()
    end = start + timedelta(days=90)

    print(f"=== Fetching TODOs: {start.date()} to {end.date()} ===\n")

    # Method 1: /users/self/todo (default bucket)
    print("--- Method 1: /users/self/todo ---")
    r1 = session.get(f"{config.CANVAS_BASE_URL}/api/v1/users/self/todo")
    todos1 = r1.json()
    print(f"Count: {len(todos1)}")
    print(json.dumps(todos1, indent=2))

    print("\n--- Method 2: /users/self/todo?bucket=upcoming ---")
    r2 = session.get(f"{config.CANVAS_BASE_URL}/api/v1/users/self/todo", params={'bucket': 'upcoming'})
    todos2 = r2.json()
    print(f"Count: {len(todos2)}")
    print(json.dumps(todos2, indent=2))

    print("\n--- Method 3: Planner items (calendar view) ---")
    r3 = session.get(
        f"{config.CANVAS_BASE_URL}/api/v1/planner/items",
        params={
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'per_page': 100
        }
    )
    planner = r3.json()
    print(f"Count: {len(planner)}")
    print(json.dumps(planner, indent=2))

    print("\n--- Method 4: All courses assignments ---")
    # Get all courses
    courses_resp = session.get(f"{config.CANVAS_BASE_URL}/api/v1/courses", params={'enrollment_state': 'active'})
    courses = courses_resp.json()
    print(f"Active courses: {len(courses)}")

    all_assignments = []
    for course in courses:
        cid = course.get('id')
        assignments_resp = session.get(
            f"{config.CANVAS_BASE_URL}/api/v1/courses/{cid}/assignments",
            params={'per_page': 100}
        )
        if assignments_resp.status_code == 200:
            assignments = assignments_resp.json()
            for a in assignments:
                if a.get('due_at'):
                    due = datetime.fromisoformat(a['due_at'].replace('Z', '+00:00'))
                    if start <= due <= end:
                        all_assignments.append({
                            'course': course.get('name'),
                            'name': a.get('name'),
                            'due_at': a.get('due_at'),
                            'points': a.get('points_possible'),
                            'submitted': a.get('has_submitted_submissions')
                        })

    print(f"Total assignments in range: {len(all_assignments)}")
    print(json.dumps(all_assignments, indent=2))

if __name__ == "__main__":
    main()
