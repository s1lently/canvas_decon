"""Get historical TODOs (graded/completed assignments) - matches getTodos.py format"""
import sys, os, json, requests, re
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def load_cookies():
    if not os.path.exists(config.COOKIES_FILE):
        print(f"Error: {config.COOKIES_FILE} not found. Run main.py first.")
        sys.exit(1)
    with open(config.COOKIES_FILE, 'r') as f:
        return {c['name']: c['value'] for c in json.load(f)}

def extract_course_code(context_name):
    match = re.match(r'^([A-Z\-]+\s+\d+)', context_name)
    return match.group(1) if match else context_name

def get_courses_map(session):
    """Get course_id -> course_name mapping"""
    try:
        r = session.get(f"{config.CANVAS_BASE_URL}/api/v1/courses", params={'per_page': 100})
        courses = r.json()
        return {str(c['id']): c.get('name', 'Unknown') for c in courses}
    except:
        return {}

def get_assignment_details(session, course_id, assignment_id):
    """Fetch assignment details to match getTodos format"""
    try:
        url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments/{assignment_id}"
        r = session.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def convert_submission_to_todo_format(submission, session, courses_map):
    """Convert graded_submission to exact getTodos.py format"""
    # Extract IDs from preview_url
    preview_url = submission.get('preview_url', '')
    # Format: /courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}
    parts = preview_url.split('/')

    try:
        course_idx = parts.index('courses')
        course_id = parts[course_idx + 1]
        assignment_id = str(submission.get('assignment_id', ''))
    except:
        return None

    # Get course name
    course_name = courses_map.get(course_id, 'Unknown Course')
    if course_name != 'Unknown Course':
        course_name = extract_course_code(course_name)

    # Get assignment details (for full metadata)
    assignment = get_assignment_details(session, course_id, assignment_id)

    assignment_name = assignment.get('name', f'Assignment {assignment_id}') if assignment else f'Assignment {assignment_id}'

    # Determine type from submission
    sub_types = []
    sub_type = submission.get('submission_type')
    if sub_type:
        sub_types = [sub_type]

    # Check if it's a quiz
    is_quiz = (sub_type == 'online_quiz')

    # Build redirect_url (relative path)
    if is_quiz and assignment and assignment.get('quiz_id'):
        quiz_id = assignment.get('quiz_id')
        redirect_url = f"/courses/{course_id}/quizzes/{quiz_id}"
    else:
        redirect_url = f"/courses/{course_id}/assignments/{assignment_id}"

    # Build assignment_details matching getTodos format EXACTLY
    assignment_details = {
        'name': None if is_quiz or not assignment else assignment.get('name'),  # null for quizzes like getTodos
        'desc': assignment.get('description', '') if assignment else '',
        'type': sub_types,
        'is_quiz': False,  # Always false to match getTodos.py behavior
        'quiz_id': None,   # Always null to match getTodos.py behavior
        'submitted': True,  # All graded submissions are submitted
        'locked_for_user': False,
        'files': None  # Historical TODOs won't download files
    }

    # Add quiz_metadata if quiz
    if is_quiz and assignment:
        assignment_details['quiz_metadata'] = {
            'locked_for_user': assignment.get('locked_for_user', False),
            'unlock_at': assignment.get('unlock_at'),
            'lock_at': assignment.get('lock_at'),
            'quiz_type': assignment.get('quiz_type'),
            'published': assignment.get('published', False),
            'allowed_attempts': assignment.get('allowed_attempts', 1),
            'time_limit': assignment.get('time_limit'),
            'question_count': assignment.get('question_count', 0),
            'attempt': submission.get('attempt', 0),
            'attempts_left': 0  # Already completed
        }

    return {
        'course_name': course_name,
        'name': assignment_name,
        'due_date': submission.get('cached_due_date'),
        'points_possible': assignment.get('points_possible') if assignment else submission.get('score'),
        'redirect_url': redirect_url,
        'assignment_details': assignment_details
    }

def get_history_todos(session):
    """Get all graded/completed assignments - exact getTodos.py format"""
    print("Fetching graded submissions (historical TODOs)...")

    # Get graded submissions with pagination
    all_graded = []
    page = 1
    per_page = 100

    while True:
        print(f"  Page {page}...", end='', flush=True)
        response = session.get(
            f"{config.CANVAS_BASE_URL}/api/v1/users/self/graded_submissions",
            params={'per_page': per_page}
        )
        response.raise_for_status()
        graded = response.json()

        if not graded:
            print(f" done")
            break

        print(f" {len(graded)} items", flush=True)
        all_graded.extend(graded)

        # Check for next page
        if 'next' not in response.links:
            break

        page += 1
        if page > 50:  # Safety limit
            break

    graded = all_graded
    print(f"Found {len(graded)} graded submissions total")

    # Get courses map
    print("Fetching course names...")
    courses_map = get_courses_map(session)

    # Get current time for filtering
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # Convert each submission
    history_todos = []
    skipped_future = 0
    for i, sub in enumerate(graded, 1):
        if sub.get('graded_at'):  # Only graded items
            print(f"  {i}/{len(graded)}", end='\r')
            todo = convert_submission_to_todo_format(sub, session, courses_map)
            if todo:
                # Filter: only include past-due assignments
                due_date_str = todo.get('due_date')
                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                        if due_date > now:
                            skipped_future += 1
                            continue  # Skip future assignments
                    except:
                        pass  # If date parsing fails, include it anyway

                history_todos.append(todo)

    print(f"\n✓ Converted {len(history_todos)} history TODOs (skipped {skipped_future} future)")
    return history_todos

def save_history_todos(todos):
    """Save to his_todo.json using history_manager (batch insert for efficiency, preserves existing data)"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from mgrHistory import batch_insert_or_update

        # Use batch insert with update_existing=False to preserve user data
        stats = batch_insert_or_update(todos, update_existing=False)

        print(f"\n✓ Saved {stats['new']} new history TODOs (skipped {stats['skipped']} existing)")
    except Exception as e:
        print(f"Error saving: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: save directly (WARNING: overwrites entire file!)
        output_path = os.path.join(config.ROOT_DIR, 'his_todo.json')
        print(f"[WARNING] Using fallback save - existing data will be lost!")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(todos, f, indent=2, ensure_ascii=False)
        print(f"Fallback save to {output_path}")

def main():
    """Fetch and save historical TODOs"""
    cookies = load_cookies()
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({'Accept': 'application/json+canvas-string-ids', 'User-Agent': 'Mozilla/5.0'})

    try:
        history_todos = get_history_todos(session)
        save_history_todos(history_todos)
        print(f"✓ Completed: {len(history_todos)} historical TODOs saved")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
