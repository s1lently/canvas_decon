"""UI Interaction Logic for Canvas LMS Automation"""
import os, sys, json, threading, requests
from PyQt6.QtCore import Qt
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


def on_login_clicked(main_window, stacked_widget, login_window, app_instance=None):
    stacked_widget.setCurrentWidget(login_window)
    # Reload API settings when opening settings window
    if app_instance and hasattr(app_instance, '_load_api_settings'):
        app_instance._load_api_settings()


def on_get_cookie_clicked(tw, mw=None):
    """Execute getCookie via Mission Control"""
    if not mw or not hasattr(mw, 'mission_control'):
        print("[ERROR] Mission Control not available")
        return

    def run(progress):
        from func.logCookie import main
        main(progress=progress)

    def on_success():
        if mw:
            mw.update_status()
            mw.show_toast("Cookie Updated!", 'success')

    mw.mission_control.start_task("Getting Cookie", run, on_success=on_success)

def on_get_todo_clicked(tw, mw=None):
    """Execute getTodos and getHistoryTodos via Mission Control"""
    if not mw or not hasattr(mw, 'mission_control'):
        print("[ERROR] Mission Control not available")
        return

    mc = mw.mission_control

    # Task 1: Fetch TODOs
    def run_todos(progress):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'func'))
        from getTodos import main
        main(progress=progress)

    def on_todos_success():
        if mw:
            mw.main_handler.load_data()
            mw.main_handler.on_category_changed(mw.main_window.categoryList.currentRow())
            mw.show_toast("TODOs Updated!", 'success')

    # Task 2: Fetch History
    def run_history(progress):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'func'))
        from getHistoryTodos import main
        main(progress=progress)

    def on_history_success():
        if mw:
            mw.show_toast("History Updated!", 'success')

    # Start both tasks in parallel
    mc.start_task("Fetching TODOs", run_todos, on_success=on_todos_success)
    mc.start_task("Fetching History", run_history, on_success=on_history_success)

def on_get_course_clicked(tw, mw=None):
    """Execute getCourses via Mission Control"""
    if not mw or not hasattr(mw, 'mission_control'):
        print("[ERROR] Mission Control not available")
        return

    def run(progress):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'func'))
        from getCourses import main
        main(progress=progress)

    def on_success():
        if mw:
            mw.main_handler.load_data()
            mw.update_status()
            mw.show_toast("Courses Updated!", 'success')

    mw.mission_control.start_task("Fetching Courses", run, on_success=on_success)


def on_gsyll_all_clicked(tw, mw=None):
    """Execute getSyll.py for all courses via Mission Control"""
    if not mw or not hasattr(mw, 'mission_control'):
        print("[ERROR] Mission Control not available")
        return

    def run(progress):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'func'))
        from getSyll import run_extraction_for_course
        import json

        progress.update(progress=0, status="Reading courses...")
        with open(config.COURSE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            courses = data.get('courses', data) if isinstance(data, dict) else data

        total = len(courses)
        progress.update(progress=10, status=f"Processing {total} courses...")
        print(f"Found {total} courses to process")

        # Run extraction for each course
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(run_extraction_for_course, c): c for c in courses}
            completed = 0
            for future in as_completed(futures):
                r = future.result()
                if r[0]:
                    results.append(r)
                completed += 1
                pct = 10 + int(completed / total * 85)
                progress.update(progress=pct, status=f"Processed {completed}/{total}")

        found_count = sum(1 for _, s in results if s)
        progress.finish(f"Found {found_count}/{len(results)} syllabi")
        print(f"Summary: Found syllabus for {found_count} out of {len(results)} courses.")

    def on_success():
        if mw:
            mw.show_toast("Syllabus Updated!", 'success')

    mw.mission_control.start_task("Get All Syllabi", run, on_success=on_success)

def on_clean_clicked(tw, mw=None):
    """Execute clean.py via Mission Control"""
    if not mw or not hasattr(mw, 'mission_control'):
        print("[ERROR] Mission Control not available")
        return

    def run(progress):
        from func.clean import preview_deletion, clean_directory

        progress.update(progress=10, status="Scanning files...")
        td = preview_deletion()
        if not td:
            progress.finish("No files to clean")
            print("✓ No files to clean")
            return

        progress.update(progress=30, status=f"Found {len(td)} files")
        print(f"Found {len(td)} files to clean")

        progress.update(progress=50, status="Cleaning...")
        clean_directory(td)
        progress.finish(f"Cleaned {len(td)} files")
        print(f"✓ Cleaned {len(td)} files")

    def on_success():
        if mw:
            mw.show_toast("Clean Complete!", 'success')

    mw.mission_control.start_task("Cleaning Files", run, on_success=on_success)

def on_back_clicked(sw, mw):
    sw.setCurrentWidget(mw)

