"""
项目配置文件
统一管理所有文件路径,确保无论从哪里调用都能正确访问

使用方法：在任何模块中导入config
```python
import sys
import os
# 添加项目根目录到sys.path（跨平台通用）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
```
"""
import os
import json

# 获取项目根目录(本文件所在目录)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# === AAFS: All Auto-generated Files Storage ===
AAFS_DIR = os.path.join(ROOT_DIR, 'AAFS')

# JSON数据目录
JSONS_DIR = os.path.join(AAFS_DIR, 'jsons')

# 数据文件路径
COOKIES_FILE = os.path.join(JSONS_DIR, 'cookies.json')
ACCOUNT_CONFIG_FILE = os.path.join(ROOT_DIR, 'account_config.json')  # Keep in root (user config, gitignored)
PERSONAL_INFO_FILE = os.path.join(JSONS_DIR, 'personal_info.json')
COURSE_FILE = os.path.join(JSONS_DIR, 'course.json')
TODOS_FILE = os.path.join(JSONS_DIR, 'todos.json')
HIS_TODO_FILE = os.path.join(JSONS_DIR, 'his_todo.json')
LEARN_PREFERENCES_FILE = os.path.join(JSONS_DIR, 'learn_preferences.json')
DONE_FILE = os.path.join(JSONS_DIR, 'Done.txt')

# TODO 工作目录 (统一自动化工作空间)
TODO_DIR = os.path.join(AAFS_DIR, 'todo')

# 课程文件系统 (统一管理所有课程资料)
COURSES_DIR = os.path.join(AAFS_DIR, 'courses')

# 输出目录 (统一所有生成文件: quiz + homework)
OUTPUT_DIR = os.path.join(AAFS_DIR, 'output')

# Legacy compatibility
SUBMISSION_DIR = OUTPUT_DIR
QUIZ_RES_DIR = OUTPUT_DIR

# Load configuration from account_config.json
def _load_account_config():
    """Load configuration from account_config.json"""
    try:
        if os.path.exists(ACCOUNT_CONFIG_FILE):
            with open(ACCOUNT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[WARN] Invalid account_config.json: {e}")
    except IOError as e:
        print(f"[WARN] Cannot read account_config.json: {e}")
    return {}

_config = _load_account_config()

# API Keys: Priority order = config file > environment variable > None
# SECURITY: Never provide default API keys in code
GEMINI_API_KEY = _config.get('gemini_api_key') or os.environ.get('GEMINI_API_KEY')
CLAUDE_API_KEY = _config.get('claude_api_key') or os.environ.get('CLAUDE_API_KEY')

def get_api_key(provider: str) -> str:
    """Get API key with validation. Raises ConfigError if missing."""
    from core.exceptions import ConfigError
    key = GEMINI_API_KEY if provider.lower() == 'gemini' else CLAUDE_API_KEY
    if not key:
        raise ConfigError(
            f"{provider.upper()}_API_KEY not configured. "
            f"Set in account_config.json or {provider.upper()}_API_KEY env var."
        )
    return key

# Canvas URLs (从account_config读取，否则使用默认值)
CANVAS_BASE_URL = _config.get('preference', {}).get('base_url', 'https://psu.instructure.com')

def reload_config():
    """Reload configuration from account_config.json"""
    global _config, GEMINI_API_KEY, CLAUDE_API_KEY, CANVAS_BASE_URL
    _config = _load_account_config()
    GEMINI_API_KEY = _config.get('gemini_api_key') or os.environ.get('GEMINI_API_KEY')
    CLAUDE_API_KEY = _config.get('claude_api_key') or os.environ.get('CLAUDE_API_KEY')
    CANVAS_BASE_URL = _config.get('preference', {}).get('base_url', 'https://psu.instructure.com')
    gemini_preview = f"{GEMINI_API_KEY[:8]}..." if GEMINI_API_KEY else "(not set)"
    claude_preview = f"{CLAUDE_API_KEY[:8]}..." if CLAUDE_API_KEY else "(not set)"
    print(f"[INFO] Config reloaded. Gemini: {gemini_preview} Claude: {claude_preview}")

# Legacy compatibility
ACCOUNT_INFO_FILE = ACCOUNT_CONFIG_FILE

# 默认提示词
DEFAULT_PROMPTS = {
    'quiz': """You are taking a quiz. Analyze each question and select the CORRECT answer based on your knowledge.

IMPORTANT INSTRUCTIONS:
- Each question has multiple options with unique IDs
- You must select the ID of the CORRECT answer for each question
- DO NOT just pick the first option - use your knowledge to choose the right answer
- Images are passed to you in sequential order (Image 1, Image 2, Image 3, etc.)
- If an option says "[See: Image 3]", that option corresponds to the 3rd image in the sequence
- If a question has "question_images": ["Image 1"], that question relates to the 1st image
- Carefully analyze ALL images to select the correct answer
- The images will be passed to you along with the prompt in order

CRITICAL: Return ONLY valid JSON with NO additional text, explanations, or markdown formatting.
Format: {"question_id": "answer_id", ...}

Example: {"question_97585716": "7574", "question_97585717": "8821"}

The questions will be provided in this format:
{
  "question_id": {
    "question": "question text",
    "options": {
      "option_id_1": "option text 1",
      "option_id_2": "No answer text provided. [See: Image 3]",
      ...
    },
    "question_images": ["Image 1"]  // optional, images that are part of the question
  }
}

Your response should map each question_id to the correct option_id.""",

    'homework': """Analyze the description and complete the assignment.

**Decision Logic:**
1. If requires course materials (lecture/textbook) → check PDF attachments for relevant content → [yes] continue
2. If requires personal experience/real-life examples (food labels, daily life) → no attachments needed → directly [yes] and write content

**Answer Requirements:**
1. Pure English
2. Avoid complex sentences/vocabulary. Avoid phrases like "resulting in", "including", "leading to". Keep logic simple. Only use necessary technical terms.
3. Start with status: [yes] = can complete [no] = cannot complete (only if description incomplete)
4. Use clean markdown format

**Format Rules (strictly follow):**
- ❌ No dividers: ----, ====, ———
- ❌ No code blocks: ```
- ❌ No decorative symbols: tables, frames, ASCII art
- ❌ No bullet points: *, -, •
- ✅ Bold question numbers: **1)** **2)** **3)** or **Question 1:**
- ✅ Letter numbering for multiple points: a. \\n b. \\n c. ... (each on new line)
- ✅ Only use: headers (###), bold (**), paragraphs, letter numbering

**Image Request Annotation:**
ONLY if assignment EXPLICITLY requires uploading an image/photo/file (e.g., "Upload a copy of the food label", "Attach a photo"), add at the **end** of answer:
[gen_img]
{
name: filename.png
des: Detailed description for image generation. IMPORTANT: Infer the full context from the question and describe what the image should realistically show based on the assignment requirements.
}
DO NOT generate images for text-only calculation questions or written reflections.

**Personal Experience Rules:**
- Location: Middletown, PA
- Background: AI CV, C++, Linux, reverse engineering (only reference if needed)
- Food/daily life: Write common realistic scenarios naturally

**Note:** For personal experience assignments, write naturally like a real student. Make question numbers prominent."""
}

def ensure_dirs():
    """确保所有必要的目录存在"""
    os.makedirs(AAFS_DIR, exist_ok=True)
    os.makedirs(JSONS_DIR, exist_ok=True)
    os.makedirs(TODO_DIR, exist_ok=True)
    os.makedirs(COURSES_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
