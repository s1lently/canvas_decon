"""Canvas TODO Fetcher - Retrieves todos, downloads files"""
import sys, os, json, requests, re
from datetime import datetime
from urllib.parse import urlparse, unquote
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
def load_cookies():
    if not os.path.exists(config.COOKIES_FILE): print(f"Error: {config.COOKIES_FILE} not found. Run main.py first."); sys.exit(1)
    with open(config.COOKIES_FILE, 'r') as f: return {c['name']: c['value'] for c in json.load(f)}
def get_todos(session, days=365):
    from datetime import datetime, timedelta; start = datetime.now(); end = start + timedelta(days=days); all_items = []; page = 1
    while True:
        params = {'start_date': start.date().isoformat(), 'end_date': end.date().isoformat(), 'per_page': 100}; response = session.get(f"{config.CANVAS_BASE_URL}/api/v1/planner/items", params=params); response.raise_for_status(); items = response.json()
        if not items: break
        for item in items:
            if item.get('plannable_type') in ['assignment', 'quiz', 'discussion_topic']:
                plannable = item.get('plannable', {}); all_items.append({'context_type': 'Course', 'course_id': str(item.get('course_id', '')), 'context_name': item.get('context_name', ''), 'type': 'submitting', 'html_url': item.get('html_url', ''), 'assignment': {'id': str(plannable.get('id', '')), 'name': plannable.get('title', ''), 'due_at': item.get('plannable_date'), 'points_possible': plannable.get('points_possible'), 'has_submitted_submissions': item.get('submissions', {}).get('submitted', False) if item.get('submissions') else False, 'is_quiz_assignment': item.get('plannable_type') == 'quiz', 'quiz_id': plannable.get('id') if item.get('plannable_type') == 'quiz' else None, 'assignment_id': plannable.get('assignment_id') if item.get('plannable_type') == 'quiz' else plannable.get('id'), 'description': plannable.get('description', ''), 'submission_types': ['online_quiz'] if item.get('plannable_type') == 'quiz' else ['online_upload']}})
        if 'next' not in response.links: break
        page += 1
    print(f"Found {len(all_items)} upcoming items (next {days} days, {page} pages)"); return all_items
def extract_course_code(context_name): match = re.match(r'^([A-Z\-]+\s+\d+)', context_name); return match.group(1) if match else context_name
def format_datetime(date_str):
    if not date_str: return "No due date"
    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00')); return dt.strftime("%Y-%m-%d %H:%M")
def extract_file_ids(description):
    if not description: return []
    matches = re.findall(r'/courses/(\d+)/files/(\d+)', description); seen, result = set(), []
    for course_id, file_id in matches:
        if file_id not in seen: seen.add(file_id); result.append({'course_id': course_id, 'file_id': file_id})
    return result
def get_unique_filename(directory, filename):
    if not os.path.exists(os.path.join(directory, filename)): return filename
    name, ext = os.path.splitext(filename); match = re.match(r'^(.+?)_r(\d+)$', name); base_name, counter = (match.group(1), int(match.group(2))) if match else (name, 0)
    while True:
        counter += 1
        new_filename = f"{base_name}_r{counter}{ext}"
        if not os.path.exists(os.path.join(directory, new_filename)):
            return new_filename
def sanitize_folder_name(name):
    invalid_chars = r'<>:"/\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    name = name.strip('. ')
    return name
def create_assignment_folder(base_dir, assignment_name, due_date):
    if due_date:
        try: dt = datetime.fromisoformat(due_date.replace('Z', '+00:00')); date_suffix = dt.strftime("%Y%m%d_%H%M%S")
        except: date_suffix = "no_date"
    else: date_suffix = "no_date"
    safe_name = sanitize_folder_name(assignment_name); folder_name = f"{safe_name}_{date_suffix}"; folder_path = os.path.join(base_dir, folder_name); files_path = os.path.join(folder_path, 'files')
    os.makedirs(files_path, exist_ok=True); os.makedirs(os.path.join(folder_path, 'auto', 'input'), exist_ok=True); os.makedirs(os.path.join(folder_path, 'auto', 'output'), exist_ok=True); return folder_path
def download_file(session, url, save_dir):
    try:
        response = session.get(url, stream=True); response.raise_for_status(); filename = None
        if 'Content-Disposition' in response.headers: match = re.search(r'filename="?([^"]+)"?', response.headers['Content-Disposition']); filename = unquote(match.group(1)) if match else filename
        if not filename: parsed = urlparse(url); filename = unquote(parsed.path.split('/')[-1]) if parsed.path else f"file_{parsed.path.split('/')[-2]}"
        files_dir = os.path.join(save_dir, 'files'); os.makedirs(files_dir, exist_ok=True); file_path = os.path.join(files_dir, filename)
        with open(file_path, 'wb') as f: [f.write(chunk) for chunk in response.iter_content(chunk_size=8192)]
        return {'success': True, 'filename': filename, 'path': file_path, 'size': os.path.getsize(file_path)}
    except Exception as e: return {'success': False, 'error': str(e)}