def on_submit_clicked(ai, pi, ki, sw, mw, manual_mode_toggle=None):
    """Save account info - allows partial updates (any field can be updated independently)

    Args:
        manual_mode_toggle: IOSToggle for manual 2FA mode (optional)
    """
    try:
        account = ai.text().strip()
        password = pi.text().strip()
        otp_key = ki.text().strip()

        # Check manual mode
        manual_mode = manual_mode_toggle.isChecked() if manual_mode_toggle else False

        # Check if at least one field is provided
        if not account and not password and not otp_key and not manual_mode:
            return print("[ERROR] At least one field must be provided")

        # Load existing config to preserve other fields
        config_data = {}
        if os.path.exists(config.ACCOUNT_CONFIG_FILE):
            with open(config.ACCOUNT_CONFIG_FILE) as f:
                config_data = json.load(f)

        # Update fields (only if provided)
        updated_fields = []

        if account:
            config_data['account'] = account
            updated_fields.append('account')

        if password:
            config_data['password'] = password
            updated_fields.append('password')

        if otp_key:
            config_data['otp_key'] = otp_key
            updated_fields.append('otp_key')
        elif manual_mode:
            # Manual mode enabled without TOTP key
            config_data['otp_key'] = "loginself"
            updated_fields.append('otp_key (manual mode)')
            print("[INFO] Manual 2FA mode enabled - you'll complete 2FA manually")

        # Save back
        with open(config.ACCOUNT_CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)

        print(f"[SUCCESS] Updated: {', '.join(updated_fields)}")

        # Clear only the fields that were filled
        if account: ai.clear()
        if password: pi.clear()
        if otp_key: ki.clear()

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


def on_load_from_decon_clicked(canvas_app, console_widget=None):
    """Load decon chapter PDFs to Learn directory via Mission Control"""
    if not canvas_app.course_detail_mgr:
        return
    if not hasattr(canvas_app, 'mission_control'):
        print("[ERROR] Mission Control not available")
        return

    # Extract data in main thread
    course_dir = canvas_app.course_detail_mgr.course_dir
    course_name = canvas_app.course_detail_mgr.get_course_name()

    def run(progress):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'func'))
        from procLearnMaterial import load_from_decon

        progress.update(progress=10, status=f"Loading from {course_name}...")
        print(f"📚 Load From Decon: {course_name}")

        copied_files = load_from_decon(course_dir, None)  # Pass None for console

        if copied_files:
            progress.finish(f"Loaded {len(copied_files)} chapters")
            print(f"✅ Successfully loaded {len(copied_files)} chapters")
            canvas_app.course_detail_signal.refresh_category.emit()
        else:
            progress.finish("No files loaded")
            print("! No files loaded")

    def on_success():
        canvas_app.show_toast("Chapters Loaded!", 'success')

    canvas_app.mission_control.start_task("Load From Decon", run, on_success=on_success)


def on_learn_material_clicked(canvas_app, console_widget=None):
    """Generate AI learning report for selected file via Mission Control"""
    if not canvas_app.course_detail_mgr:
        return
    if not hasattr(canvas_app, 'mission_control'):
        print("[ERROR] Mission Control not available")
        return

    # Get selected item from Learn category
    cdw = canvas_app.course_detail_window
    current_item = cdw.itemList.currentItem()

    if not current_item:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(cdw, "No Selection", "Please select a file from the Learn category first.")
        return

    # Get item data (UserRole + 1 contains the full dict)
    item_data = current_item.data(Qt.ItemDataRole.UserRole + 1)
    if not item_data or item_data.get('type') != 'learn_file':
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(cdw, "Invalid Selection", "Please select a valid learning material file.")
        return

    # Extract all data in main thread before starting worker
    file_path = item_data['data']['path']
    course_dir = canvas_app.course_detail_mgr.course_dir
    course_name = canvas_app.course_detail_mgr.get_course_name()
    filename = os.path.basename(file_path)

    # Get default prompt from preferences or fall back to built-in default
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'func'))
    from procLearnMaterial import get_default_prompt
    from gui.learn import get_prompt

    # Determine prompt type
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.py', '.js', '.java', '.cpp', '.c', '.go', '.rs', '.txt', '.md', '.json', '.xml', '.html', '.css', '.sh']:
        prompt_type = 'text'
    elif ext == '.csv':
        prompt_type = 'csv'
    else:
        prompt_type = 'pdf'

    # Try to get custom prompt from preferences first
    default_prompt = get_prompt(prompt_type)
    if not default_prompt:
        # Fall back to built-in default
        default_prompt = get_default_prompt(file_path)

    from PyQt6.QtWidgets import QInputDialog
    prompt, ok = QInputDialog.getMultiLineText(
        cdw,
        "Edit Learning Prompt",
        f"Customize AI prompt for: {filename}\n\n"
        f"Tip: Leave unchanged to use saved preferences",
        default_prompt
    )

    if not ok:
        return  # User cancelled

    custom_prompt = prompt.strip() if prompt.strip() else None

    def run(progress):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'func'))
        from procLearnMaterial import learn_material

        progress.update(progress=10, status=f"Processing {filename}...")
        print(f"📚 Learn: {filename} | Course: {course_name}")

        report_path = learn_material(file_path, course_dir, None, custom_prompt=custom_prompt, use_preferences=True)

        if report_path:
            progress.finish("Report generated!")
            print(f"✅ Report: {report_path}")
            canvas_app.course_detail_signal.refresh_category.emit()
        else:
            progress.fail("Failed to generate report")
            print("✗ Failed to generate learning report")

    def on_success():
        canvas_app.show_toast("Learn Report Done!", 'success')

    canvas_app.mission_control.start_task(f"Learn: {filename}", run, on_success=on_success)
