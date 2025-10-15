"""UI Interaction Logic for Canvas LMS Automation"""
import os, sys, json, threading, requests
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


class ThreadSafeConsole:
    """Thread-safe wrapper for QTextEdit console"""
    def __init__(self, console_widget):
        self.console = console_widget

    def append(self, text):
        """Thread-safe append to console"""
        # Use Qt's invokeMethod to safely call from any thread
        QMetaObject.invokeMethod(
            self.console,
            "append",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, str(text))
        )

def _create_console_tab(tw, name, with_progress=False):
    """Create console tab with optional progress widget

    Args:
        tw: QTabWidget
        name: Tab name
        with_progress: If True, include progress bar widget

    Returns:
        ThreadSafeConsole wrapper if with_progress=False
        tuple (ThreadSafeConsole, progress_widget) if with_progress=True
    """
    if with_progress:
        from gui.wgtProgress import create_console_with_progress
        console_widget, progress_widget = create_console_with_progress(tw, name)
        return ThreadSafeConsole(console_widget), progress_widget
    else:
        # Legacy: plain console tab
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
        tab, layout, console = QWidget(), QVBoxLayout(), QTextEdit()
        console.setReadOnly(True)
        console.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: 'Courier New', monospace; font-size: 11px;")
        layout.addWidget(console)
        tab.setLayout(layout)
        tw.setCurrentIndex(tw.addTab(tab, name))
        return ThreadSafeConsole(console)

def _run_in_thread(func, console, name, on_success=None, task_id=None):
    """Execute in daemon thread with task management

    Args:
        func: Function to run (receives console and stop_event)
        console: Console object
        name: Task name
        on_success: Callback on success
        task_id: Unique task ID (defaults to thread name)
    """
    from gui.mgrTask import get_task_manager

    console.append(f"[INFO] {name} started")

    # Create stop event
    stop_event = threading.Event()

    def wrapper():
        tid = task_id or threading.current_thread().name
        try:
            console.append(f"[INFO] Starting {name}...")

            # Check if function accepts stop_event parameter
            import inspect
            sig = inspect.signature(func)
            if 'stop_event' in sig.parameters:
                func(console, stop_event=stop_event)
            else:
                func(console)

            # Check if stopped
            if stop_event.is_set():
                console.append(f"[WARNING] {name} stopped by user")
            else:
                console.append(f"[SUCCESS] {name} completed")
                if on_success:
                    on_success()
        except Exception as e:
            if not stop_event.is_set():  # Don't show error if stopped
                import traceback
                console.append(f"[ERROR] {name} failed: {e}")
                console.append(traceback.format_exc())
        finally:
            # Unregister task
            get_task_manager().unregister_task(tid)

    # Start thread
    thread = threading.Thread(target=wrapper, daemon=True, name=task_id)
    thread.start()

    # Register task
    tid = task_id or thread.name
    get_task_manager().register_task(tid, name, thread, stop_event, console)

    return tid  # Return task ID for tracking

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
    """Execute getTodos and getHistoryTodos in parallel"""
    def run_todos(c):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from getTodos import main
        c.append("[INFO] Fetching upcoming TODOs...")
        main()
        c.append("[SUCCESS] Upcoming TODOs fetched")

    def run_history(c):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from getHistoryTodos import main
        c.append("[INFO] Fetching historical TODOs...")
        main()
        c.append("[SUCCESS] Historical TODOs fetched")

    def success():
        if mw:
            mw.main_handler.load_data()
            mw.main_handler.on_category_changed(mw.main_window.categoryList.currentRow())
            mw.show_toast("TODOs 获取完成！", 'success')

    # Launch both threads
    _run_in_thread(run_todos, _create_console_tab(tw, "Get TODO"), "getTodos", success)
    _run_in_thread(run_history, _create_console_tab(tw, "Get History"), "getHistoryTodos")

