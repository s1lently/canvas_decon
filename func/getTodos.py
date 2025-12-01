"""Canvas TODO Fetcher - Retrieves todos, downloads files (Concurrent Version)"""
import sys, os, json, requests, re, time
import concurrent.futures
from datetime import datetime, timedelta
from urllib.parse import urlparse, unquote

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

def extract_file_ids(description):
    if not description: return []
    matches = re.findall(r'/courses/(\d+)/files/(\d+)', description)
    seen, result = set(), []
    for course_id, file_id in matches:
        if file_id not in seen:
            seen.add(file_id)
            result.append({'course_id': course_id, 'file_id': file_id})
    return result

def sanitize_folder_name(name):
    """Sanitize folder name - delegates to core.security for safety"""
    try:
        from core.security import sanitize_path
        return sanitize_path(name)
    except ImportError:
        # Fallback if core not available (backward compat)
        import re
        if not name:
            return "unnamed"
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
        while '..' in name:
            name = name.replace('..', '_')
        name = name.strip('. /\\')
        return name or "unnamed"

def create_assignment_folder(base_dir, assignment_name, due_date):
    if due_date:
        try:
            dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            date_suffix = dt.strftime("%Y%m%d_%H%M%S")
        except (ValueError, AttributeError):
            date_suffix = "no_date"
    else:
        date_suffix = "no_date"
    
    safe_name = sanitize_folder_name(assignment_name)
    folder_name = f"{safe_name}_{date_suffix}"
    folder_path = os.path.join(base_dir, folder_name)
    
    os.makedirs(os.path.join(folder_path, 'files'), exist_ok=True)
    os.makedirs(os.path.join(folder_path, 'auto', 'input'), exist_ok=True)
    os.makedirs(os.path.join(folder_path, 'auto', 'output'), exist_ok=True)
    
    return folder_path

def download_file(session, url, save_dir):
    try:
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        filename = None
        if 'Content-Disposition' in response.headers:
            match = re.search(r'filename="?([^"]+)"?', response.headers['Content-Disposition'])
            filename = unquote(match.group(1)) if match else None
            
        if not filename:
            parsed = urlparse(url)
            filename = unquote(parsed.path.split('/')[-1]) if parsed.path else f"file_unknown"
            
        file_path = os.path.join(save_dir, 'files', filename)
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return {'success': True, 'filename': filename, 'path': file_path, 'size': os.path.getsize(file_path)}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def fetch_assignment_details(session, assignment_url, assignment_name, due_date, base_todo_dir):
    try:
        clean_url = assignment_url.split('#')[0]
        parts = clean_url.split('/')
        
        try:
            course_id = parts[parts.index('courses') + 1]
        except ValueError:
            return {'error': f'Invalid URL: {assignment_url}'}
            
        if 'quizzes' in parts:
            quiz_id = parts[parts.index('quizzes') + 1]
            api_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/quizzes/{quiz_id}"
        elif 'discussion_topics' in parts:
            topic_id = parts[parts.index('discussion_topics') + 1]
            api_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/discussion_topics/{topic_id}"
        elif 'assignments' in parts:
            assignment_id = parts[parts.index('assignments') + 1]
            api_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments/{assignment_id}"
        else:
            return {'error': f'Unknown URL type: {assignment_url}'}
            
        response = session.get(api_url, timeout=10)
        response.raise_for_status()
        assignment_data = response.json()
        
        description = assignment_data.get('description', '')
        file_infos = extract_file_ids(description)
        downloaded_files = []
        folder_name = None
        assignment_folder = None
        
        # Download files if present
        if file_infos:
            assignment_folder = create_assignment_folder(base_todo_dir, assignment_name, due_date)
            folder_name = os.path.basename(assignment_folder)
            
            for file_info in file_infos:
                download_url = f"{config.CANVAS_BASE_URL}/courses/{file_info['course_id']}/files/{file_info['file_id']}/download?download_frd=1"
                result = download_file(session, download_url, assignment_folder)
                
                if result['success']:
                    downloaded_files.append({
                        'file_id': file_info['file_id'], 
                        'download_url': download_url, 
                        'filename': result['filename'], 
                        'local_path': result['path']
                    })
                else:
                    downloaded_files.append({
                        'file_id': file_info['file_id'], 
                        'download_url': download_url, 
                        'error': result['error']
                    })
        else:
            # Create folder anyway for consistency (or skip? original code created it)
            assignment_folder = create_assignment_folder(base_todo_dir, assignment_name, due_date)
            folder_name = os.path.basename(assignment_folder)
            
        result = {
            'name': assignment_data.get('name'),
            'desc': description,
            'type': assignment_data.get('submission_types', []),
            'is_quiz': assignment_data.get('is_quiz_assignment', False),
            'quiz_id': assignment_data.get('quiz_id'),
            'submitted': assignment_data.get('has_submitted_submissions', False),
            'locked_for_user': assignment_data.get('locked_for_user', False),
            'files': downloaded_files if downloaded_files else None,
            'assignment_folder': assignment_folder,
            'folder': folder_name
        }
        
        # Additional Quiz Metadata
        if 'quizzes' in parts:
            quiz_metadata = {
                'locked_for_user': assignment_data.get('locked_for_user', False),
                'unlock_at': assignment_data.get('unlock_at'),
                'lock_at': assignment_data.get('lock_at'),
                'quiz_type': assignment_data.get('quiz_type'),
                'published': assignment_data.get('published', False),
                'allowed_attempts': assignment_data.get('allowed_attempts', 1),
                'time_limit': assignment_data.get('time_limit'),
                'question_count': assignment_data.get('question_count', 0)
            }
            try:
                submissions_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions"
                sub_response = session.get(submissions_url, timeout=5)
                if sub_response.status_code == 200:
                    submissions = sub_response.json()
                    user_submissions = submissions.get('quiz_submissions', [])
                    latest_sub = user_submissions[0] if user_submissions else None
                    quiz_metadata['attempt'] = latest_sub.get('attempt', 0) if latest_sub else 0
                    
                    if quiz_metadata['allowed_attempts'] != -1:
                        quiz_metadata['attempts_left'] = quiz_metadata['allowed_attempts'] - quiz_metadata['attempt']
                    else:
                        quiz_metadata['attempts_left'] = 999
            except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError):
                quiz_metadata['attempt'] = 0
                quiz_metadata['attempts_left'] = 999

            result['quiz_metadata'] = quiz_metadata
            
            if assignment_data.get('quiz_type') == 'assignment' and assignment_data.get('published'):
                if 'online_quiz' not in result['type']:
                    result['type'].append('online_quiz')
                    
        # Discussion handling
        if 'discussion_topics' in parts:
            is_locked = assignment_data.get('locked', False)
            if not is_locked and 'discussion_topic' not in result['type']:
                result['type'].append('discussion_topic')
                
        return result
    except Exception as e:
        return {'error': str(e)}

