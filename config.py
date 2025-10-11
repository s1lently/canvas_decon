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

# 获取项目根目录(本文件所在目录)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据文件路径(存放在根目录)
COOKIES_FILE = os.path.join(ROOT_DIR, 'cookies.json')
ACCOUNT_INFO_FILE = os.path.join(ROOT_DIR, 'account_info.json')
PERSONAL_INFO_FILE = os.path.join(ROOT_DIR, 'personal_info.json')
COURSE_FILE = os.path.join(ROOT_DIR, 'course.json')

# 输出目录
OUTPUT_DIR = os.path.join(ROOT_DIR, 'homework_res')
SUBMISSION_DIR = os.path.join(OUTPUT_DIR, 'submission')
QUIZ_RES_DIR = os.path.join(ROOT_DIR, 'quiz_res')
PDF_DIR = os.path.join(ROOT_DIR, 'bisc_pdfs')

# API 配置
GEMINI_API_KEY = "AIzaSyBZTx5UDH7pxyYZUgpDzKHRU25FWoPIA8I"

# Canvas URLs
CANVAS_BASE_URL = "https://psu.instructure.com"

def ensure_dirs():
    """确保所有必要的目录存在"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SUBMISSION_DIR, exist_ok=True)
    os.makedirs(QUIZ_RES_DIR, exist_ok=True)
