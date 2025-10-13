# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Canvas LMS automation for Penn State University with **PyQt6 GUI**. Automates login (Selenium + 2FA), assignments (Gemini AI + DOCX generation), and quizzes (vision API + auto-submit).

**Features**: Real-time status monitoring, automatic cookie refresh, TODO/course management, visual filtering system, and integrated automation workflows.

**Security**: Hardcoded `GEMINI_API_KEY` in [config.py](config.py) - handle with care.

## Project Structure

**Four-tier organization**:
- **gui/** - PyQt6 GUI (10 modules: qt.py, qt_interact.py, styles.py, delegates.py, data_manager.py, done_manager.py, course_detail_manager.py, formatters.py, ios_toggle.py, ui/)
- **func/** - Production modules (getTodos, getCourses, getHomework, getQuiz_ultra, getSyll)
- **login/** - Auth (getCookie: Selenium+2FA, getTotp: TOTP generation)
- **misc/** - Deprecated code (old quiz workflows, legacy login implementations)
- **Courses/** - Unified course file system (`CourseName_CourseID/Syll|Files/Textbook|Tabs/`)
- **main.py** - GUI entry point (initializes PyQt6 application)
- **checkStatus.py** - Status validation (account, cookie, todos, network, courses)
- **config.py** - Global paths, API keys, URLs, `COURSES_DIR`
- **clean.py** + **clean_whitelist.txt** - Whitelist-based garbage collection (auto-keeps `.py`, protected dirs)

## Key Commands

```bash
# Setup
pip install -r requirements.txt

# GUI Mode (recommended - all features in one interface)
python main.py

# CLI Mode (standalone scripts)
python func/getTodos.py        # Fetch todos + download files → todo_files/
python func/getCourses.py      # Get course list
python func/getHomework.py     # Edit TARGET_ASSIGNMENT_URL first
python func/getQuiz_ultra.py   # Edit BASE_QUIZ_URL first

# Status Check (used by GUI, can run standalone)
python checkStatus.py          # Check all statuses (account, cookie, network, etc.)

# Maintenance
python clean.py                # Remove non-whitelisted files
```

## Architecture

### GUI System (PyQt6)
**Entry point**: `main.py:25` → initializes QApplication + loads dark theme + shows window

**Four-window architecture**:
1. **Main Window** (`gui/ui/main.ui`) - Dashboard with courses/TODOs/files viewer
2. **Login Window** (`gui/ui/login.ui`) - Account credential input (saves to `account_info.json`)
3. **Automation Window** (`gui/ui/automation.ui`) - Categorized TODO management (4 tabs)
4. **CourseDetail Window** (`gui/ui/course_detail.ui`) - Course-specific content viewer

**Core modules** (~1100 lines total, compressed from ~1259 lines):
- **gui/qt.py** (377 lines) - Main app logic (`CanvasApp` class), window management
- **gui/qt_interact.py** - Button handlers + threading (`_run_in_thread`)
- **gui/styles.py** - Dark Next.js-inspired theme (background: `#0a0a0a`, accent: `#3b82f6`)
- **gui/delegates.py** - Custom item renderers:
  - `TodoItemDelegate` - Colored dots (🔴 Auto, 🔵 Discussion, 🟣 Quiz, 🟡 Homework) + type labels
  - `FileItemDelegate` - 🟢 Green dot indicator for downloaded files
- **gui/data_manager.py** - JSON data loading (`load_all()`)
- **gui/done_manager.py** - Checkbox state persistence (`Done.txt`)
- **gui/course_detail_manager.py** - Course folder structure + data filtering
- **gui/formatters.py** - HTML formatters for detail views
- **gui/ios_toggle.py** - iOS-style toggle switch widget (150ms animation, synchronized across windows)

**Key features**:
- **Auto-refresh**: Cookies expire after 24h → automatic `getCookie` execution
- **Auto-fetch**: If cookie valid but data missing → auto-runs `getCourses` + `getTodos`
- **Real-time data viewer**: 3-column layout (categories → items → details) with dynamic HTML formatting
- **Visual filtering**: Checkboxes for homework/quiz/discussion/automatable (OR logic)
- **Folder integration**: "Open Folder" button → opens `todo_files/{assignment_folder}` in file explorer
- **Automation workflow**: Click automatable TODO → auto-navigate to automation page with pre-selection
- **Keyboard navigation**: WASD (move), C/T/F (jump tabs), Space (open detail), Shift+A/C (shortcuts)
- **Course detail**: Double-click syllabus/textbook (open folder), tabs (fetch & convert to markdown)

### Status Monitoring (checkStatus.py)
**Returns**: 0 (red - fail/missing), 1 (green - valid), 2 (yellow - expired/invalid)

**Five validators** (checkStatus.py:20-99):
1. `check_account_info()` - Validates `account_info.json` structure (requires: account, password, otp_key)
2. `check_cookie_validity()` - File age (<24h) + format + Canvas API test (`/api/v1/users/self`)
3. `check_todo_list()` - Validates `todos.json` exists and non-empty
4. `check_network()` - Pings Canvas API (accepts 200/401/403 as valid network responses)
5. `check_course_list()` - Validates `course.json` exists and non-empty

**Usage in GUI**:
```python
status = checkStatus.get_all_status()  # Returns dict with all 5 statuses
colors = {0: '#ef4444', 1: '#22c55e', 2: '#eab308'}  # Red, Green, Yellow
widget.setStyleSheet(f"background-color: {colors[status['cookie']]}")
```

### Path Management
All modules run from **project root**. Standard import pattern:
```python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
```

### Authentication Flow
**CLI mode**: Direct script execution → reads `account_info.json` → calls `login/getCookie.py`
**GUI mode**: Click "Get Cookie" button (gui/qt_interact.py:61-74) → threaded execution

**Process**:
1. Read `account_info.json` (credentials + TOTP secret)
2. `getCookie.py` → Selenium (Microsoft SSO) → 2FA via `getTotp.py` (TOTP, 3 retries)
3. Save `cookies.json` → used by all subsequent API calls
4. GUI auto-calls `update_status()` on success → refreshes status indicators

Human behavior mimicking:
```python
def human_type(element, text):  # 50-150ms/char
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))

def human_click(driver, element):  # Random pause before click
    ActionChains(driver).move_to_element(element).pause(random.uniform(0.1, 0.3)).click().perform()
```

### TODO Management (`getTodos.py`)
1. Fetch `/api/v1/users/self/todo`
2. Extract file IDs from descriptions: `/courses/(\d+)/files/(\d+)`
3. Download files → `todo_files/` (auto-rename duplicates: `_r{N}`)
4. Output `todos.json`:
```json
{"course_name": "BISC 002", "assignment_details": {"is_quiz": false, "submitted": false,
 "files": [{"file_id": "123", "filename": "lecture.pdf", "local_path": "..."}]}}
```

### Quiz Automation (`getQuiz_ultra.py`)
**Current production** (replaces old 2-stage workflow). 168 lines vs old 525 lines.

**Features**: Vision API for images, concurrent download (20 workers), smart naming `q_{qid}_{i}.png` / `a_{aid}_{i}.png`

**Flow**:
1. Direct `/take` page access → parse with lxml XPath
2. Concurrent image download (questions + answer options)
3. Upload images to Gemini → `genai.upload_file()`
4. Combined prompt + images → `gemini-2.5-pro` → answers
5. Save preview (`questions.html`, `questions.md`, `QesWA.md`)
6. User confirm → submit

### Assignment Automation (`getHomework.py`)
1. Fetch assignment via API (`/api/v1/courses/{cid}/assignments/{aid}`)
2. Upload PDFs from `bisc_pdfs/` → Gemini
3. Load `personal_info.json` (name, age, weight, height, gender, location)
4. `gemini-2.5-pro` generates markdown (strict rules: no bullets, letter numbering, `**1)**` format, optional `[gen_img]` tags)
5. Parse `[gen_img]` → generate with `gemini-2.5-flash-image`
6. Convert markdown → DOCX (python-docx)
7. Multi-step upload: token request (`/files/pending`) → S3 upload → confirm → submit with file IDs

### Unified Course File System
**Structure** (`/Courses/`):
```
bisc_4_2418560/          # Format: first_two_words_courseID
  ├── Syll/              # Syllabus files (from getSyll.py)
  ├── Files/
  │   └── Textbook/      # Textbook PDFs
  └── Tabs/              # Downloaded tab content (markdown, auto-cached on single-click)
```

**Naming logic**: Extract first 2 words from course name + course ID, lowercase with underscores.

**Implementation**: `config.py:COURSES_DIR`, `course_detail_manager.py:26-31`, `func/getSyll.py:19-28`

### Data Files (Git-Ignored)
- `account_info.json` - Credentials + TOTP secret
- `personal_info.json` - Student context for personalized answers
- `cookies.json` - Session cookies (auto-generated)
- `course.json`, `todos.json` - Cached data
- `Done.txt` - Checked item URLs (checkbox state persistence)

## Technical Patterns

### Redirect Handling (getHTML.py pattern)
```python
# Server-side redirects (automatic via requests)
response = session.get(url)
if response.history:  # Check redirect chain
    for resp in response.history:
        print(f"{resp.status_code} {resp.url}")

# Client-side JavaScript redirects
import re
js_redirect = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", response.text)
if js_redirect:
    redirect_url = js_redirect.group(1)
    if redirect_url.startswith('/'):
        redirect_url = f"https://psu.instructure.com{redirect_url}"
    response = session.get(redirect_url)
```

### CSRF Handling
```python
csrf = next((unquote(c.value) for c in s.cookies if c.name == '_csrf_token'), '')
payload = {'_method': 'post', 'authenticity_token': csrf_token}
```

### URL Parsing
```python
path = urlparse(url).path.split('/')
course_id = path[path.index('courses') + 1]
quiz_id = path[path.index('quizzes') + 1]
```

### XPath Queries
```python
doc.xpath('//*[@id="questions"]')  # Questions container
doc.xpath('//*[@id="questions"]/div[contains(@class, "question")]')  # Question elements
question_container.xpath('.//input[@type="radio"]')  # Answer inputs
answer_input.get('value')  # Answer ID (e.g., "4690")
```

### Session Management
```python
cookies = {c['name']: c['value'] for c in json.load(open(config.COOKIES_FILE))}
session = requests.Session()
session.cookies.update(cookies)
session.headers.update({'Accept': 'application/json+canvas-string-ids', 'User-Agent': 'Mozilla/5.0'})
```

### Canvas File Upload (4-step)
```python
# 1. Token
r = session.post('https://psu.instructure.com/files/pending', data={
    'attachment[filename]': filename, 'attachment[size]': str(size),
    'attachment[content_type]': mime, 'attachment[context_code]': f'course_{cid}'
})
info = r.json()

# 2. S3 upload
r = session.post(info['upload_url'], files={'file': (filename, open(path, 'rb'), mime)}, allow_redirects=False)

# 3. Confirm
r = session.get(r.headers['location'])
file_id = str(r.json()['id'])

# 4. Submit
session.post(f".../assignments/{aid}/submissions", data={'submission[attachment_ids]': ','.join(file_ids)})
```

### Concurrent Image Download
```python
from concurrent.futures import ThreadPoolExecutor
tasks = [(url, save_path), ...]  # List of tuples
def dl(url, p): open(p, 'wb').write(requests.get(url, timeout=10).content); return p
with ThreadPoolExecutor(max_workers=20) as ex: list(ex.map(lambda x: dl(x[0], x[1]), tasks))
```

### Gemini Integration
- **Assignments**: `gemini-2.5-pro` (file upload, reasoning)
- **Image Gen**: `gemini-2.5-flash-image` (via `google.genai.Client`)
- **Quiz Vision**: `gemini-2.5-pro` + `genai.upload_file()` for images

### GUI Threading Model
**Pattern** (gui/qt_interact.py:35-51):
```python
def _run_in_thread(func, console_output, task_name, on_success=None):
    """Execute function in daemon thread with console output + success callback"""
    def wrapper():
        try:
            func(console_output)
            console_output.append(f"[SUCCESS] {task_name} completed")
            if on_success:
                on_success()  # Auto-refresh data viewer or status indicators
        except Exception as e:
            console_output.append(f"[ERROR] {task_name} failed: {str(e)}")
    threading.Thread(target=wrapper, daemon=True).start()
```

**All long-running operations** (getCookie, getTodos, getCourses, clean) run in background threads to prevent UI freezing. Each gets dedicated console tab for output streaming.

**Status update thread** (gui/qt.py:757-764): Daemon thread refreshes status indicators every 30 seconds via Qt signals (thread-safe)

### Clean Script
- Whitelist: `clean_whitelist.txt` (dirs end with `/`, auto-keeps `.py` via extension rule)
- Tree preview → user confirm → delete non-whitelisted → recursive empty dir cleanup (10 iterations)

### Keyboard Navigation (Event Filter Pattern)
**Shortcuts** (implemented via `eventFilter` on all QListWidget instances):
- **WASD**: Navigate items (W/S = up/down, A/D = left/right between tabs)
- **C/T/F**: Jump to Courses/TODOs/Files tabs (auto-focuses categoryList)
- **Space**: Open CourseDetail window (on Main > Courses list)
- **Shift+A**: Open Automation window
- **Shift+C**: Open Clean dialog

**Implementation** (gui/qt.py):
```python
# Event filter intercepts WASD before Qt's default handling
def eventFilter(self, obj, event):
    if isinstance(obj, QListWidget) and key in [W,A,S,D]:
        self._handle_wasd_navigation(key, current_widget)
        return True  # Block propagation to prevent conflicts
```

**Priority order**: Check Shift+A/C before A/C to avoid being eaten by navigation.

### Tab Content System (Auto-Caching + Redirect Handling)
**Single-click behavior** (`on_course_detail_item_changed`):
- Click Tab → Automatically check local cache (`Courses/.../Tabs/{safe_name}.md`)
- **Cache hit** → Load + render instantly (no network request)
- **Cache miss** → Auto-fetch + convert + save + render

**Redirect handling** (borrowed from `getHTML.py`):
- **Server-side redirects**: Track via `response.history`
- **Client-side JS redirects**: Parse `window.location.href = '...'` and follow

**Markdown rendering** (qt.py:438-517):
- Enhanced CSS styling (dark theme, blue accents)
- **Table support**: Blue headers, hover effects, zebra striping
- Code blocks with syntax highlighting colors
- Responsive typography

**Keyboard shortcuts** (CourseDetail window - Tabs category):
- **Space** → Open URL in browser
- **F** → Open Tabs folder
- **Double-click** → (removed, now single-click auto-loads)

### Double-Click Handlers
**Main Window** (`on_main_item_double_clicked`):
- Course item → Open CourseDetail window

**CourseDetail Window** (`on_course_detail_item_double_clicked`):
- Syllabus (with green dot) → Open Syll folder
- Textbook file → Open containing folder

**Implementation**: Cross-platform folder opening (`os.startfile` on Windows, `subprocess.Popen(['open'])` on macOS)

### Custom Widget Patterns

**FileItemDelegate** (gui/delegates.py):
```python
# Conditional delegate based on category + force repaint
cdw.itemList.setItemDelegate(
    FileItemDelegate(cdw.itemList)
    if category in ['Syllabus', 'Textbook']
    else QStyledItemDelegate()  # NEVER use None - causes rendering bugs!
)
cdw.itemList.viewport().update()  # Force viewport refresh
```

**Critical bug fix**: `setItemDelegate(None)` prevents viewport refresh in PyQt6 → use `QStyledItemDelegate()` instead.

**IOSToggle** (gui/ios_toggle.py):
- Animated switch (150ms transition)
- Synchronized across all windows via signal/slot connections
- Controls console visibility

## Development Guidelines

**Module organization**:
- `gui/` - UI code (qt.py, qt_interact.py, styles.py, delegates.py, data_manager.py, done_manager.py, course_detail_manager.py, formatters.py, ios_toggle.py)
- `func/` - Production scripts (must work standalone + via GUI)
- `misc/` - Archive (never delete)
- `Courses/` - Unified course materials

**GUI development rules**:
1. Separation of concerns: UI (qt.py) vs handlers (qt_interact.py)
2. Thread safety: Use `_run_in_thread()` + Qt signals
3. Event filters: Install on QListWidget, `return True` to block propagation
4. **CRITICAL**: NEVER use `setItemDelegate(None)` → use `QStyledItemDelegate()` + `viewport().update()`
5. Keyboard shortcuts: Check Shift combinations before single keys
6. Error handling: Wrap threads in try/except → log to console

**Script compatibility**:
- All `func/` scripts work standalone + via GUI
- Use `console.append()` only when `console` exists
- Avoid `input()` in GUI-callable functions
- Save to `config.COURSES_DIR` for course materials

**Before changes**:
1. Check `misc/` for patterns
2. Use `config.py` paths
3. Check `.claude/debug_history/` for known issues

**Script execution**: Always from project root
