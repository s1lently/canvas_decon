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

# 数据文件路径(存放在根目录)
COOKIES_FILE = os.path.join(ROOT_DIR, 'cookies.json')
ACCOUNT_CONFIG_FILE = os.path.join(ROOT_DIR, 'account_config.json')
PERSONAL_INFO_FILE = os.path.join(ROOT_DIR, 'personal_info.json')
COURSE_FILE = os.path.join(ROOT_DIR, 'course.json')
DONE_FILE = os.path.join(ROOT_DIR, 'Done.txt')

# 输出目录
OUTPUT_DIR = os.path.join(ROOT_DIR, 'homework_res')
SUBMISSION_DIR = os.path.join(OUTPUT_DIR, 'submission')
QUIZ_RES_DIR = os.path.join(ROOT_DIR, 'quiz_res')
PDF_DIR = os.path.join(ROOT_DIR, 'bisc_pdfs')

# 课程文件系统 (统一管理所有课程资料)
COURSES_DIR = os.path.join(ROOT_DIR, 'Courses')

# Load configuration from account_config.json
def _load_account_config():
    """Load configuration from account_config.json"""
    try:
        if os.path.exists(ACCOUNT_CONFIG_FILE):
            with open(ACCOUNT_CONFIG_FILE) as f:
                return json.load(f)
    except:
        pass
    return {}

_config = _load_account_config()

# API 配置 (从account_config读取，否则使用默认值)
GEMINI_API_KEY = _config.get('gemini_api_key', 'AIzaSyBZTx5UDH7pxyYZUgpDzKHRU25FWoPIA8I')

# Canvas URLs (从account_config读取，否则使用默认值)
CANVAS_BASE_URL = _config.get('preference', {}).get('base_url', 'https://psu.instructure.com')

# Legacy compatibility
ACCOUNT_INFO_FILE = ACCOUNT_CONFIG_FILE

def ensure_dirs():
    """确保所有必要的目录存在"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SUBMISSION_DIR, exist_ok=True)
    os.makedirs(QUIZ_RES_DIR, exist_ok=True)
    os.makedirs(COURSES_DIR, exist_ok=True)
