# CLAUDE.md - AI Assistant Development Guide

This file provides essential guidance for Claude Code and other AI assistants when working with this Canvas LMS automation codebase.

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Dependency Flow](#architecture--dependency-flow)
3. [Core Modules](#core-modules)
4. [Data Structures](#data-structures)
5. [Technical Patterns](#technical-patterns)
6. [Development Guidelines](#development-guidelines)

---

## Project Overview

**Canvas LMS Automation System** - Full-stack Python automation with PyQt6 GUI for Penn State University Canvas platform.

### Key Technologies

- **GUI**: PyQt6 (6 windows, modular handlers, qt.py: 227 lines)
- **Backend**: Python 3.10+
- **Auth**: Selenium + TOTP (pyotp)
- **AI**: Gemini + Claude (unified via utilPromptFiles, dynamic model fetching, robust retry logic)
- **Web**: requests, lxml, concurrent.futures (high-performance fetching)
- **Config**: Hot-reload support for seamless updates

### High-Level Architecture (Post-Refactor)

```
main.py → gui/qt.py (CanvasApp - 227 lines, 87% reduction)
    ├─> 6 Windows + Floating Sidebar
    ├─> qt_utils/ (Modular Architecture)
    │   ├─> window_handlers/ (7 handlers: Main, Launcher, Auto, etc.)
    │   ├─> event_handlers/ (Keyboard)
    │   ├─> content_processors/ (HTML, TabLoader, Preview)
    │   └─> initializers/ (UI, Signal)
    ├─> Managers (mgr prefix): mgrData, mgrDone, mgrCourseDetail, mgrAutoDetail
    ├─> func/ (get/proc/util prefix): getTodos, getHomework, getQuiz_ultra, utilPromptFiles
    └─> misc/jsons/ (cookies.json, todos.json, course.json, his_todo.json)
```

---

## Architecture & Dependency Flow

### Startup Flow (Modular)

```
main.py → CanvasApp.__init__()
├─> UIInitializer.init_qt() - Load 6 windows + floating sidebar
├─> SignalInitializer.init_button_bindings() - Connect all signals
├─> UIInitializer.init_data_viewer() - Load data + show launcher
├─> check_status() - Run 5 validators (account, cookie, todos, network, courses)
└─> Window: 1600x900, Sidebar: 70px collapsed → 200px on hover
```

### Naming Convention (Standardized)

**GUI Files** (`gui/`):
- `mgr*.py` - Managers (mgrData, mgrDone, mgrTask)
- `rdr*.py` - Renderers (rdrDelegates, rdrToast)
- `wgt*.py` - Widgets (wgtSidebar, wgtIOSToggle)
- `util*.py` - Utilities (utilQtInteract, utilFormatters)
- `cfg*.py` - Config (cfgModel, cfgStyles, cfgLearnPrefs)

**Func Files** (`func/`):
- `get*.py` - Fetch data (getTodos, getCourses, getHomework)
- `proc*.py` - Process data (procLearnMaterial)
- `util*.py` - Utilities (utilPromptFiles, utilModelSelector)
- `mgr*.py` - Managers (mgrHistory)

### Authentication Flow

**Automatic Mode** (with TOTP key):
```
User: Click "Get Cookie"
└─> qt_interact.on_get_cookie_clicked()
    └─> [Thread] login/getCookie.py:main()
        ├─> get_cookies(account, password, otp_key)
        │   ├─> Selenium WebDriver (Chrome)
        │   ├─> Navigate to https://psu.instructure.com/login
        │   ├─> human_type(account) + Submit (50-150ms/char delay)
        │   ├─> human_type(password) + Submit
        │   ├─> Wait for 2FA page (30s timeout)
        │   ├─> [3 retries] TOTP verification
        │   │   └─> getTotp.generate_token(otp_key) → pyotp.TOTP(key).now()
        │   └─> driver.get_cookies()
        └─> Save to cookies.json (24h validity)
```

**Manual 2FA Mode** (for users without TOTP key):
```
User: Enable "Manual 2FA Mode" toggle in Settings → Save with empty TOTP key
    → otp_key saved as "loginself" in account_config.json

User: Click "Get Cookie"
└─> qt_interact.on_get_cookie_clicked()
    └─> [Thread] login/getCookie.py:main()
        ├─> get_cookies(account, password, "loginself")
        │   ├─> Selenium WebDriver (Chrome)
        │   ├─> Navigate to https://psu.instructure.com/login
        │   ├─> human_type(account) + Submit
        │   ├─> human_type(password) + Submit
        │   ├─> Print: "MANUAL 2FA MODE - Complete 2FA in browser"
        │   ├─> Wait for user to manually complete 2FA (5min timeout)
        │   ├─> Wait for dashboard detection
        │   └─> driver.get_cookies()
        └─> Save to cookies.json (24h validity)
```

### Data Fetching Flow

```
[GET TODOS]
qt_interact.on_get_todo_clicked()
└─> [Thread] func/getTodos.py:main()
    ├─> GET /api/v1/planner/items (Concurrent/Paginated)
    ├─> process_and_save_todos_concurrent(raw_todos, session)
    │   ├─> ThreadPoolExecutor (20 workers)
    │   ├─> For each TODO (Parallel):
    │   │   ├─> fetch_assignment_details(session, url)
    │   │   │   ├─> Parse URL → course_id + assignment_id/quiz_id
    │   │   │   ├─> GET /api/v1/courses/{cid}/assignments/{aid}
    │   │   │   ├─> extract_file_ids(description) → Regex match
    │   │   │   ├─> [If files] create_assignment_folder() + download_file()
    │   │   │   │   └─> Structure: todo/{name}_{timestamp}/
    │   │   │   │       ├── files/
    │   │   │   │       └── auto/
    │   │   │   │           ├── input/
    │   │   │   │           └── output/
    │   │   │   └─> Return assignment_details: {type, submitted, files, folder, ...}
    │   │   └─> Update existing dict
    │   └─> Sort by due_date → Save to todos.json
    └─> display_todos(todos)

[GET COURSES]
qt_interact.on_get_course_clicked()
└─> [Thread] func/getCourses.py:main()
    ├─> GET /api/v1/courses
    ├─> For each course: GET /api/v1/courses/{cid}/tabs
    └─> Save to course.json
```

### Homework Automation Flow

```
User: Double-click TODO → AutoDetail → Preview
└─> on_hw_again_clicked()
    └─> [Thread] func/getHomework.py:run_gui(url, product, model, prompt, ref_files, folder)
        ├─> Clear auto/output/
        ├─> get_homework_details(url) → {assignment, submission}
        ├─> ask_llm_with_pdfs(description, product, model, prompt, ref_files)
        │   └─> upPromptFiles.call_ai() → AI response
        ├─> parse_img_requests(answer) → Extract [gen_img] tags
        ├─> Save answer.md → auto/output/
        ├─> generate_images(img_requests) → Gemini image generation
        ├─> md_to_docx(auto/output/answer.docx, answer.md)
        │   └─> python-docx.Document() + markdown parsing
        └─> Signal: preview_refresh.emit()

User: Submit
└─> on_hw_submit_clicked()
    └─> [Thread] func/getHomework.py:submit_to_canvas(url)
        ├─> Scan auto/output/ → Find all files
        ├─> [4-step upload] For each file:
        │   ├─> POST /files/pending → {upload_url, upload_params}
        │   ├─> POST {upload_url} → Upload to Canvas/S3
        │   ├─> GET {Location header} → {id: file_id}
        │   └─> Collect file_ids
        └─> POST /courses/{cid}/assignments/{aid}/submissions
            └─> Data: {submission[attachment_ids]: "123,456"}
```

### Quiz Automation Flow

```
User: Double-click Quiz → AutoDetail (Status Bar: Score|Best|Attempts|🔴进行中/⚪未开始/✅已完成/🟡可重试)
└─> QTimer(500ms) → func/getQuizStatus.py:get_quiz_status(url) → quiz_status_update signal
└─> on_quiz_again_clicked()
    └─> [Thread] func/getQuiz_ultra.py:run_gui(url, product, model, prompt, folder, thinking)
        ├─> Clear auto/output/
        ├─> GET {url}/take - Auto-start quiz
        ├─> parse_questions(html, base_url, auto/output/)
        │   ├─> XPath: //*[@id="questions"]/div[@class="question"]
        │   ├─> For each question:
        │   │   ├─> Extract id, text, images
        │   │   ├─> Download images → auto/output/images/
        │   │   └─> Extract answers: {id, text, images}
        │   └─> Return questions list
        ├─> save_preview(questions, html, auto/output/)
        ├─> get_answers(questions, product, model, prompt, thinking)
        │   ├─> Build question dict with image mapping
        │   ├─> upPromptFiles.call_ai(full_prompt, ..., thinking=True)
        │   │   └─> [Claude thinking] params["thinking"] = {"type": "enabled", "budget_tokens": 8000}
        │   ├─> Parse JSON response
        │   └─> Return {"question_97585716": "7574", ...}
        ├─> save_answers(questions, answers, auto/output/) → QesWA.md
        └─> Signal: preview_refresh.emit()

User: Submit
└─> on_quiz_submit_clicked()
    └─> [Thread] func/getQuiz_ultra.py:submit(session, url, doc, questions, answers)
        ├─> XPath extract form: //form[@id="submit_quiz_form"]
        ├─> Build POST data: hidden fields + answers
        └─> POST {quiz_url}/submissions
```

---

## Core Modules

### gui/qt.py - Lightweight Router (227 lines, 87% reduction)

**CanvasApp** - Delegates all business logic to handlers

```python
class CanvasApp(QMainWindow):
    def __init__(self):
        # Data Managers
        self.dm, self.done_mgr = DataManager(), DoneManager()

        # 7 Window Handlers (all logic delegated)
        self.launcher_handler = LauncherHandler(self)
        self.main_handler = MainWindowHandler(self)
        self.automation_handler = AutomationWindowHandler(self)
        self.course_detail_handler = CourseDetailWindowHandler(self)
        self.auto_detail_handler = AutoDetailWindowHandler(self)
        self.sitting_handler = SittingWindowHandler(self)
        self.keyboard_handler = KeyboardHandler(self)

        # Initialize (now in separate initializers)
        UIInitializer.init_qt(self)           # Load 6 UI + sidebar
        SignalInitializer.init_button_bindings(self)  # Connect signals
        UIInitializer.init_data_viewer(self)  # Load data
```

**Sidebar Widget** (`wgtSidebar.py`):
- Floating right-side overlay (doesn't occupy space)
- Smooth animation: 70px → 200px on hover (200ms OutCubic)
- Auto-repositions during window resize
- Extensible: `update_tools(actions)` for per-page tools

### gui/qt_interact.py - Button Handlers

**Threading Pattern**:

```python
def _run_in_thread(func, console, name, on_success=None):
    """Execute function in daemon thread with console output"""
    console.append(f"[INFO] {name} started")

    def wrapper():
        try:
            func(console)
            console.append(f"[SUCCESS] {name} completed")
            if on_success:
                on_success()
        except Exception as e:
            console.append(f"[ERROR] {name} failed: {e}")
            console.append(traceback.format_exc())

    threading.Thread(target=wrapper, daemon=True).start()
```

### gui/data_manager.py - Data Management

```python
class DataManager:
    def load_all(self):
        self._load_courses()  # course.json
        self._load_todos()    # todos.json
        self._load_files()    # Scan TODO_DIR

    def classify_todo(self, todo):
        """Returns: {is_quiz, is_discussion, is_automatable, is_homework, is_open}"""
        ad = todo.get('assignment_details', {})
        types = ad.get('type', [])

        # Determine type flags
        is_quiz = 'quiz' in todo.get('redirect_url', '').lower()
        is_discussion = 'discussion' in todo.get('redirect_url', '').lower()
        is_automatable = any(t in types for t in [
            'online_quiz', 'online_upload', 'online_text_entry', 'discussion_topic'
        ])

        # Determine open status
        is_open = not ad.get('submitted', False) and not ad.get('locked_for_user', False)
        if is_quiz and 'quiz_metadata' in ad:
            qm = ad['quiz_metadata']
            if qm.get('locked_for_user') or qm.get('attempts_left', 1) <= 0:
                is_open = False

        return {
            'is_quiz': is_quiz,
            'is_discussion': is_discussion,
            'is_automatable': is_automatable,
            'is_homework': not (is_quiz or is_discussion),
            'is_open': is_open
        }
```

### gui/delegates.py - Custom Rendering

**TodoItemDelegate** - Urgency-based gradient + custom overlays

```python
class TodoItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # STEP 1: Calculate urgency color
        todo = index.data(Qt.ItemDataRole.UserRole + 1)
        if todo and todo.get('due_date'):
            hours_left = calculate_hours_left(todo['due_date'])

            if hours_left <= 0:
                urgency_color = QColor(100, 0, 0, 150)  # OVERDUE
            else:
                t = min(hours_left / 168, 1.0)  # 168h = 7 days
                urgency = math.exp(-3 * t)
                r = int(urgency ** 0.7 * 100)
                g = int((1 - urgency ** 1.5) * 100)
                alpha = int(60 + urgency * 90)
                urgency_color = QColor(r, g, 0, alpha)

            painter.fillRect(option.rect, urgency_color)

        # STEP 2: Paint default content (text, checkbox)
        super().paint(painter, option, index)

        # STEP 3: Paint custom overlays (dots, labels, date)
        # [Right to left: dots, type labels, due date]
```

### func/utilPromptFiles.py - Unified AI Interface

```python
def call_ai(prompt, product, model, files=[], uploaded_info=None, thinking=False):
    """Unified AI calling interface"""
    if product == 'Gemini':
        return _gemini(prompt, model, uploaded_info=uploaded_info)
    elif product == 'Claude':
        return _claude(prompt, model, uploaded_info=uploaded_info, thinking=thinking)

def _gemini(prompt, model, uploaded_info=None):
    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    # 构建 contents
    contents = [prompt]
    if uploaded_info:
        # 添加上传的文件
        contents.extend([info['uploaded_obj'] for info in uploaded_info])

    # 调用 API
    response = client.models.generate_content(
        model=model,
        contents=contents
    )
    return response.text

def _claude(prompt, model, uploaded_info=None, thinking=False):
    import anthropic
    client = anthropic.Anthropic(api_key=config.CLAUDE_API_KEY)

    # Build content
    content = [{"type": "text", "text": prompt}]
    if uploaded_info:
        for info in uploaded_info:
            content.append({
                "type": info['type'],  # 'image' or 'document'
                "source": {
                    "type": "base64",
                    "media_type": info['mime'],
                    "data": info['data']
                }
            })

    # Build params
    params = {
        "model": model,
        "max_tokens": 16384,
        "messages": [{"role": "user", "content": content}]
    }

    if thinking:
        params["thinking"] = {"type": "enabled", "budget_tokens": 8000}

    msg = client.messages.create(**params)
    return next(block.text for block in msg.content if hasattr(block, 'text'))
```

---

## Data Structures

### JSON Files

**account_config.json** (User-created, Git-ignored)
```json
{
  "account": "user@psu.edu",
  "password": "password",
  "otp_key": "BASE32_TOTP_SECRET",
  "gemini_api_key": "AIza...",
  "claude_api_key": "sk-ant-..."
}
```

**cookies.json** (Auto-generated, 24h validity)
```json
[
  {"name": "_csrf_token", "value": "abc123...", "domain": ".instructure.com", ...},
  {"name": "canvas_session", "value": "xyz789...", ...}
]
```

**todos.json** (Auto-generated, sorted by due_date)
```json
[
  {
    "course_name": "BISC 4",
    "name": "Week 5 Quiz",
    "due_date": "2025-10-20T23:59:00Z",
    "points_possible": 10,
    "redirect_url": "https://psu.instructure.com/courses/2418560/quizzes/5363417",
    "assignment_details": {
      "type": ["online_quiz"],
      "submitted": false,
      "locked_for_user": false,
      "folder": "Week_5_Quiz_20251020_235900",
      "assignment_folder": "/path/to/todo/Week_5_Quiz_20251020_235900",
      "quiz_metadata": {
        "question_count": 15,
        "attempt": 0,
        "allowed_attempts": 2,
        "attempts_left": 2
      }
    }
  }
]
```

### File System Structure

```
canvas_decon/
├── Courses/                              # Course materials (Git-ignored)
│   └── bisc_4_2418560/                   # {name}_{course_id}
│       ├── Syll/                         # Syllabus files
│       ├── Files/Textbook/               # Manually placed
│       └── Tabs/                         # Auto-cached tab content
│
└── todo/                                 # TODO workspace (Git-ignored)
    └── Week_5_Quiz_20251020_235900/      # {name}_{timestamp}
        ├── files/                        # Downloaded reference files
        └── auto/
            ├── input/                    # User-placed input files
            └── output/                   # Auto-generated outputs
                ├── answer.md
                ├── answer.docx
                ├── questions.md
                ├── QesWA.md
                └── images/
```

---

## Technical Patterns

### 1. Threading Pattern

**Rule**: All long-running operations MUST run in background threads

```python
# ✅ CORRECT
def on_button_clicked(console_tab_widget):
    def run(console):
        result = some_api_call()
        console.append(f"Result: {result}")

    console = _create_console_tab(console_tab_widget, "Task")
    _run_in_thread(run, console, "Task", on_success=refresh_ui)

# ❌ INCORRECT (blocks UI)
def on_button_clicked():
    result = some_api_call()  # Freezes GUI
```

### 2. Signal/Slot Pattern (Thread-safe UI Updates)

```python
# Define signals
class AutoDetailSignal(QObject):
    status_update = pyqtSignal(str)
    preview_refresh = pyqtSignal()
    quiz_not_started = pyqtSignal()
    quiz_status_update = pyqtSignal(dict)  # Real-time quiz status (0.5s timer)

# Connect in __init__
self.auto_detail_signal.quiz_status_update.connect(self._update_quiz_status)

# Emit from worker thread (thread-safe!)
def worker():
    status = get_quiz_status(url)  # func/getQuizStatus.py
    self.auto_detail_signal.quiz_status_update.emit(status)
```

### 3. Event Filter Pattern (Keyboard Navigation)

```python
def eventFilter(self, obj, event):
    if event.type() == QEvent.Type.KeyPress:
        key = event.key()
        modifiers = event.modifiers()

        # Handle WASD navigation
        if key in [Qt.Key.Key_W, Qt.Key.Key_S]:
            if isinstance(obj, QListWidget):
                self._handle_navigation(key, obj)
                return True  # Block propagation

        # Handle shortcuts (check Shift first!)
        if key == Qt.Key.Key_A and (modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.on_automation_clicked()
            return True

    return super().eventFilter(obj, event)
```

### 4. Delegate Pattern (Custom Rendering)

**Critical Rule**: NEVER use `setItemDelegate(None)` in PyQt6

```python
# ✅ CORRECT
if use_custom:
    list_widget.setItemDelegate(CustomDelegate())
else:
    list_widget.setItemDelegate(QStyledItemDelegate())  # Use default, not None!

list_widget.viewport().update()  # Force repaint

# ❌ INCORRECT
list_widget.setItemDelegate(None)  # Causes rendering bugs!
```

### 5. Canvas API Patterns

**URL Parsing**
```python
from urllib.parse import urlparse

path = urlparse(url).path.split('/')
course_id = path[path.index('courses') + 1]

if 'quizzes' in path:
    quiz_id = path[path.index('quizzes') + 1]
elif 'assignments' in path:
    assignment_id = path[path.index('assignments') + 1]
```

**Session Management**
```python
cookies = {c['name']: c['value'] for c in json.load(open(config.COOKIES_FILE))}
session = requests.Session()
session.cookies.update(cookies)
session.headers.update({
    'Accept': 'application/json+canvas-string-ids',
    'User-Agent': 'Mozilla/5.0 ...'
})
```

**File Upload (4-step)**
```python
# 1. Request upload token
r = session.post('/files/pending', data={
    'attachment[filename]': filename,
    'attachment[size]': str(file_size)
})
upload_info = r.json()

# 2. Upload to S3
r = session.post(upload_info['upload_url'], files={'file': ...}, allow_redirects=False)

# 3. Confirm upload
r = session.get(r.headers['location'])
file_id = str(r.json()['id'])

# 4. Submit with file IDs
session.post(f'/courses/{cid}/assignments/{aid}/submissions',
    data={'submission[attachment_ids]': ','.join(file_ids)})
```

### 6. XPath Patterns (Quiz Parsing)

```python
from lxml import html

doc = html.fromstring(response.content)

# Extract questions
question_divs = doc.xpath('//*[@id="questions"]/div[contains(@class, "question")]')

for qdiv in question_divs:
    # Extract question ID
    qcontainer = qdiv.xpath('.//div[starts-with(@id, "question_")]')[0]
    question_id = qcontainer.get('id')

    # Extract question text
    qtext = qcontainer.xpath('.//div[contains(@class, "question_text")]')[0].text_content()

    # Extract answers
    answers = qcontainer.xpath('.//input[@type="radio"]')
    for ainput in answers:
        answer_id = ainput.get('value')
        label = qcontainer.xpath(f'.//label[@for="{ainput.get("id")}"]')[0]
```

### 7. Concurrency & Feedback Patterns

**Concurrent Data Fetching**
Use `concurrent.futures.ThreadPoolExecutor` for IO-bound tasks (API calls, file downloads).
```python
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(fetch_func, arg): arg for arg in items}
    for future in concurrent.futures.as_completed(futures):
        # Process result
```

**Real-time Status Callbacks**
Pass a callback to deep logic functions to stream status updates to the UI without coupling.
```python
# In GUI Handler
status_cb = lambda msg: console.append(msg)
call_ai(..., status_callback=status_cb)

# In Logic Function
if status_callback:
    status_callback("Waiting for rate limit...")
```

### 8. Drag & Drop Pattern (PyQt6)

**Custom ListWidget**
Override `dragMoveEvent` and `dropEvent` for specific handling.
```python
class DropListWidget(QListWidget):
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            # Handle file drop
            self.on_drop_callback(files)
```

---

## Development Guidelines

### Code Organization Rules

1. **Separation of Concerns**
   - `gui/qt.py` → UI structure + window management
   - `gui/qt_interact.py` → Button handlers + threading
   - `func/` → Business logic (must work standalone + GUI-callable)

2. **Path Management**
   - ALL paths use `config.py` definitions
   - NEVER hardcode paths
   - Use `os.path.join()` for cross-platform

3. **Module Imports**
   ```python
   sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
   import config
   ```

### Thread Safety Rules

1. **UI Updates from Threads**
   - ✅ Use Qt signals: `self.signal.emit(data)`
   - ❌ Direct widget access: `self.label.setText(text)`

2. **Console Output**
   ```python
   def my_function(console=None):
       if console:
           console.append("[INFO] Starting...")
       else:
           print("[INFO] Starting...")
   ```

### Common Pitfalls

1. **❌ Using `input()` in GUI-callable functions**
   ```python
   # BAD - Freezes GUI
   def my_function():
       answer = input("Continue? ")

   # GOOD - Use QMessageBox
   def my_function():
       QMessageBox.question(...)
   ```

2. **❌ Forgetting `console` parameter**
   ```python
   # BAD - Output goes to terminal only
   def my_function():
       print("Starting...")

   # GOOD - Dual-mode support
   def my_function(console=None):
       if console:
           console.append("[INFO] Starting...")
       else:
           print("[INFO] Starting...")
   ```

3. **❌ Hardcoding paths**
   ```python
   # BAD
   output_dir = "/Users/me/project/output"

   # GOOD
   output_dir = config.OUTPUT_DIR
   ```

4. **❌ Blocking main thread**
   ```python
   # BAD
   def on_button_clicked():
       time.sleep(5)  # Freezes GUI

   # GOOD
   def on_button_clicked():
       threading.Thread(target=lambda: time.sleep(5), daemon=True).start()
   ```

### Adding New Features

**Process**:

1. **Design Phase**
   - Identify operation length (short/long)
   - Decide mode: GUI-only, CLI-only, or dual
   - Check existing patterns in `misc/`

2. **Implementation Phase**
   - Long operation → Create module in `func/`
   - GUI integration → Add button + binding + handler
   - Threading → Use `_run_in_thread()` pattern
   - Console output → Add progress messages

3. **Testing Phase**
   - Test CLI: `python func/new_module.py`
   - Test GUI: Click button + verify console
   - Test errors: Force failure + check traceback

---

## Quick Reference

### File Locations (Functional Domains)

```
# Core
main.py, config.py, checkStatus.py, clean.py
gui/qt.py                       # 227-line router

# GUI (Modular by Domain)
gui/core/                       # Base: mgrData, mgrDone, mgrTask, utilQtInteract
gui/details/                    # Detail managers: mgrAutoDetail, mgrCourseDetail
gui/learn/                      # Learn system: cfgLearnPrefs, rdrLearnSitting, utilFormatters
gui/widgets/                    # UI: wgtSidebar, wgtIOSToggle, rdrDelegates, rdrToast, wgtProgress
gui/config/                     # Config: cfgModel, cfgStyles
gui/qt_utils/                   # Handlers: window_handlers/, event_handlers/, initializers/

# Business Logic
func/                           # getTodos, getCourses, getHomework, getQuiz_ultra, getQuizStatus, utilPromptFiles
login/                          # getCookie, getTotp
misc/jsons/                     # Runtime data: todos.json, cookies.json, course.json
```

### Key Constants (config.py)

```python
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
JSONS_DIR = os.path.join(ROOT_DIR, 'misc', 'jsons')

COOKIES_FILE = os.path.join(JSONS_DIR, 'cookies.json')
TODOS_FILE = os.path.join(JSONS_DIR, 'todos.json')
COURSE_FILE = os.path.join(JSONS_DIR, 'course.json')
ACCOUNT_CONFIG_FILE = os.path.join(ROOT_DIR, 'account_config.json')
TODO_DIR = os.path.join(ROOT_DIR, 'todo')
COURSES_DIR = os.path.join(ROOT_DIR, 'Courses')

CANVAS_BASE_URL = "https://psu.instructure.com"
```

### Common Operations

```bash
# Start GUI
python main.py

# CLI mode
python func/getTodos.py
python func/getHomework.py --url "..." --product Gemini
python func/getQuiz_ultra.py --url "..." --product Claude --thinking

# Status check
python checkStatus.py

# Clean
python clean.py
```

---

## Important Reminders

### Security
- NEVER commit `account_config.json`
- Cookies auto-expire after 24 hours
- Treat TOTP secret like password

### Technical Limitations
- Cookie expiry: 24h (requires re-login)
- API quotas: Gemini/Claude daily limits
- Quiz support: Multiple choice only
- Image recognition: Depends on AI vision

---

**When in doubt, follow existing patterns. Check `misc/` for legacy implementations before creating new code.**