def on_get_course_clicked(tw, mw=None):
    """Execute getCourses"""
    def run(c):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from getCourses import main
        main()
        c.append("✓ Courses saved")
    def success():
        if mw:
            mw.main_handler.load_data()
            mw.update_status()
            mw.show_toast("Courses 获取完成！", 'success')
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


def on_load_from_decon_clicked(canvas_app):
    """Load decon chapter PDFs to Learn directory"""
    if not canvas_app.course_detail_mgr:
        return

    # Extract data in main thread
    course_dir = canvas_app.course_detail_mgr.course_dir
    course_name = canvas_app.course_detail_mgr.get_course_name()

    # Create console in main thread
    console = _create_console_tab(canvas_app.main_window.consoleTabWidget, "Load From Decon")

    def run(console):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from procLearnMaterial import load_from_decon

        console.append(f"{'='*80}")
        console.append(f"📚 Load From Decon: {course_name}")
        console.append(f"{'='*80}\n")

        copied_files = load_from_decon(course_dir, console)

        if copied_files:
            console.append(f"\n✅ Successfully loaded {len(copied_files)} chapters to Learn")
            # Trigger UI refresh
            canvas_app.course_detail_signal.refresh_category.emit()
            # Show toast
            canvas_app.show_toast(f"已加载 {len(copied_files)} 个章节！", 'success')
        else:
            console.append("\n! No files loaded")

    # Console already created above
    _run_in_thread(run, console, "Load From Decon")


def on_learn_material_clicked(canvas_app):
    """Generate AI learning report for selected file"""
    if not canvas_app.course_detail_mgr:
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
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gui'))
    from procLearnMaterial import get_default_prompt
    from cfgLearnPrefs import get_prompt

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
        "Edit Learning Prompt (编辑学习提示词)",
        f"Customize AI prompt for: {filename}\n\n"
        f"💡 Tip: Leave unchanged to use saved preferences\n\n"
        f"Available placeholders:\n"
        "  {{filename}} - File name\n"
        "  {{file_type}} - File type (for text files)\n"
        "  {{content}} - File content (for text files)\n"
        "  {{csv_preview}} - CSV preview (for CSV files)",
        default_prompt
    )

    if not ok:
        return  # User cancelled

    # If user cleared the prompt, use None to trigger preference loading in learn_material
    custom_prompt = prompt.strip() if prompt.strip() else None

    # Create console in main thread
    console = _create_console_tab(canvas_app.main_window.consoleTabWidget, f"Learn: {filename}")

    def run(console):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from procLearnMaterial import learn_material

        console.append(f"{'='*80}")
        console.append(f"📚 Learn: {filename}")
        console.append(f"Course: {course_name}")
        console.append(f"{'='*80}\n")

        report_path = learn_material(file_path, course_dir, console, custom_prompt=custom_prompt, use_preferences=True)

        if report_path:
            console.append(f"\n{'='*80}")
            console.append(f"✅ Learning report generated successfully!")
            console.append(f"📄 Report: {report_path}")
            console.append(f"{'='*80}")

            # Display report preview in console
            console.append(f"\n📖 Report Preview:")
            console.append("=" * 80)
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    report_content = f.read()
                    # Show first 1000 chars
                    preview = report_content[:1000]
                    if len(report_content) > 1000:
                        preview += "\n\n... (truncated, see full report at path above)"
                    console.append(preview)
            except Exception as e:
                console.append(f"! Could not read report: {e}")
            console.append("=" * 80)

            # Trigger UI refresh to show report indicator
            canvas_app.course_detail_signal.refresh_category.emit()
            # Show toast
            canvas_app.show_toast(f"Learn 报告生成完成！", 'success')
        else:
            console.append("\n✗ Failed to generate learning report")
            canvas_app.show_toast("Learn 生成失败", 'error')

    # Console already created above, just run thread
    _run_in_thread(run, console, f"Learn: {filename}")
