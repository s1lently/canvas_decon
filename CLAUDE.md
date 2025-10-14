# CLAUDE.md - AI Assistant Development Guide

This file provides comprehensive guidance for Claude Code and other AI assistants when working with this Canvas LMS automation codebase.

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Complete Dependency Tree](#complete-dependency-tree)
3. [Core Modules Deep Dive](#core-modules-deep-dive)
4. [Data Flow Architecture](#data-flow-architecture)
5. [Technical Patterns](#technical-patterns)
6. [Development Guidelines](#development-guidelines)

---

## Project Overview

**Canvas LMS Automation System** - Full-stack Python automation with PyQt6 GUI for Penn State University Canvas platform.

### Key Technologies

- **GUI**: PyQt6 (6 windows, 10 modules, ~2500 lines)
- **Backend**: Python 3.10+
- **Auth**: Selenium + TOTP (pyotp)
- **AI**: Gemini API + Claude API (unified interface)
- **Web**: requests, lxml, BeautifulSoup4
- **Document**: python-docx, Pillow, markdown

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                             │
│                    (Entry Point)                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  gui/qt.py (CanvasApp)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 6 Windows: Main, Launcher, Sitting, Automation,     │  │
│  │            CourseDetail, AutoDetail                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Managers: DataManager, DoneManager,                  │  │
│  │           CourseDetailManager, AutoDetailManager     │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Custom Widgets: IOSToggle, TodoItemDelegate          │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌───────────────┐ ┌──────────────┐ ┌────────────────┐
│ login/        │ │ func/        │ │ checkStatus.py │
│ getCookie.py  │ │ getTodos.py  │ │ (5 validators) │
│ getTotp.py    │ │ getHomework  │ └────────────────┘
└───────────────┘ │ getQuiz      │
                  │ upPromptFiles│
                  └──────────────┘
```

---

## Complete Dependency Tree

### 🌳 Startup Flow (main.py → GUI)

```
main.py:main()
├─> init()
│   ├─> QApplication()
│   ├─> setStyleSheet(DARK_THEME)  # gui/styles.py
│   └─> init_qt_window()  # gui/qt.py
│       ├─> CanvasApp.__init__()
│       │   ├─> DataManager()  # gui/data_manager.py
│       │   ├─> DoneManager()  # gui/done_manager.py
│       │   ├─> init_qt()  # Load 6 UI files + setup widgets
│       │   │   ├─> loadUi(main.ui)
│       │   │   ├─> loadUi(launcher.ui)
│       │   │   ├─> loadUi(sitting.ui)
│       │   │   ├─> loadUi(automation.ui)
│       │   │   ├─> loadUi(course_detail.ui)
│       │   │   ├─> loadUi(autoDetail.ui)
│       │   │   ├─> IOSToggle() × 8  # gui/ios_toggle.py
│       │   │   └─> model_config.load_default_config()  # gui/model_config.py
│       │   ├─> init_button_bindings()  # Connect all signals
│       │   ├─> init_data_viewer()
│       │   │   ├─> history_manager.archive_past_todos()
│       │   │   └─> _show_launcher()  # Show launcher overlay
│       │   └─> check_status()  # Initial status check + auto-fix
│       │       ├─> checkStatus.get_all_status()
│       │       │   ├─> check_account_info()
│       │       │   ├─> check_cookie_validity()
│       │       │   ├─> check_todo_list()
│       │       │   ├─> check_network()
│       │       │   └─> check_course_list()
│       │       └─> [Auto-fix] Expired/missing data → auto-run scripts
│       └─> [Daemon Threads]
│           ├─> status_update_thread (every 30s)
│           └─> archive_thread (every 5min)
└─> window.show() → app.exec()
```

### 🔐 Authentication Flow

```
User Action: Click "Get Cookie"
├─> qt_interact.on_get_cookie_clicked()
│   └─> [Background Thread] _run_in_thread()
│       ├─> login/getCookie.py:main()
│       │   ├─> Load account_config.json
│       │   └─> get_cookies(account, password, otp_key)
│       │       ├─> Selenium WebDriver (Chrome)
│       │       ├─> Navigate to https://psu.instructure.com/login
│       │       ├─> human_type(account) + human_click(Submit)
│       │       │   └─> 50-150ms delay per character
│       │       ├─> human_type(password) + human_click(Submit)
│       │       ├─> Wait for 2FA page (30s timeout)
│       │       ├─> [3 retries] TOTP verification
│       │       │   ├─> getTotp.generate_token(otp_key)
│       │       │   │   └─> pyotp.TOTP(key).now()
│       │       │   ├─> human_type(token)
│       │       │   └─> Wait for dashboard
│       │       ├─> driver.get_cookies()
│       │       └─> driver.quit()
│       └─> Save to cookies.json
│           [
│             {"name": "_csrf_token", "value": "...", ...},
│             {"name": "canvas_session", "value": "...", ...}
│           ]
└─> [Success Callback] update_status()
```

### 📚 Data Fetching Flow

```
[GET COURSES]
qt_interact.on_get_course_clicked()
└─> [Thread] func/getCourses.py:main()
    ├─> Load cookies.json → requests.Session
    ├─> GET /api/v1/courses
    ├─> For each course:
    │   └─> GET /api/v1/courses/{cid}/tabs
    └─> Save to course.json
        {
          "base_url": "https://psu.instructure.com",
          "courses": [
            {
              "id": 2418560,
              "name": "BISC 4, Section 001: Human Body",
              "tabs": {
                "Home": "/courses/2418560",
                "Modules": "/courses/2418560/modules",
                "Grades": "/courses/2418560/grades",
                "Syllabus": "/courses/2418560/assignments/syllabus"
              }
            }
          ]
        }

[GET TODOS]
qt_interact.on_get_todo_clicked()
└─> [Thread] func/getTodos.py:main()
    ├─> Load cookies.json → requests.Session
    ├─> get_todos(session, days=365)
    │   ├─> GET /api/v1/planner/items (paginated, 100 per page)
    │   └─> Filter: assignment, quiz, discussion_topic
    ├─> process_and_save_todos(raw_todos, session)
    │   ├─> Merge with existing todos.json (by redirect_url)
    │   ├─> For each TODO:
    │   │   ├─> fetch_assignment_details(session, url)
    │   │   │   ├─> Parse URL → course_id + assignment_id/quiz_id/topic_id
    │   │   │   ├─> GET /api/v1/courses/{cid}/assignments/{aid}
    │   │   │   │   or /api/v1/courses/{cid}/quizzes/{qid}
    │   │   │   │   or /api/v1/courses/{cid}/discussion_topics/{tid}
    │   │   │   ├─> extract_file_ids(description)
    │   │   │   │   └─> Regex: /courses/(\d+)/files/(\d+)
    │   │   │   ├─> [If files exist]
    │   │   │   │   ├─> create_assignment_folder(TODO_DIR, name, due_date)
    │   │   │   │   │   └─> todo/{sanitized_name}_{timestamp}/
    │   │   │   │   │       ├── files/
    │   │   │   │   │       └── auto/
    │   │   │   │   │           ├── input/
    │   │   │   │   │           └── output/
    │   │   │   │   └─> For each file_id:
    │   │   │   │       └─> download_file(session, /files/{fid}/download)
    │   │   │   │           └─> Save to files/ directory
    │   │   │   ├─> [Quiz special handling]
    │   │   │   │   ├─> GET /api/v1/courses/{cid}/quizzes/{qid}/submissions
    │   │   │   │   └─> Calculate attempts_left = allowed_attempts - attempt
    │   │   │   └─> Return assignment_details:
    │   │   │       {
    │   │   │         "type": ["online_quiz", "online_upload"],
    │   │   │         "submitted": false,
    │   │   │         "locked_for_user": false,
    │   │   │         "files": [...],
    │   │   │         "folder": "folder_name",
    │   │   │         "assignment_folder": "/full/path",
    │   │   │         "quiz_metadata": {
    │   │   │           "question_count": 15,
    │   │   │           "attempt": 0,
    │   │   │           "allowed_attempts": 2,
    │   │   │           "attempts_left": 2
    │   │   │         }
    │   │   │       }
    │   │   └─> Update existing dict
    │   └─> Sort by due_date → Save to todos.json
    └─> display_todos(todos)
```

### 🤖 Homework Automation Flow

```
User Action: Double-click automatable TODO → AutoDetail → Preview
├─> on_hw_again_clicked()  # qt.py:847
│   └─> [Thread] func/getHomework.py:run_gui(url, product, model, prompt, ref_files, assignment_folder)
│       ├─> Clear auto/output/
│       ├─> get_homework_details(url)
│       │   ├─> Parse URL → course_id + assignment_id
│       │   ├─> GET /api/v1/courses/{cid}/assignments/{aid}
│       │   ├─> GET /api/v1/courses/{cid}/assignments/{aid}/submissions/self
│       │   └─> Return {assignment: {...}, submission: {...}}
│       ├─> Load personal_info.json
│       ├─> Extract description (HTML → text)
│       ├─> ask_llm_with_pdfs(description, product, model, prompt, ref_files)
│       │   ├─> Build full prompt (prompt + personal_context + description)
│       │   └─> upPromptFiles.call_ai()
│       │       ├─> [Gemini]
│       │       │   ├─> genai.upload_file(pdf) → uri
│       │       │   ├─> GenerativeModel(model)
│       │       │   └─> generate_content([prompt, file_obj_1, ...])
│       │       └─> [Claude]
│       │           ├─> base64 encode PDFs
│       │           ├─> Build content = [{"type": "text"}, {"type": "document", ...}]
│       │           └─> messages.create(model, messages=[...])
│       ├─> [Validate] Check for [no] in response
│       ├─> parse_img_requests(answer)
│       │   ├─> Regex: \[gen_img\]\n\{name: xxx.png\ndes: ...\}
│       │   └─> Return (clean_answer, img_requests)
│       ├─> Save answer.md → auto/output/
│       ├─> generate_images(img_requests)
│       │   ├─> google.genai.Client(api_key)
│       │   └─> For each request:
│       │       └─> client.models.generate_content(model="gemini-2.5-flash-image", ...)
│       │           └─> PIL.Image.save(output_dir/name)
│       ├─> md_to_docx(auto/output/answer.docx, answer.md)
│       │   ├─> python-docx.Document()
│       │   ├─> Parse markdown line by line:
│       │   │   ├─> # → doc.add_heading(level=1)
│       │   │   ├─> **text** → run.bold = True
│       │   │   └─> - → doc.add_paragraph(style='List Bullet')
│       │   └─> doc.save(docx_path)
│       └─> Return {status: 'success', answer_path, docx_path}
└─> [Signal] auto_detail_signal.preview_refresh.emit()
    └─> _refresh_auto_detail_preview()
        └─> Load & render markdown with CSS

User Action: Submit
├─> on_hw_submit_clicked()  # qt.py:921
│   └─> [Thread] func/getHomework.py:submit_to_canvas(url)
│       ├─> Parse URL → course_id + assignment_id
│       ├─> Load cookies.json → requests.Session (with CSRF)
│       ├─> Scan auto/output/ → Find all files (.docx, .pdf, .png)
│       ├─> [4-step upload] For each file:
│       │   ├─> [1/4] POST /files/pending
│       │   │   └─> Return {upload_url, upload_params}
│       │   ├─> [2/4] POST {upload_url}?token={token}
│       │   │   └─> Upload to Canvas/S3
│       │   ├─> [3/4] GET {Location header}
│       │   │   └─> Return {id: file_id}
│       │   └─> Collect file_ids
│       └─> [4/4] POST /courses/{cid}/assignments/{aid}/submissions
│           └─> Data: {submission[attachment_ids]: "123,456"}
└─> Status: "Submitted successfully"
```

### 📝 Quiz Automation Flow

```
User Action: Double-click Quiz TODO → AutoDetail → Preview
├─> on_quiz_again_clicked()  # qt.py:879
│   └─> [Thread] func/getQuiz_ultra.py:run_gui(url, product, model, prompt, assignment_folder, thinking)
│       ├─> Clear auto/output/
│       ├─> Load cookies.json → requests.Session
│       ├─> GET {url}/take  # Auto-start quiz
│       ├─> parse_questions(html, base_url, auto/output/)
│       │   ├─> lxml.html.fromstring(html)
│       │   ├─> XPath: //*[@id="questions"]/div[contains(@class, "question")]
│       │   ├─> For each question div:
│       │   │   ├─> Extract question_id (e.g., "question_97585716")
│       │   │   ├─> Extract question_text
│       │   │   ├─> Extract question images → auto/output/images/q_{qid}_{i}.png
│       │   │   ├─> XPath: .//input[@type="radio"] → Extract answers
│       │   │   └─> For each answer:
│       │   │       ├─> Extract answer_id (e.g., "7574")
│       │   │       ├─> Extract answer_text
│       │   │       └─> Extract answer images → auto/output/images/a_{aid}_{i}.png
│       │   ├─> [Concurrent download] ThreadPoolExecutor(max_workers=20)
│       │   │   └─> Download all images
│       │   └─> Return questions:
│       │       [
│       │         {
│       │           "id": "question_97585716",
│       │           "txt": "What is photosynthesis?",
│       │           "imgs": ["/path/to/q_xxx_0.png"],
│       │           "ans": [
│       │             {"id": "7574", "txt": "A process...", "imgs": null},
│       │             {"id": "7575", "txt": "", "imgs": ["/path/to/a_7575_0.png"]}
│       │           ]
│       │         }
│       │       ]
│       ├─> save_preview(questions, html, auto/output/)
│       │   ├─> questions.html (raw HTML)
│       │   └─> questions.md (formatted preview)
│       ├─> get_answers(questions, product, model, prompt, thinking)
│       │   ├─> [Collect all images] questions + answers
│       │   ├─> upPromptFiles.upload_files(files, product)
│       │   │   ├─> [Gemini] genai.upload_file(img) → uri
│       │   │   └─> [Claude] base64 encode images
│       │   ├─> Build question dict:
│       │   │   {
│       │   │     "question_97585716": {
│       │   │       "question": "What is photosynthesis?",
│       │   │       "question_images": ["Image 1"],  # or Gemini URI
│       │   │       "options": {
│       │   │         "7574": "A process...",
│       │   │         "7575": "No answer text. [See: Image 2]"
│       │   │       }
│       │   │     }
│       │   │   }
│       │   ├─> Build full prompt (user prompt + image mapping + questions JSON)
│       │   ├─> upPromptFiles.call_ai(full_prompt, product, model, uploaded_info, thinking)
│       │   │   └─> [Claude thinking mode]
│       │   │       └─> params["thinking"] = {"type": "enabled", "budget_tokens": 8000}
│       │   ├─> [Parse response] Extract JSON
│       │   │   ├─> Remove ```json ... ```
│       │   │   └─> json.loads()
│       │   └─> Return {"question_97585716": "7574", ...}
│       ├─> save_answers(questions, answers, auto/output/)
│       │   └─> QesWA.md (with ✅ marks)
│       └─> Return {questions, answers, output_dir, session, doc, url}
├─> Save result to self._last_quiz_result
└─> [Signal] auto_detail_signal.preview_refresh.emit()
    └─> Load & render QesWA.md with embedded base64 images

User Action: Submit
├─> on_quiz_submit_clicked()  # qt.py:944
│   └─> [Thread] func/getQuiz_ultra.py:submit(session, url, doc, questions, answers, skip_confirm=True)
│       ├─> Stats: Total {N} | Answered {M} | Unanswered {K}
│       ├─> XPath extract form: //form[@id="submit_quiz_form"]
│       ├─> Build POST data:
│       │   ├─> Copy all hidden fields (authenticity_token, ...)
│       │   └─> Merge answers dict {"question_97585716": "7574"}
│       └─> POST {quiz_url}/submissions
└─> Status: "Submitted successfully"
```

---

## Core Modules Deep Dive

### gui/qt.py - Main Application Class

**CanvasApp** (1190 lines) - Central GUI controller

```python
class CanvasApp(QMainWindow):
    def __init__(self):
        # Managers
        self.dm = DataManager()              # JSON data loading
        self.done_mgr = DoneManager()        # Checkbox state (Done.txt)
        self.course_detail_mgr = None        # Lazy init on open
        self.auto_detail_mgr = None          # Lazy init on open

        # Signals (thread-safe communication)
        self.status_signal = StatusUpdateSignal()         # Status refresh
        self.tab_content_signal = TabContentSignal()      # Tab rendering
        self.auto_detail_signal = AutoDetailSignal()      # AutoDetail updates

        # Initialize
        self.init_qt()                    # Load 6 UI files
        self.init_button_bindings()       # Connect signals/slots
        self.init_data_viewer()           # Load data + show launcher
        self.check_status()               # Initial status check + auto-fix

        # Event filters (keyboard navigation)
        self.installEventFilter(self)
        self._install_list_event_filters()
```

**Key Methods**:

1. **init_qt()** (qt.py:42-70)
   - Loads 6 .ui files with loadUi()
   - Creates IOSToggle widgets (8 instances)
   - Sets up status indicator widgets
   - Initializes launcher overlay

2. **init_button_bindings()** (qt.py:222-288)
   - Connects all buttons to handlers
   - Hooks up IOSToggle state changes
   - Binds keyboard shortcuts

3. **check_status()** (qt.py:289-305)
   - Runs checkStatus.get_all_status()
   - Auto-fixes expired cookies
   - Auto-fetches missing data

4. **eventFilter()** (qt.py:992-1089)
   - WASD navigation
   - C/T/F quick jumps
   - Space/Shift+Space actions
   - Shift+A/C shortcuts

### gui/qt_interact.py - Button Handlers

**Pattern**: All long-running operations use threading

```python
def _run_in_thread(func, console, name, on_success=None):
    """Execute function in daemon thread with console output"""
    console.append(f"[INFO] {name} started")

    def wrapper():
        try:
            console.append(f"[INFO] Starting {name}...")
            func(console)
            console.append(f"[SUCCESS] {name} completed")
            if on_success:
                on_success()  # Refresh UI
        except Exception as e:
            import traceback
            console.append(f"[ERROR] {name} failed: {e}")
            console.append(traceback.format_exc())

    threading.Thread(target=wrapper, daemon=True).start()
```

**Key Handlers**:
- `on_get_cookie_clicked()` → login/getCookie.py
- `on_get_todo_clicked()` → func/getTodos.py
- `on_get_course_clicked()` → func/getCourses.py
- `on_clean_clicked()` → clean.py

### gui/data_manager.py - Data Management

```python
class DataManager:
    def load_all(self):
        self._load_courses()  # course.json → self.data['courses']
        self._load_todos()    # todos.json → self.data['todos']
        self._load_files()    # Scan TODO_DIR → self.data['files']

    def classify_todo(self, todo):
        """Classify TODO and return metadata"""
        # Extract type, URL
        ad = todo.get('assignment_details', {})
        url = todo.get('redirect_url', '').lower()
        types = ad.get('type', [])

        # Determine flags
        is_quiz = 'quiz' in url
        is_discussion = 'discussion' in url
        is_automatable = any(t in types for t in [
            'online_quiz', 'online_upload', 'online_text_entry', 'discussion_topic'
        ])
        is_homework = not (is_quiz or is_discussion)

        # Determine open status
        is_open = not ad.get('submitted', False)
        if ad.get('locked_for_user', False):
            is_open = False

        # For quizzes, check attempts
        if is_quiz and 'quiz_metadata' in ad:
            qm = ad['quiz_metadata']
            if qm.get('locked_for_user', False):
                is_open = False
            elif qm.get('attempts_left', 1) <= 0:
                is_open = False

        return {
            'is_quiz': is_quiz,
            'is_discussion': is_discussion,
            'is_automatable': is_automatable,
            'is_homework': is_homework,
            'is_open': is_open,
            'dots': {
                'homework': is_homework,
                'quiz': is_quiz,
                'discussion': is_discussion,
                'automatable': is_automatable
            }
        }
```

### gui/delegates.py - Custom Rendering

**TodoItemDelegate** - Urgency-based gradient background

```python
class TodoItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # STEP 1: Calculate urgency color
        todo = index.data(Qt.ItemDataRole.UserRole + 1)
        urgency_color = None

        if todo and isinstance(todo, dict):
            due_date = todo.get('due_date')
            if due_date:
                try:
                    dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    now = datetime.now(dt.tzinfo)
                    hours_left = (dt - now).total_seconds() / 3600

                    if self.history_mode and hours_left <= 0:
                        # History mode: past-due = blue with alpha
                        alpha = 255 if is_selected else 120
                        urgency_color = QColor(59, 130, 246, alpha)
                    elif not self.history_mode:
                        # Normal mode: urgency gradient
                        if hours_left <= 0:
                            r, g, base_alpha = 100, 0, 150  # OVERDUE
                        else:
                            t = min(hours_left / 168, 1.0)  # 168h = 7 days
                            urgency = math.exp(-3 * t)      # Exponential decay
                            r = int(urgency ** 0.7 * 100)
                            g = int((1 - urgency ** 1.5) * 100)
                            base_alpha = int(60 + urgency * 90)

                        alpha = 255 if is_selected else base_alpha
                        urgency_color = QColor(r, g, 0, alpha)
                except:
                    pass

        # STEP 2: Paint urgency background (bottom layer)
        if urgency_color:
            painter.fillRect(option.rect, urgency_color)

        # STEP 3: Paint default content (text, checkbox) with disabled selection
        opt_copy = option.__class__(option)
        if is_selected:
            opt_copy.state &= ~QStyle.StateFlag.State_Selected
        opt_copy.state &= ~QStyle.StateFlag.State_MouseOver
        super().paint(painter, opt_copy, index)

        # STEP 4: Paint custom overlays (dots, labels, date) at front
        # [Implementation continues...]
```

**Visual hierarchy** (right to left):
1. Colored dots (🔴🔵🟣🟡)
2. Type labels (HW/QZ/DS)
3. Due date (mm/dd format)

### func/upPromptFiles.py - Unified AI Interface

```python
def call_ai(prompt, product, model, files=[], uploaded_info=None, thinking=False):
    """Unified AI calling interface

    Args:
        prompt: User prompt text
        product: 'Gemini' or 'Claude'
        model: Model name
        files: File paths (if uploaded_info is None)
        uploaded_info: Pre-uploaded file info (from upload_files())
        thinking: Enable thinking mode (Claude only)

    Returns:
        str: AI-generated text
    """
    if product == 'Gemini':
        return _gemini(prompt, model, uploaded_info=uploaded_info)
    elif product == 'Claude':
        return _claude(prompt, model, uploaded_info=uploaded_info, thinking=thinking)
    raise ValueError(f"Unknown product: {product}")

def _gemini(prompt, model, uploaded_info=None):
    """Gemini API call"""
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    m = genai.GenerativeModel(model)

    if not uploaded_info:
        return m.generate_content([prompt]).text

    # Use pre-uploaded file objects
    uploaded_objs = [info['uploaded_obj'] for info in uploaded_info]
    return m.generate_content([prompt] + uploaded_objs).text

def _claude(prompt, model, uploaded_info=None, thinking=False):
    """Claude API call"""
    import anthropic

    # Force official API (ignore Claude Code proxy)
    client = anthropic.Anthropic(
        api_key=config.CLAUDE_API_KEY,
        base_url="https://api.anthropic.com"
    )

    # Build content
    content = [{"type": "text", "text": prompt}]

    if uploaded_info:
        for info in uploaded_info:
            if info['type'] == 'image':
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": info['mime'],
                        "data": info['data']
                    }
                })
            elif info['type'] == 'document':
                content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": info['mime'],
                        "data": info['data']
                    }
                })

    # Build API parameters
    params = {
        "model": model,
        "max_tokens": 16384,
        "messages": [{"role": "user", "content": content}]
    }

    # Enable thinking mode if requested
    if thinking:
        params["thinking"] = {"type": "enabled", "budget_tokens": 8000}

    msg = client.messages.create(**params)

    # Extract text from response
    for block in msg.content:
        if hasattr(block, 'text'):
            return block.text
    return ""
