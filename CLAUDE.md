# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Canvas LMS automation for Penn State University. Automates login (Selenium + 2FA), assignments (Gemini AI + DOCX generation), and quizzes (vision API + auto-submit).

**Security**: Hardcoded `GEMINI_API_KEY` in [config.py](config.py) - handle with care.

## Project Structure

**Three-tier organization**:
- **func/** - Production modules (getTodos, getCourses, getHomework, getQuiz_ultra, getSyll)
- **login/** - Auth (getCookie: Selenium+2FA, getTotp: TOTP generation)
- **misc/** - Deprecated code (old quiz workflows, legacy login implementations)
- **config.py** - Global paths, API keys, URLs
- **clean.py** + **clean_whitelist.txt** - Whitelist-based garbage collection (auto-keeps `.py`, protected dirs)

## Key Commands

```bash
# Setup
pip install -r requirements.txt

# Login (required first)
python main.py

# Recommended workflow
python func/getTodos.py        # Fetch todos + download files → todo_files/
python func/getCourses.py      # Get course list
python func/getHomework.py     # Edit TARGET_ASSIGNMENT_URL first
python func/getQuiz_ultra.py   # Edit BASE_QUIZ_URL first

# Maintenance
python clean.py                # Remove non-whitelisted files
```

## Architecture

### Path Management
All modules run from **project root**. Standard import pattern:
```python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
```

### Authentication Flow
1. `main.py` → reads `account_info.json` → calls `login/getCookie.py`
2. `getCookie.py` → Selenium (Microsoft SSO) → 2FA via `getTotp.py` (TOTP, 3 retries)
3. Saves `cookies.json` → used by all API calls

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

### Data Files (Git-Ignored)
- `account_info.json` - Credentials + TOTP secret
- `personal_info.json` - Student context for personalized answers
- `cookies.json` - Session cookies (auto-generated)
- `course.json`, `todos.json` - Cached data

## Technical Patterns

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

### Clean Script
- Whitelist: `clean_whitelist.txt` (dirs end with `/`, auto-keeps `.py` via extension rule)
- Tree preview → user confirm → delete non-whitelisted → recursive empty dir cleanup (10 iterations)

## Development Guidelines

**Module organization**:
- `func/` - Production code only
- `misc/` - Archive/version history (never delete)
- `func/util/` - Experimental/alternative implementations

**Before changes**:
1. Check `misc/` for similar patterns
2. Use `config.py` paths (no hardcoded paths)
3. Test with `clean.py` to avoid accidental deletion

**Script execution**: Always from project root → `python func/getQuiz_ultra.py`