def fetch_assignment_details(session, assignment_url, assignment_name, due_date, base_todo_dir):
    try:
        clean_url = assignment_url.split('#')[0]; parts = clean_url.split('/'); course_id = parts[parts.index('courses') + 1]
        if 'quizzes' in parts: quiz_id = parts[parts.index('quizzes') + 1]; api_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/quizzes/{quiz_id}"
        elif 'discussion_topics' in parts: topic_id = parts[parts.index('discussion_topics') + 1]; api_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/discussion_topics/{topic_id}"
        elif 'assignments' in parts: assignment_id = parts[parts.index('assignments') + 1]; api_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments/{assignment_id}"
        else: return {'error': f'Unknown URL format: {assignment_url}'}
        response = session.get(api_url); response.raise_for_status(); assignment_data = response.json(); description = assignment_data.get('description', ''); file_infos = extract_file_ids(description); downloaded_files = []; folder_name = None; assignment_folder = None
        if file_infos:
            assignment_folder = create_assignment_folder(base_todo_dir, assignment_name, due_date); folder_name = os.path.basename(assignment_folder)
            for file_info in file_infos:
                download_url = f"{config.CANVAS_BASE_URL}/courses/{file_info['course_id']}/files/{file_info['file_id']}/download?download_frd=1"; result = download_file(session, download_url, assignment_folder)
                if result['success']: downloaded_files.append({'file_id': file_info['file_id'], 'download_url': download_url, 'filename': result['filename'], 'local_path': result['path']})
                else: downloaded_files.append({'file_id': file_info['file_id'], 'download_url': download_url, 'error': result['error']})
        else: assignment_folder = create_assignment_folder(base_todo_dir, assignment_name, due_date)
        result = {'name': assignment_data.get('name'), 'desc': description, 'type': assignment_data.get('submission_types', []), 'is_quiz': assignment_data.get('is_quiz_assignment', False), 'quiz_id': assignment_data.get('quiz_id'), 'submitted': assignment_data.get('has_submitted_submissions', False), 'locked_for_user': assignment_data.get('locked_for_user', False), 'files': downloaded_files if downloaded_files else None, 'assignment_folder': assignment_folder}
        if 'quizzes' in parts:
            quiz_metadata = {'locked_for_user': assignment_data.get('locked_for_user', False), 'unlock_at': assignment_data.get('unlock_at'), 'lock_at': assignment_data.get('lock_at'), 'quiz_type': assignment_data.get('quiz_type'), 'published': assignment_data.get('published', False), 'allowed_attempts': assignment_data.get('allowed_attempts', 1), 'time_limit': assignment_data.get('time_limit'), 'question_count': assignment_data.get('question_count', 0)}
            try:
                submissions_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions"; sub_response = session.get(submissions_url)
                if sub_response.status_code == 200: submissions = sub_response.json(); user_submissions = submissions['quiz_submissions'] if submissions and 'quiz_submissions' in submissions else []; latest_sub = user_submissions[0] if user_submissions else None; quiz_metadata['attempt'] = latest_sub.get('attempt', 0) if latest_sub else 0; quiz_metadata['attempts_left'] = quiz_metadata['allowed_attempts'] - quiz_metadata['attempt'] if quiz_metadata['allowed_attempts'] != -1 else 999
            except: quiz_metadata['attempt'] = 0; quiz_metadata['attempts_left'] = quiz_metadata['allowed_attempts'] if quiz_metadata['allowed_attempts'] != -1 else 999
            result['quiz_metadata'] = quiz_metadata
            if assignment_data.get('quiz_type') == 'assignment' and assignment_data.get('published'):
                if 'online_quiz' not in result['type']: result['type'].append('online_quiz')
        if 'discussion_topics' in parts:
            is_locked = assignment_data.get('locked', False); discussion_type = assignment_data.get('discussion_type', 'threaded')
            if not is_locked:
                if 'discussion_topic' not in result['type']: result['type'].append('discussion_topic')
        if folder_name: result['folder'] = folder_name
        return result
    except Exception as e: return {'error': str(e)}
def process_and_save_todos(todos, session):
    output_path = config.TODOS_FILE; existing = {}
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f: [existing.update({t.get('redirect_url'): t}) for t in json.load(f) if t.get('redirect_url')]
    todo_dir = config.TODO_DIR; os.makedirs(todo_dir, exist_ok=True)
    for item in todos:
        assignment = item.get('assignment', {}); context_name = item.get('context_name', 'Unknown Course'); course_code = extract_course_code(context_name); redirect_url = item.get('html_url', ''); assignment_name = assignment.get('name', 'Unknown Assignment'); due_date = assignment.get('due_at')
        todo_data = {'course_name': course_code, 'name': assignment_name, 'due_date': due_date, 'points_possible': assignment.get('points_possible'), 'redirect_url': redirect_url}
        idx = todos.index(item) + 1
        print(f"  {idx}/{len(todos)}: {todo_data['name'][:40]}")
        assignment_details = fetch_assignment_details(session, redirect_url, assignment_name, due_date, todo_dir); todo_data['assignment_details'] = assignment_details
        if 'error' in assignment_details: print(f"    ✗ Error: {assignment_details['error']}")
        existing[redirect_url] = todo_data
    from datetime import datetime
    def parse_due(t):
        d = t.get('due_date')
        try:
            return datetime.fromisoformat(d.replace('Z', '+00:00')) if d else datetime.max
        except:
            return datetime.max
    result = sorted(existing.values(), key=parse_due)
    with open(output_path, 'w', encoding='utf-8') as f: json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n{'='*80}\nSaved to: {output_path}"); return result
def display_todos(todos):
    if not todos: print("No todos found."); return
    print(f"\n{'='*80}\n✓ Saved {len(todos)} TODOs to todos.json\n{'='*80}")
def main(days=365):
    print(f"Fetching Canvas TODO items (next {days} days)..."); cookies = load_cookies(); session = requests.Session(); session.cookies.update(cookies); session.headers.update({'Accept': 'application/json+canvas-string-ids', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    try: raw_todos = get_todos(session, days=days); simplified_todos = process_and_save_todos(raw_todos, session); display_todos(simplified_todos)
    except requests.exceptions.RequestException as e: print(f"Error: {e}"); sys.exit(1)
if __name__ == "__main__": main()