def fetch_planner_items_page(session, page, start_date, end_date):
    """Fetch single page of planner items"""
    params = {
        'start_date': start_date,
        'end_date': end_date,
        'per_page': 100,
        'page': page
    }
    try:
        r = session.get(f"{config.CANVAS_BASE_URL}/api/v1/planner/items", params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except (requests.RequestException, json.JSONDecodeError):
        pass
    return []

def get_todos_concurrent(session, days=365, progress=None):
    """Fetch planner items concurrently

    Args:
        session: requests.Session
        days: Days to look ahead
        progress: TaskProgress instance (optional)
    """
    start = datetime.now()
    end = start + timedelta(days=days)
    start_date = start.date().isoformat()
    end_date = end.date().isoformat()

    if progress:
        progress.update(progress=0, status=f"Fetching Planner ({days} days)...")
    print(f"Fetching Planner items ({days} days)...")
    
    # First request to get total pages (if possible) or just page 1
    # Planner API doesn't always give total pages in Link header reliably for all LMS
    # But we can try probing pages 1-5 concurrently first? 
    # Let's just do a sequential probe of page 1 to check links, then burst.
    
    total_pages = 1
    try:
        r = session.head(
            f"{config.CANVAS_BASE_URL}/api/v1/planner/items",
            params={'start_date': start_date, 'end_date': end_date, 'per_page': 100}
        )
        if 'last' in r.links:
            match = re.search(r'[?&]page=(\d+)', r.links['last']['url'])
            if match:
                total_pages = int(match.group(1))
    except (requests.RequestException, KeyError, AttributeError):
        pass
    
    print(f"  Detected {total_pages} pages of items")
    
    all_items = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_planner_items_page, session, p, start_date, end_date): p for p in range(1, total_pages + 1)}
        
        for future in concurrent.futures.as_completed(futures):
            items = future.result()
            if items:
                all_items.extend(items)
                
    # Filter for assignments/quizzes/discussions
    filtered_items = []
    for item in all_items:
        if item.get('plannable_type') in ['assignment', 'quiz', 'discussion_topic']:
            plannable = item.get('plannable', {})
            filtered_items.append({
                'context_type': 'Course',
                'course_id': str(item.get('course_id', '')),
                'context_name': item.get('context_name', ''),
                'type': 'submitting',
                'html_url': item.get('html_url', ''),
                'assignment': {
                    'id': str(plannable.get('id', '')),
                    'name': plannable.get('title', ''),
                    'due_at': item.get('plannable_date'),
                    'points_possible': plannable.get('points_possible'),
                    'has_submitted_submissions': item.get('submissions', {}).get('submitted', False) if item.get('submissions') else False,
                    'is_quiz_assignment': item.get('plannable_type') == 'quiz',
                    'quiz_id': plannable.get('id') if item.get('plannable_type') == 'quiz' else None,
                    'assignment_id': plannable.get('assignment_id') if item.get('plannable_type') == 'quiz' else plannable.get('id'),
                    'description': plannable.get('description', ''),
                    'submission_types': ['online_quiz'] if item.get('plannable_type') == 'quiz' else ['online_upload']
                }
            })
            
    if progress:
        progress.update(progress=10, status=f"Found {len(filtered_items)} TODOs")
    print(f"  Found {len(filtered_items)} upcoming TODOs")
    return filtered_items

