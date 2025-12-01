# CLAUDE.md - AI Assistant Development Guide

Essential guidance for Claude Code when working with this Canvas LMS automation codebase.

---

## Project Overview

**Canvas LMS Automation System** - Full-stack Python automation with PyQt6 GUI for Penn State University Canvas platform.

### Key Technologies

- **GUI**: PyQt6 (View pattern, GitHub Dark theme)
- **Backend**: Python 3.10+
- **Auth**: Selenium + TOTP (pyotp)
- **AI**: Gemini + Claude (unified via `func/ai.py`)
- **Web**: requests, lxml, concurrent.futures

### Architecture (Post-Refactor)

```
canvas_decon/
├── main.py                 # Entry point
├── config.py               # All paths & config
├── account_config.json     # User credentials (gitignored)
│
├── AAFS/                   # All Auto-generated Files Storage
│   ├── jsons/              # cookies.json, todos.json, course.json, etc.
│   ├── todo/               # Assignment workspaces
│   ├── courses/            # Course materials
│   └── output/             # Generated outputs
│
├── gui/                    # PyQt6 GUI (12 files + _internal/)
│   ├── app.py              # Main application (~400 lines)
│   ├── main_view.py        # Dashboard + Launcher
│   ├── auto_view.py        # Automation window (4 tabs)
│   ├── detail_view.py      # AutoDetail window
│   ├── course_view.py      # CourseDetail window
│   ├── settings_view.py    # Settings overlay
│   ├── styles.py           # GitHub Dark theme (unified COLORS dict)
│   ├── processors.py       # HTML/Tab processing
│   ├── widgets.py          # Merged: delegates, toast, toggle, progress
│   ├── learn.py            # Merged: prefs, formatters, sitting widget
│   ├── _internal/          # Managers + large widgets
│   │   ├── mgrData.py, mgrDone.py, mgrTask.py
│   │   ├── mgrAutoDetail.py, mgrCourseDetail.py
│   │   ├── wgtSidebar.py, wgtMissionControl.py, wgtAutoDetailModern.py
│   │   ├── utilQtInteract.py, keyboard.py, cfgModel.py
│   │   └── __init__.py
│   └── ui/                 # Qt Designer .ui files
│
├── func/                   # Business logic (CLI + GUI compatible)
│   ├── getTodos.py, getCourses.py, getHistoryTodos.py
│   ├── getHomework.py, getQuiz_ultra.py, getQuizStatus.py
│   ├── getSyll.py, procLearnMaterial.py
│   ├── ai.py               # Unified AI interface (Gemini/Claude)
│   ├── logCookie.py        # Selenium login (from login/)
│   ├── logTotp.py          # TOTP generator (from login/)
│   ├── checkStatus.py      # Status validators
│   └── clean.py            # Cleanup utility with exclusion support
│
├── core/                   # Shared utilities
└── misc/                   # Legacy tools
```

---

## GUI Architecture

### View Pattern (not Handler)

Each view is a simple class that takes `app` reference:

```python
class MainView:
    def __init__(self, app):
        self.app = app
        self.mw = app.main_window  # QWidget from .ui file

    def populate_window(self):
        # Load data and populate widgets
        pass

    def on_item_clicked(self, index):
        # Handle events
        pass
```

### App Structure (gui/app.py)

```python
class CanvasApp(QMainWindow):
    def __init__(self):
        # Load .ui files
        self.main_window = loadUi('gui/ui/main.ui')
        self.automation_window = loadUi('gui/ui/automation.ui')
        # ... more windows

        # Data managers
        self.dm = DataManager()
        self.done_mgr = DoneManager()

        # Views (not handlers!)
        self.main_view = MainView(self)
        self.auto_view = AutoView(self)
        self.detail_view = DetailView(self)
        self.course_view = CourseView(self)
        self.settings_view = SettingsView(self)

        # Stacked widget for navigation
        self.stacked_widget.addWidget(self.main_window)
        self.stacked_widget.addWidget(self.automation_window)
        # ...
```

### Theme (gui/styles.py)

```python
COLORS = {
    'bg': '#0d1117',           # GitHub Dark background
    'bg_secondary': '#161b22',
    'bg_tertiary': '#21262d',
    'border': '#30363d',
    'text': '#e6edf3',
    'text_secondary': '#8b949e',
    'accent': '#238636',       # Green
    'accent_blue': '#1f6feb',
    # ...
}

def get_app_stylesheet():
    return f"""
        QMainWindow {{ background-color: {COLORS['bg']}; }}
        QListWidget {{ background-color: {COLORS['bg_secondary']}; }}
        ...
    """
```

