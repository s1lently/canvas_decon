"""Historical TODO management - time-ordered insertion"""
import os, json
from datetime import datetime
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

HIS_TODO_FILE = os.path.join(config.ROOT_DIR, 'his_todo.json')

def _parse_due(due):
    """Parse due_date string to datetime"""
    if not due: return None
    try:
        return datetime.fromisoformat(due.replace('Z', '+00:00'))
    except: return None

def load_history():
    """Load historical todos"""
    if not os.path.exists(HIS_TODO_FILE): return []
    with open(HIS_TODO_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_history(todos):
    """Save historical todos"""
    with open(HIS_TODO_FILE, 'w', encoding='utf-8') as f:
        json.dump(todos, f, indent=2, ensure_ascii=False)

def insert_or_update(todo):
    """Insert/update single todo in history (sorted by due_date)

    WARNING: This WILL overwrite existing todo data!
    For batch operations, use batch_insert_or_update() with update_existing=False instead.
    """
    history = load_history()
    url = todo.get('redirect_url', '')

    # Find existing by URL
    for i, t in enumerate(history):
        if t.get('redirect_url') == url:
            history[i] = todo
            save_history(history)
            return

    # Insert new (sorted by due_date)
    due = _parse_due(todo.get('due_date'))
    if not due:
        history.append(todo)
    else:
        inserted = False
        for i, t in enumerate(history):
            t_due = _parse_due(t.get('due_date'))
            if not t_due or due < t_due:
                history.insert(i, todo)
                inserted = True
                break
        if not inserted:
            history.append(todo)
    save_history(history)

def batch_insert_or_update(todos, update_existing=False):
    """Batch insert/update multiple todos (more efficient than calling insert_or_update in a loop)

    Args:
        todos: List of todos to insert/update
        update_existing: If False (default), skip existing todos to preserve user data.
                        If True, update existing todos (use with caution!)
    """
    history = load_history()
    url_map = {t.get('redirect_url'): i for i, t in enumerate(history) if t.get('redirect_url')}

    new_todos = []
    skipped_count = 0

    for todo in todos:
        url = todo.get('redirect_url', '')
        if url in url_map:
            if update_existing:
                # Update existing (dangerous - may overwrite user data!)
                history[url_map[url]] = todo
            else:
                # Skip existing to preserve user modifications
                skipped_count += 1
        else:
            # Collect new todos for batch insertion
            new_todos.append(todo)

    # Batch insert new todos (sorted by due_date)
    for todo in new_todos:
        due = _parse_due(todo.get('due_date'))
        if not due:
            history.append(todo)
        else:
            inserted = False
            for i, t in enumerate(history):
                t_due = _parse_due(t.get('due_date'))
                if not t_due or due < t_due:
                    history.insert(i, todo)
                    inserted = True
                    break
            if not inserted:
                history.append(todo)

    # Save once at the end
    if new_todos:  # Only save if there are changes
        save_history(history)

    return {'new': len(new_todos), 'skipped': skipped_count, 'total': len(todos)}

def archive_past_todos():
    """Move past-due todos from todos.json to his_todo.json (preserves existing history data)"""
    if not os.path.exists(config.COURSE_FILE.replace('course.json', 'todos.json')): return

    todos_file = os.path.join(config.ROOT_DIR, 'todos.json')
    with open(todos_file, 'r', encoding='utf-8') as f:
        todos = json.load(f)

    now = datetime.now(datetime.now().astimezone().tzinfo)
    current, past = [], []

    for t in todos:
        due = _parse_due(t.get('due_date'))
        if due and due < now:
            past.append(t)
        else:
            current.append(t)

    if past:
        # Use batch insert with update_existing=False to preserve user data
        stats = batch_insert_or_update(past, update_existing=False)
        # Update todos.json
        with open(todos_file, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        print(f"[HISTORY] Archived {stats['new']} new past-due todos (skipped {stats['skipped']} already in history)")