```

---

## Data Flow Architecture

### JSON Data Files

**account_config.json** (User-created, Git-ignored)
```json
{
  "account": "user@psu.edu",
  "password": "password",
  "otp_key": "BASE32_TOTP_SECRET",
  "gemini_api_key": "AIza...",
  "claude_api_key": "sk-ant-...",
  "preference": {
    "base_url": "https://psu.instructure.com"
  }
}
```

**cookies.json** (Auto-generated, 24h validity)
```json
[
  {
    "name": "_csrf_token",
    "value": "abc123...",
    "domain": ".instructure.com",
    "path": "/",
    "httpOnly": true,
    "secure": true
  },
  {
    "name": "canvas_session",
    "value": "xyz789...",
    ...
  }
]
```

**course.json** (Auto-generated)
```json
{
  "base_url": "https://psu.instructure.com",
  "courses": [
    {
      "id": 2418560,
      "name": "BISC 4, Section 001: Human Body",
      "tabs": {
        "Home": "/courses/2418560",
        "Modules": "/courses/2418560/modules",
        "Grades": "/courses/2418560/grades",
        "Syllabus": "/courses/2418560/assignments/syllabus",
        "Announcements": "/courses/2418560/announcements",
        "Discussions": "/courses/2418560/discussion_topics",
        "Files": "/courses/2418560/files",
        "Assignments": "/courses/2418560/assignments",
        "Quizzes": "/courses/2418560/quizzes"
      }
    }
  ]
}
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
      "name": "Week 5 Quiz",
      "desc": "HTML description...",
      "type": ["online_quiz"],
      "is_quiz": true,
      "quiz_id": "5363417",
      "submitted": false,
      "locked_for_user": false,
      "files": null,
      "folder": "Week_5_Quiz_20251020_235900",
      "assignment_folder": "/full/path/to/todo/Week_5_Quiz_20251020_235900",
      "quiz_metadata": {
        "locked_for_user": false,
        "unlock_at": null,
        "lock_at": "2025-10-20T23:59:00Z",
        "quiz_type": "assignment",
        "published": true,
        "allowed_attempts": 2,
        "time_limit": 60,
        "question_count": 15,
        "attempt": 0,
        "attempts_left": 2
      }
    }
  },
  {
    "course_name": "BISC 4",
    "name": "Weekly Reflection",
    "due_date": "2025-10-22T23:59:00Z",
    "points_possible": 20,
    "redirect_url": "https://psu.instructure.com/courses/2418560/assignments/17474475",
    "assignment_details": {
      "name": "Weekly Reflection",
      "desc": "Write a reflection...",
      "type": ["online_upload"],
      "is_quiz": false,
      "submitted": false,
      "locked_for_user": false,
      "files": [
        {
          "file_id": "123456",
          "download_url": "https://...",
          "filename": "guidelines.pdf",
          "local_path": "/full/path/to/todo/Weekly_Reflection_20251022_235900/files/guidelines.pdf"
        }
      ],
      "folder": "Weekly_Reflection_20251022_235900",
      "assignment_folder": "/full/path/to/todo/Weekly_Reflection_20251022_235900"
    }
  }
]
```

**Done.txt** (Checkbox state persistence)
```
https://psu.instructure.com/courses/2418560/assignments/17474475
https://psu.instructure.com/courses/2418560/quizzes/5363417
```

### File System Structure

```
/Users/zeroripper/wow/canvas_decon/
├── Courses/                                      # Course materials (Git-ignored)
│   └── bisc_4_2418560/                           # {first_two_words}_{course_id}
│       ├── Syll/                                 # Syllabus files
│       │   ├── syllabus_v1.pdf
│       │   └── syllabus_v2.pdf
│       ├── Files/
│       │   └── Textbook/                         # Manually placed textbooks
│       │       ├── chapter1.pdf
│       │       └── chapter2.pdf
│       └── Tabs/                                 # Auto-cached tab content
│           ├── Home.md
│           ├── Modules.md
│           ├── Grades.md
│           └── Announcements.md
│
└── todo/                                         # TODO workspace (Git-ignored)
    ├── Weekly_Reflection_20251022_235900/        # {sanitized_name}_{timestamp}
    │   ├── files/                                # Downloaded reference files
    │   │   ├── guidelines.pdf
    │   │   └── rubric.pdf
    │   └── auto/
    │       ├── input/                            # User-placed input files
    │       │   └── extra_reference.pdf
    │       └── output/                           # Auto-generated outputs
    │           ├── answer.md
    │           ├── answer.docx
    │           └── image1.png
    │
    └── Week_5_Quiz_20251020_235900/
        ├── files/
        └── auto/
            ├── input/
            └── output/
                ├── questions.html
                ├── questions.md
                ├── QesWA.md
                └── images/
                    ├── q_question_97585716_0.png
                    ├── a_7574_0.png
                    └── a_7575_0.png
