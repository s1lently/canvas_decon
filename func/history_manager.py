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
    """Insert/update single todo in history (sorted by due_date)"""
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

def archive_past_todos():
    """Move past-due todos from todos.json to his_todo.json"""
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
            insert_or_update(t)
        else:
            current.append(t)

    if past:
        with open(todos_file, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        print(f"[HISTORY] Archived {len(past)} past-due todos")
