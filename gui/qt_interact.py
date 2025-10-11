"""
UI Interaction Logic for Canvas LMS Automation
Handles button clicks and operations, separated from UI definition
"""
import os
import sys
import json
import threading
import requests

# Add parent directory to path to import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


# ==================== Helper Functions ====================

def _create_console_tab(tab_widget, tab_name):
    """Create a new console tab and return the console output widget"""
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit

    new_tab = QWidget()
    layout = QVBoxLayout()
    console_output = QTextEdit()
    console_output.setReadOnly(True)
    layout.addWidget(console_output)
    new_tab.setLayout(layout)

    index = tab_widget.addTab(new_tab, tab_name)
    tab_widget.setCurrentIndex(index)

    return console_output


def _run_in_thread(func, console_output, task_name, on_success=None):
    """Execute a function in a daemon thread with console output"""
    console_output.append(f"[INFO] {task_name} thread started")

    def wrapper():
        try:
            console_output.append(f"[INFO] Starting {task_name} process...")
            func(console_output)
            console_output.append(f"[SUCCESS] {task_name} completed successfully")
            if on_success:
                on_success()
        except Exception as e:
            import traceback
            console_output.append(f"[ERROR] {task_name} failed: {str(e)}")
            console_output.append(traceback.format_exc())

    threading.Thread(target=wrapper, daemon=True).start()


# ==================== Main Window Handlers ====================

def on_login_clicked(main_window, stacked_widget, login_window):
    """Navigate to login window"""
    stacked_widget.setCurrentWidget(login_window)


def on_get_cookie_clicked(tab_widget, main_window=None):
    """Execute getCookie in a new thread with dedicated tab"""
    console_output = _create_console_tab(tab_widget, "Get Cookie")

    def run_task(console):
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from login.getCookie import main as get_cookie_main
        get_cookie_main()

    def on_success():
        if main_window:
            main_window.update_status()

    _run_in_thread(run_task, console_output, "getCookie", on_success)


def on_get_todo_clicked(tab_widget, main_window=None):
    """Execute getTodos in a new thread with dedicated tab"""
    console_output = _create_console_tab(tab_widget, "Get TODO")

    def run_task(console):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from getTodos import main as get_todos_main
        get_todos_main()

    def on_success():
        if main_window:
            main_window.load_data()
            main_window.on_category_changed(main_window.main_window.categoryList.currentRow())

    _run_in_thread(run_task, console_output, "getTodos", on_success)


def on_get_course_clicked(tab_widget, main_window=None):
    """Execute getCourses in a new thread with dedicated tab"""
    console_output = _create_console_tab(tab_widget, "Get Courses")

    def run_task(console):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from getCourses import main as get_courses_main
        get_courses_main()
        console.append("✓ Courses data saved")

    def on_success():
        if main_window:
            main_window.load_data()
            main_window.update_status()

    _run_in_thread(run_task, console_output, "getCourses", on_success)


def on_clean_clicked(tab_widget):
    """Execute clean.py in a new thread with dedicated tab"""
    console_output = _create_console_tab(tab_widget, "Clean")

    def run_task(console):
        from io import StringIO
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from clean import preview_deletion, clean_directory, build_tree, print_tree

        to_delete = preview_deletion()
        if not to_delete:
            console.append("✓ No files to clean")
            return

        console.append(f"Found {len(to_delete)} files to delete:\n")

        # Capture tree output
        tree_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = tree_output
        print_tree(build_tree(to_delete))
        sys.stdout = old_stdout

        console.append(tree_output.getvalue())
        console.append("\n[INFO] Auto-confirming cleanup (running from GUI)...")
        clean_directory(to_delete)

    _run_in_thread(run_task, console_output, "Clean")


# ==================== Login Window Handlers ====================

def on_back_clicked(stacked_widget, main_window):
    """Navigate back to main window"""
    stacked_widget.setCurrentWidget(main_window)


def on_submit_clicked(account_input, password_input, key_input, stacked_widget, main_window):
    """Save account info to account_info.json and navigate back"""
    try:
        # Collect and validate inputs
        credentials = {
            "account": account_input.text().strip(),
            "password": password_input.text().strip(),
            "otp_key": key_input.text().strip()
        }

        if not all(credentials.values()):
            print("[ERROR] All fields are required")
            return

        # Save to file
        with open(config.ACCOUNT_INFO_FILE, 'w') as f:
            json.dump(credentials, f, indent=2)

        print(f"[SUCCESS] Account info saved to {config.ACCOUNT_INFO_FILE}")

        # Clear and navigate
        for field in (account_input, password_input, key_input):
            field.clear()
        stacked_widget.setCurrentWidget(main_window)

    except Exception as e:
        print(f"[ERROR] Failed to save account info: {str(e)}")


# ==================== Status Update Functions ====================

def update_status_indicators(status_widgets, checkStatus):
    """Update all status indicator colors based on check results"""
    status = checkStatus.get_all_status()

    # Color mapping: 0=red, 1=green, 2=yellow
    colors = {0: '#ef4444', 1: '#22c55e', 2: '#eab308'}

    # Apply styles to all indicators
    for key, widget in status_widgets.items():
        color = colors[status[key]]
        widget.setStyleSheet(f"background-color: {color}; border-radius: 6px;")


# ==================== User Info Functions ====================

def get_user_info():
    """Get user info from account_info.json and Canvas API"""
    user_info = {'email': '--', 'name': '--', 'id': '--'}

    try:
        # Get email from account_info.json
        if os.path.exists(config.ACCOUNT_INFO_FILE):
            with open(config.ACCOUNT_INFO_FILE, 'r') as f:
                user_info['email'] = json.load(f).get('account', '--')

        # Get name and ID from Canvas API
        if os.path.exists(config.COOKIES_FILE):
            with open(config.COOKIES_FILE, 'r') as f:
                cookies = {c['name']: c['value'] for c in json.load(f)}

            resp = requests.get(
                'https://psu.instructure.com/api/v1/users/self',
                cookies=cookies,
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                user_info.update({
                    'name': data.get('name', '--'),
                    'id': str(data.get('id', '--'))
                })

    except Exception as e:
        print(f"[ERROR] Failed to get user info: {e}")

    return user_info


def update_user_info_labels(email_label, name_label, id_label):
    """Update user info labels in the UI"""
    info = get_user_info()
    for label, key in [(email_label, 'email'), (name_label, 'name'), (id_label, 'id')]:
        label.setText(f"{key.capitalize()}: {info[key]}")