---

## Key Modules

### gui/widgets.py (merged)

Contains:
- `TodoItemDelegate` - Urgency-based gradient + type dots
- `FileItemDelegate` - Green/blue dot indicators
- `ToastNotification` - Next.js style toast
- `IOSToggle` - Animated toggle switch
- `ProgressWidget` - Compact progress indicator

### gui/learn.py (merged)

Contains:
- Preferences: `load_preferences()`, `get_product()`, `get_model()`
- Formatters: `format_course()`, `format_todo()`, `format_folder()`
- `LearnSittingWidget` - 2-tab widget for textbook management

### gui/_internal/

Large widgets and managers:
- `DataManager` - Loads courses, todos, files
- `DoneManager` - Checkbox state persistence
- `TaskManager` - Background task tracking
- `MissionControl` - Task progress UI
- `GlobalSidebar` - Floating sidebar with hover animation
- `KeyboardHandler` - WASD navigation

### func/ai.py

Unified AI interface:
```python
def call_ai(prompt, product, model, files=[], thinking=False):
    if product == 'Gemini':
        return _gemini(prompt, model, ...)
    elif product == 'Claude':
        return _claude(prompt, model, thinking=thinking)
```

### func/clean.py

Interactive cleanup with exclusion:
```python
items = scan_items()  # Returns [(path, type, size_str), ...]
clean_items(items, exclude_indices={0, 2, 5})  # Skip items 0, 2, 5
```

---

## Data Flow

### config.py Paths

```python
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
AAFS_DIR = os.path.join(ROOT_DIR, 'AAFS')

JSONS_DIR = os.path.join(AAFS_DIR, 'jsons')
TODO_DIR = os.path.join(AAFS_DIR, 'todo')
COURSES_DIR = os.path.join(AAFS_DIR, 'courses')
OUTPUT_DIR = os.path.join(AAFS_DIR, 'output')

COOKIES_FILE = os.path.join(JSONS_DIR, 'cookies.json')
TODOS_FILE = os.path.join(JSONS_DIR, 'todos.json')
COURSE_FILE = os.path.join(JSONS_DIR, 'course.json')
ACCOUNT_CONFIG_FILE = os.path.join(ROOT_DIR, 'account_config.json')
```

### Threading Pattern (Mission Control)

```python
def on_button_clicked(app):
    def run(progress):
        progress.update(progress=50, status="Working...")
        # Do work
        progress.finish("Done!")

    app.mission_control.start_task("Task Name", run, on_success=callback)
```

### Signal/Slot for Thread-safe UI

```python
# Define in AppSignals
class AppSignals(QObject):
    toast_show = pyqtSignal(str, str, int)  # message, type, duration

# Connect
self.signals.toast_show.connect(self._show_toast)

# Emit from anywhere (thread-safe)
self.signals.toast_show.emit("Success!", "success", 3000)
```

---

## Common Operations

```bash
# Start GUI
python main.py

# CLI mode
python func/getTodos.py
python func/getHomework.py --url "..." --product Gemini
python func/getQuiz_ultra.py --url "..." --product Claude --thinking

# Status check
python func/checkStatus.py

# Clean (interactive)
python func/clean.py
```

---

## Development Rules

1. **View Pattern**: Use `*_view.py` classes, not handlers
2. **Paths**: Always use `config.*` constants
3. **Threading**: Use Mission Control for long operations
4. **UI Updates**: Use signals from background threads
5. **Imports**: Use `from gui._internal.xxx import` for internal modules
6. **Theme**: Use `COLORS` dict from `gui/styles.py`

---

## File Naming Convention

**gui/**:
- `*_view.py` - View classes (main_view, auto_view, etc.)
- `widgets.py` - Small reusable widgets
- `learn.py` - Learning module
- `styles.py` - Theme and styles
- `processors.py` - Content processors

**gui/_internal/**:
- `mgr*.py` - Managers
- `wgt*.py` - Large widgets
- `util*.py` - Utilities
- `cfg*.py` - Config

**func/**:
- `get*.py` - Data fetching
- `proc*.py` - Data processing
- `log*.py` - Login/auth
- `ai.py` - AI interface
- `check*.py`, `clean.py` - Utilities