```

---

## Technical Patterns

### 1. Threading Pattern

**Rule**: All long-running operations MUST run in background threads

```python
# ✅ CORRECT
def on_button_clicked(console_tab_widget):
    def run(console):
        # Long-running operation
        result = some_api_call()
        console.append(f"Result: {result}")

    console = _create_console_tab(console_tab_widget, "Task Name")
    _run_in_thread(run, console, "Task Name", on_success=lambda: refresh_ui())

# ❌ INCORRECT (blocks UI)
def on_button_clicked():
    result = some_api_call()  # Freezes GUI
    show_result(result)
```

### 2. Event Filter Pattern (Keyboard Navigation)

```python
def eventFilter(self, obj, event):
    """Intercept keyboard events before Qt's default handling"""
    if event.type() == QEvent.Type.KeyPress:
        key = event.key()
        modifiers = event.modifiers()

        # Handle WASD navigation
        if key in [Qt.Key.Key_W, Qt.Key.Key_A, Qt.Key.Key_S, Qt.Key.Key_D]:
            if isinstance(obj, QListWidget):
                self._handle_wasd_navigation(key, current_widget)
                return True  # Block propagation

        # Handle shortcuts (check Shift first!)
        if key == Qt.Key.Key_A and (modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.on_automation_top_clicked()
            return True
        elif key == Qt.Key.Key_C and (modifiers & Qt.KeyboardModifier.ShiftModifier):
            self._show_clean_dialog()
            return True
        elif key == Qt.Key.Key_C and not (modifiers & Qt.KeyboardModifier.ShiftModifier):
            # Jump to Courses category
            return True

    return super().eventFilter(obj, event)  # Pass to default handler
```

### 3. Delegate Pattern (Custom Rendering)

**Critical Rule**: NEVER use `setItemDelegate(None)` in PyQt6

```python
# ✅ CORRECT
if category in ['Syllabus', 'Textbook']:
    cdw.itemList.setItemDelegate(FileItemDelegate(cdw.itemList))
else:
    cdw.itemList.setItemDelegate(QStyledItemDelegate())  # Use default, not None!

cdw.itemList.viewport().update()  # Force repaint

# ❌ INCORRECT (causes rendering bugs in PyQt6)
cdw.itemList.setItemDelegate(None)  # Viewport won't refresh!
```

### 4. Signal/Slot Pattern (Thread-safe UI Updates)

```python
# Define signals
class AutoDetailSignal(QObject):
    status_update = pyqtSignal(str)
    preview_refresh = pyqtSignal()

# Connect signals in __init__
self.auto_detail_signal.status_update.connect(self._update_auto_detail_status)
self.auto_detail_signal.preview_refresh.connect(self._refresh_auto_detail_preview)

# Emit from background thread (thread-safe!)
def worker_thread():
    # ... long operation ...
    self.auto_detail_signal.status_update.emit("Status: Complete")
    self.auto_detail_signal.preview_refresh.emit()
```

### 5. Canvas API Patterns

**URL Parsing**
```python
from urllib.parse import urlparse

path = urlparse(url).path.split('/')
course_id = path[path.index('courses') + 1]

if 'quizzes' in path:
    quiz_id = path[path.index('quizzes') + 1]
    api_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/quizzes/{quiz_id}"
elif 'assignments' in path:
    assignment_id = path[path.index('assignments') + 1]
    api_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments/{assignment_id}"
```

**Session Management**
```python
# Load cookies
cookies = {c['name']: c['value'] for c in json.load(open(config.COOKIES_FILE))}
session = requests.Session()
session.cookies.update(cookies)
session.headers.update({
    'Accept': 'application/json+canvas-string-ids',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})
```

**CSRF Handling**
```python
from urllib.parse import unquote

# Extract CSRF token from cookies
csrf_token = next((unquote(c.value) for c in session.cookies if c.name == '_csrf_token'), '')

# Include in POST requests
payload = {
    'authenticity_token': csrf_token,
    '_method': 'post',
    ...
}
```

**File Upload (4-step process)**
```python
# 1. Request upload token
r = session.post('https://psu.instructure.com/files/pending', data={
    'attachment[filename]': filename,
    'attachment[size]': str(file_size),
    'attachment[content_type]': mime_type,
    'attachment[context_code]': f'course_{course_id}'
})
upload_info = r.json()

# 2. Upload to S3
r = session.post(
    upload_info['upload_url'],
    files={'file': (filename, open(file_path, 'rb'), mime_type)},
    allow_redirects=False
)

# 3. Confirm upload
r = session.get(r.headers['location'])
file_id = str(r.json()['id'])

# 4. Submit with file IDs
session.post(
    f"{config.CANVAS_BASE_URL}/courses/{course_id}/assignments/{assignment_id}/submissions",
    data={'submission[attachment_ids]': ','.join(file_ids)}
)
```

### 6. XPath Patterns (Quiz Parsing)

```python
from lxml import html

doc = html.fromstring(response.content)

# Extract questions container
questions_container = doc.xpath('//*[@id="questions"]')[0]

# Extract all question divs
question_divs = doc.xpath('//*[@id="questions"]/div[contains(@class, "question")]')

for qdiv in question_divs:
    # Extract question ID
    qcontainer = qdiv.xpath('.//div[starts-with(@id, "question_")]')[0]
    question_id = qcontainer.get('id')

    # Extract question text
    qtext_elem = qcontainer.xpath('.//div[contains(@class, "question_text")]')[0]
    question_text = qtext_elem.text_content().strip()

    # Extract images in question
    qimages = qcontainer.xpath('.//div[contains(@class, "question_text")]//img')

    # Extract answer options
    answer_elements = qcontainer.xpath('.//input[@type="radio"]')
    for ainput in answer_elements:
        answer_id = ainput.get('value')
        label = qcontainer.xpath(f'.//label[@for="{ainput.get("id")}"]')
        answer_text = label[0].text_content().strip() if label else ''
```

### 7. Redirect Handling

```python
import re

# Server-side redirects (automatic via requests)
response = session.get(url)
if response.history:
    for resp in response.history:
        print(f"Redirect: {resp.status_code} {resp.url}")

# Client-side JavaScript redirects
js_redirect = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", response.text)
if js_redirect:
    redirect_url = js_redirect.group(1)
    if redirect_url.startswith('/'):
        redirect_url = f"https://psu.instructure.com{redirect_url}"
    response = session.get(redirect_url)
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
   - Use `os.path.join()` for cross-platform compatibility

3. **Module Imports**
   ```python
   # Standard pattern for all modules
   sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
   import config
   ```

### Thread Safety Rules

1. **UI Updates from Threads**
   - ✅ Use Qt signals: `self.signal.emit(data)`
   - ❌ Direct widget access: `self.label.setText(text)`

2. **Long Operations**
   - ✅ Background thread + console output
   - ❌ Direct execution in button handler

3. **Console Output**
   ```python
   def my_function(console=None):
       if console:
           console.append("[INFO] Starting...")
       # ... operation ...
       if console:
           console.append("[SUCCESS] Done")
   ```

### GUI Development Rules

1. **Event Filters**
   - Install on QListWidget instances
   - Return `True` to block propagation
   - Check Shift modifiers BEFORE single keys

2. **Delegates**
   - NEVER use `setItemDelegate(None)`
   - Always call `viewport().update()` after changing delegate
   - Use `QStyledItemDelegate()` as default

3. **Signals/Slots**
   - Define signals in separate QObject classes
   - Connect in `__init__`
   - Disconnect in cleanup (if needed)

### Testing Guidelines

1. **Dual-mode Testing**
   - Test standalone CLI: `python func/module.py`
   - Test GUI integration: Click button + check console output

2. **Error Handling**
   - Wrap all thread functions in try/except
   - Log full traceback to console
   - Show user-friendly QMessageBox

3. **Debugging Tools**
   - Console tabs for live output
   - Debug button (separate process)
   - Selenium screenshots (error_screenshot.png)

### Common Pitfalls

1. **❌ Using `input()` in GUI-callable functions**
   ```python
   # BAD
   def my_function():
       answer = input("Continue? ")  # Freezes GUI

   # GOOD
   def my_function():
       # Use QMessageBox.question() instead
       pass
   ```

2. **❌ Forgetting `console` parameter**
   ```python
   # BAD (can't run from GUI)
   def my_function():
       print("Starting...")  # Goes to terminal, not GUI

   # GOOD
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

4. **❌ Blocking operations on main thread**
   ```python
   # BAD
   def on_button_clicked():
       time.sleep(5)  # Freezes GUI

   # GOOD
   def on_button_clicked():
       def worker():
           time.sleep(5)
       threading.Thread(target=worker, daemon=True).start()
   ```

### Adding New Features

**Step-by-step process**:

1. **Design Phase**
   - Identify if it's a short or long operation
   - Decide: GUI-only, CLI-only, or dual-mode
   - Check if similar patterns exist in `misc/`

2. **Implementation Phase**
   - Long operation → Create module in `func/`
   - GUI integration → Add button + binding + handler
   - Threading → Use `_run_in_thread()` pattern
   - Console output → Add progress messages

3. **UI Integration**
   - Edit `.ui` file in Qt Designer (if needed)
   - Add button binding in `init_button_bindings()`
   - Create handler in `gui/qt_interact.py` or `gui/qt.py`

4. **Testing Phase**
   - Test CLI mode: `python func/new_module.py`
   - Test GUI mode: Click button + verify console output
   - Test error handling: Force failure + check traceback

5. **Documentation Phase**
   - Update CLAUDE.md with new patterns
   - Add usage examples
   - Document any gotchas

---

## Important Reminders

### Security

1. **API Keys**: NEVER commit `account_config.json` to Git
2. **Cookies**: Auto-expire after 24 hours
3. **TOTP Secret**: Treat like a password

### Academic Integrity

This tool is for learning and research ONLY. Users must:
- Understand generated content
- Follow school AI policies
- Respect Honor Code
- Take responsibility for submissions

### Technical Limitations

1. **Cookie Expiry**: 24h limit, requires re-login
2. **API Quotas**: Gemini/Claude have daily limits
3. **Quiz Support**: Multiple choice only (no fill-in-blank)
4. **Image Recognition**: Depends on AI vision capabilities

---

## Quick Reference

### File Locations

```
main.py                    # Entry point
config.py                  # All paths + API keys + prompts
checkStatus.py             # Status validators
clean.py                   # Garbage collection

gui/qt.py                  # Main app class (1190 lines)
gui/qt_interact.py         # Button handlers + threading
gui/data_manager.py        # JSON data loading
gui/done_manager.py        # Checkbox persistence
gui/course_detail_manager.py  # Course detail logic
gui/auto_detail_manager.py    # AutoDetail logic
gui/delegates.py           # Custom renderers
gui/formatters.py          # HTML formatters
gui/ios_toggle.py          # Toggle widget
gui/model_config.py        # AI model selection

func/getTodos.py           # Fetch TODOs + download files
func/getCourses.py         # Fetch courses + tabs
func/getHomework.py        # Homework automation
func/getQuiz_ultra.py      # Quiz automation
func/upPromptFiles.py      # Unified AI interface
func/getSyll.py            # Batch download syllabi

login/getCookie.py         # Selenium auto-login
login/getTotp.py           # TOTP generation
```

### Key Constants (config.py)

```python
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

COOKIES_FILE = os.path.join(ROOT_DIR, 'cookies.json')
ACCOUNT_CONFIG_FILE = os.path.join(ROOT_DIR, 'account_config.json')
PERSONAL_INFO_FILE = os.path.join(ROOT_DIR, 'personal_info.json')
COURSE_FILE = os.path.join(ROOT_DIR, 'course.json')
DONE_FILE = os.path.join(ROOT_DIR, 'Done.txt')

TODO_DIR = os.path.join(ROOT_DIR, 'todo')
COURSES_DIR = os.path.join(ROOT_DIR, 'Courses')
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output')

GEMINI_API_KEY = "..."  # From account_config.json
CLAUDE_API_KEY = "..."  # From account_config.json
CANVAS_BASE_URL = "https://psu.instructure.com"

DEFAULT_PROMPTS = {
    'homework': "...",
    'quiz': "..."
}
```

### Common Operations

```bash
# Start GUI
python main.py

# CLI mode
python func/getTodos.py
python func/getHomework.py --url "..." --product Gemini --model gemini-2.5-pro
python func/getQuiz_ultra.py --url "..." --product Claude --model claude-sonnet-4-5

# Status check
python checkStatus.py

# Clean
python clean.py
```

---

**Remember**: When in doubt, follow existing patterns in the codebase. Check `misc/` for legacy implementations before creating new code.
