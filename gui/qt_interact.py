"""UI Interaction Logic for Canvas LMS Automation"""
import os, sys, json, threading, requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def _create_console_tab(tw, name):
    """Create console tab"""
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
    tab, layout, console = QWidget(), QVBoxLayout(), QTextEdit()
    console.setReadOnly(True)
    layout.addWidget(console)
    tab.setLayout(layout)
    tw.setCurrentIndex(tw.addTab(tab, name))
    return console

def _run_in_thread(func, console, name, on_success=None):
    """Execute in daemon thread"""
    console.append(f"[INFO] {name} started")
    def wrapper():
        try:
            console.append(f"[INFO] Starting {name}...")
            func(console)
            console.append(f"[SUCCESS] {name} completed")
            if on_success: on_success()
        except Exception as e:
            import traceback
            console.append(f"[ERROR] {name} failed: {e}")
            console.append(traceback.format_exc())
    threading.Thread(target=wrapper, daemon=True).start()

def on_login_clicked(main_window, stacked_widget, login_window, app_instance=None):
    stacked_widget.setCurrentWidget(login_window)
    # Reload API settings when opening settings window
    if app_instance and hasattr(app_instance, '_load_api_settings'):
        app_instance._load_api_settings()


def on_get_cookie_clicked(tw, mw=None):
    """Execute getCookie"""
    def run(c):
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from login.getCookie import main as get_cookie_main
        get_cookie_main()
    _run_in_thread(run, _create_console_tab(tw, "Get Cookie"), "getCookie", lambda: mw.update_status() if mw else None)

def on_get_todo_clicked(tw, mw=None):
    """Execute getTodos"""
    def run(c):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from getTodos import main
        main()
    def success():
        if mw: mw.load_data(); mw.on_category_changed(mw.main_window.categoryList.currentRow())
    _run_in_thread(run, _create_console_tab(tw, "Get TODO"), "getTodos", success)

def on_get_course_clicked(tw, mw=None):
    """Execute getCourses"""
    def run(c):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from getCourses import main
        main()
        c.append("✓ Courses saved")
    def success():
        if mw: mw.load_data(); mw.update_status()
    _run_in_thread(run, _create_console_tab(tw, "Get Courses"), "getCourses", success)


def on_gsyll_all_clicked(tw):
    """Execute getSyll.py for all courses"""
    def run(c):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from getSyll import run_extraction_for_course, logger
        import json

        # Read courses
        with open(config.COURSE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            courses = data.get('courses', data) if isinstance(data, dict) else data

        c.append(f"[INFO] Found {len(courses)} courses to process")

        # Run extraction for each course
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = [r for r in executor.map(run_extraction_for_course, courses) if r[0]]

        c.append("\n--- Syllabus Extraction Summary ---")
        found_count = sum(1 for _, s in results if s)
        for name, successes in sorted(results):
            status = f"[SUCCESS] {name}: Found via {', '.join(sorted(set(successes)))}" if successes else f"[ FAIL  ] {name}: No syllabus found."
            c.append(status)
        c.append(f"\nSummary: Found syllabus for {found_count} out of {len(results)} courses.")
    _run_in_thread(run, _create_console_tab(tw, "Get Syllabus All"), "gSyllAll")

def on_clean_clicked(tw):
    """Execute clean.py"""
    def run(c):
        from io import StringIO
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from clean import preview_deletion, clean_directory, build_tree, print_tree
        td = preview_deletion()
        if not td: return c.append("✓ No files to clean")
        c.append(f"Found {len(td)} files:\n")
        to = StringIO()
        old = sys.stdout
        sys.stdout = to
        print_tree(build_tree(td))
        sys.stdout = old
        c.append(to.getvalue())
        c.append("\n[INFO] Auto-confirming cleanup...")
        clean_directory(td)
    _run_in_thread(run, _create_console_tab(tw, "Clean"), "Clean")

def on_back_clicked(sw, mw):
    sw.setCurrentWidget(mw)

def on_submit_clicked(ai, pi, ki, sw, mw):
    """Save account info - only update account/password/otp_key fields"""
    try:
        account = ai.text().strip()
        password = pi.text().strip()
        otp_key = ki.text().strip()

        if not all([account, password, otp_key]):
            return print("[ERROR] All fields required")

        # Load existing config to preserve other fields
        config_data = {}
        if os.path.exists(config.ACCOUNT_CONFIG_FILE):
            with open(config.ACCOUNT_CONFIG_FILE) as f:
                config_data = json.load(f)

        # Update only the three login fields
        config_data['account'] = account
        config_data['password'] = password
        config_data['otp_key'] = otp_key

        # Save back
        with open(config.ACCOUNT_CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)

        print(f"[SUCCESS] Login credentials saved to {config.ACCOUNT_CONFIG_FILE}")
        for f in (ai, pi, ki): f.clear()
        sw.setCurrentWidget(mw)
    except Exception as e:
        print(f"[ERROR] Save failed: {e}")


def update_status_indicators(sw, cs):
    """Update status indicators"""
    st = cs.get_all_status()
    colors = {0: '#ef4444', 1: '#22c55e', 2: '#eab308'}
    for k, w in sw.items(): w.setStyleSheet(f"background-color: {colors[st[k]]}; border-radius: 6px;")

def get_user_info():
    """Get user info"""
    ui = {'email': '--', 'name': '--', 'id': '--'}
    try:
        if os.path.exists(config.ACCOUNT_INFO_FILE):
            ui['email'] = json.load(open(config.ACCOUNT_INFO_FILE)).get('account', '--')
        if os.path.exists(config.COOKIES_FILE):
            cookies = {c['name']: c['value'] for c in json.load(open(config.COOKIES_FILE))}
            r = requests.get('https://psu.instructure.com/api/v1/users/self', cookies=cookies, timeout=5)
            if r.status_code == 200:
                d = r.json()
                ui.update({'name': d.get('name', '--'), 'id': str(d.get('id', '--'))})
    except Exception as e:
        print(f"[ERROR] Get user info failed: {e}")
    return ui

def update_user_info_labels(el, nl, il):
    """Update user info labels"""
    info = get_user_info()
    for lbl, key in [(el, 'email'), (nl, 'name'), (il, 'id')]:
        lbl.setText(f"{key.capitalize()}: {info[key]}")
