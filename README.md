# Canvas LMS Automation System

Penn State University Canvas 平台自动化系统，PyQt6 GUI + CLI 工具。

## Features

- **Modern GUI**: PyQt6 + GitHub Dark theme + View pattern
- **AI Integration**: Gemini + Claude dual engine
- **Homework Automation**: AI generate → DOCX → auto submit
- **Quiz Automation**: Vision API + auto answer + auto submit
- **Course Management**: Unified file system + tab caching

## Project Structure

```
canvas_decon/
├── main.py                 # Entry point
├── config.py               # Global config
├── account_config.json     # Credentials (gitignored)
│
├── AAFS/                   # All Auto-generated Files Storage
│   ├── jsons/              # cookies, todos, courses cache
│   ├── todo/               # Assignment workspaces
│   ├── courses/            # Course materials
│   └── output/             # Generated outputs
│
├── gui/                    # PyQt6 GUI
│   ├── app.py              # Main application
│   ├── *_view.py           # View classes (main, auto, detail, course, settings)
│   ├── styles.py           # GitHub Dark theme
│   ├── widgets.py          # Delegates, toast, toggle, progress
│   ├── learn.py            # Learning module
│   ├── processors.py       # Content processors
│   ├── _internal/          # Managers + large widgets
│   └── ui/                 # Qt Designer .ui files
│
├── func/                   # Business logic (CLI + GUI)
│   ├── get*.py             # Data fetching (todos, courses, homework, quiz)
│   ├── proc*.py            # Data processing
│   ├── ai.py               # Unified AI interface
│   ├── logCookie.py        # Selenium login
│   ├── logTotp.py          # TOTP generator
│   ├── checkStatus.py      # Status validators
│   └── clean.py            # Cleanup utility
│
├── core/                   # Shared utilities
└── misc/                   # Legacy tools
```

## Quick Start

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Configure

Create `account_config.json`:

```json
{
  "account": "your_email@psu.edu",
  "password": "your_password",
  "otp_key": "YOUR_TOTP_SECRET",
  "gemini_api_key": "AIzaSy...",
  "claude_api_key": "sk-ant-..."
}
```

**No TOTP key?** Set `"otp_key": "loginself"` for manual 2FA mode.

### 3. Run

```bash
python main.py
```

## GUI Navigation

```
[Launcher] - Start screen
├── TODOs list (left) - Double-click → AutoDetail
└── Courses list (right) - Double-click → CourseDetail

[Main Window] - 3 columns
├── Categories: Courses (C) / TODOs (T) / Files (F)
├── Items list with urgency colors
└── Detail view (HTML formatted)

[Keyboard]
├── W/S - Up/Down
├── A/D - Left/Right column
├── Space - Open CourseDetail
├── Shift+Space - Open AutoDetail
├── Shift+A - Automation window
```

## Homework Workflow

1. **Select TODO** → Double-click → AutoDetail window
2. **Configure**: Product (Gemini/Claude) + Model + Prompt
3. **Add files**: `AAFS/todo/{assignment}/auto/input/`
4. **Preview**: Click Preview → AI generates → `auto/output/`
5. **Submit**: Click Submit → Auto upload to Canvas

## Quiz Workflow

1. **Select Quiz** → Double-click → AutoDetail window
2. **Configure**: Product + Model + Thinking mode (Claude)
3. **Preview**: Click Preview → Parse questions → AI answers
4. **Review**: Check `QesWA.md` for answers
5. **Submit**: Click Submit → Auto submit to Canvas

## CLI Mode

```bash
# Get cookies
python func/logCookie.py

# Get data
python func/getTodos.py
python func/getCourses.py

# Automation
python func/getHomework.py --url "..." --product Gemini
python func/getQuiz_ultra.py --url "..." --product Claude --thinking

# Utilities
python func/checkStatus.py
python func/clean.py  # Interactive cleanup
```

## Data Files

| File | Location | Description |
|------|----------|-------------|
| `account_config.json` | Root | Credentials (gitignored) |
| `cookies.json` | AAFS/jsons/ | Session cookies (24h) |
| `todos.json` | AAFS/jsons/ | TODO cache |
| `course.json` | AAFS/jsons/ | Course cache |
| `Done.txt` | AAFS/jsons/ | Completed items |

## Security

- Never commit `account_config.json`
- Cookies expire in 24 hours
- TOTP key = password level secret

## Technical Notes

- **Cookie expiry**: 24h, auto-refresh available
- **API quotas**: Gemini/Claude daily limits apply
- **Quiz support**: Multiple choice only
- **Image recognition**: Depends on AI vision capability

## License

MIT - For educational use only. Respect your institution's academic integrity policies.