def process_and_save_todos_concurrent(todos, session, progress=None):
    """Process todos details concurrently"""
    output_path = config.TODOS_FILE
    existing = {}
    
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing = {t.get('redirect_url'): t for t in json.load(f) if t.get('redirect_url')}
        except (json.JSONDecodeError, IOError, TypeError):
            pass

    todo_dir = config.TODO_DIR
    os.makedirs(todo_dir, exist_ok=True)

    if progress:
        progress.update(progress=15, status="Processing details...")
    print("Processing details & downloading files (Concurrent)...")

    processed_todos = []
    start_time = time.time()
    total_items = len(todos)
    processed_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_map = {}
        
        for item in todos:
            assignment = item.get('assignment', {})
            context_name = item.get('context_name', 'Unknown Course')
            course_code = extract_course_code(context_name)
            redirect_url = item.get('html_url', '')
            assignment_name = assignment.get('name', 'Unknown Assignment')
            due_date = assignment.get('due_at')
            
            todo_data = {
                'course_name': course_code,
                'name': assignment_name,
                'due_date': due_date,
                'points_possible': assignment.get('points_possible'),
                'redirect_url': redirect_url
            }
            
            # Submit task to fetch details
            future = executor.submit(fetch_assignment_details, session, redirect_url, assignment_name, due_date, todo_dir)
            future_map[future] = (todo_data, redirect_url)

        # Collect results
        for future in concurrent.futures.as_completed(future_map):
            todo_data, redirect_url = future_map[future]
            processed_count += 1
            
            try:
                details = future.result()
                todo_data['assignment_details'] = details
                if 'error' in details:
                    # Log error but don't stop
                    pass 
                
                # Update existing map (merge with old data if needed, but here we usually overwrite)
                existing[redirect_url] = todo_data
                
            except Exception as e:
                print(f"\nError processing {todo_data['name']}: {e}")
                
            # Progress bar
            elapsed = time.time() - start_time
            speed = processed_count / elapsed if elapsed > 0 else 0
            pct = 15 + int((processed_count / total_items) * 80)  # 15-95%
            if progress:
                progress.update(progress=pct, status=f"Processing {processed_count}/{total_items}", speed=f"{speed:.1f}/s")
            print(f"\r  Processing: {processed_count}/{total_items} | Speed: {speed:.1f} items/s", end='', flush=True)

    elapsed_total = time.time() - start_time
    if progress:
        progress.update(progress=95, status=f"Processed {total_items} in {elapsed_total:.1f}s")
    print(f"\n✓ Processed {total_items} items in {elapsed_total:.2f}s")
    
    # Sort by due date
    def parse_due(t):
        d = t.get('due_date')
        try:
            return datetime.fromisoformat(d.replace('Z', '+00:00')) if d else datetime.max
        except (ValueError, AttributeError):
            return datetime.max
            
    result = sorted(existing.values(), key=parse_due)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    if progress:
        progress.finish(f"Saved {len(result)} TODOs")
    print(f"✓ Saved {len(result)} TODOs to todos.json")
    return result


def main(days=365, progress=None):
    """Main entry point

    Args:
        days: Days to look ahead
        progress: TaskProgress instance (optional, for GUI mode)
    """
    if progress:
        progress.update(progress=0, status="Starting...")
    print(f"Fetching Canvas TODO items (next {days} days)...")

    cookies = load_cookies()
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({
        'Accept': 'application/json+canvas-string-ids',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        raw_todos = get_todos_concurrent(session, days=days, progress=progress)
        process_and_save_todos_concurrent(raw_todos, session, progress=progress)
    except Exception as e:
        if progress:
            progress.fail(str(e))
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
