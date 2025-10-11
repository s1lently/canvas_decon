# Canvas LMS 自动化工具

Penn State University Canvas 平台学习任务自动化工具集

## 📁 项目结构

```
niubiaaaa/
├── login/                  # 登录认证模块
│   ├── __init__.py
│   ├── getCookie.py       # Selenium 自动登录
│   ├── getTotp.py         # 生成 TOTP 验证码
│   ├── getUsrid.py        # 获取用户 ID
│   └── old_main.py        # 旧版主入口(已废弃)
│
├── func/                   # 自动化功能模块
│   ├── __init__.py
│   ├── getCourses.py      # 获取课程列表
│   ├── getAss.py          # 获取作业列表
│   ├── getHomework.py     # 作业自动完成与提交
│   ├── getQuiz.py         # 测验自动完成与提交 ⭐
│   ├── annotate_quiz_pdf.py  # 测验 PDF 标注工具 ⭐ NEW
│   ├── getSyll.py         # 获取课程大纲
│   ├── getHTML.py         # HTML 内容获取
│   ├── html2md.py         # HTML 转 Markdown
│   ├── getAPI.py          # API 工具函数
│   ├── gCO.py             # 课程操作
│   ├── stQz.py            # 测验状态
│   ├── sel_test.py        # Selenium 测试
│   ├── ask_with_pdf.py    # PDF 问答
│   ├── QUIZ_USAGE.md      # 测验使用指南
│   └── PDF_ANNOTATION_GUIDE.md  # PDF 标注指南
│
├── config.py              # 统一配置文件(路径、API密钥等)
├── main.py                # 主入口文件
├── requirements.txt       # Python 依赖
│
├── account_info.json      # 账户信息(需手动创建)
├── cookies.json           # 登录凭证(自动生成)
├── personal_info.json     # 个人信息(需手动创建)
├── course.json            # 课程数据(自动生成)
│
├── homework_res/          # 作业输出目录
│   └── submission/        # 待提交文件
├── quiz_res/              # 测验输出目录
└── bisc_pdfs/             # 课程 PDF 资料
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置账户信息

创建 `account_info.json`:

```json
{
  "account": "your_email@psu.edu",
  "password": "your_password",
  "otp_keys": "your_2fa_secret_key"
}
```

创建 `personal_info.json` (用于生成个性化作业):

```json
{
  "name": "Your Name",
  "age": 20,
  "weight_kg": 70,
  "weight_lbs": 154,
  "height_cm": 175,
  "height_inches": 69,
  "gender": "Male/Female",
  "location": "Middletown, PA"
}
```

### 3. 获取登录 Cookie

```bash
python main.py
```

### 4. 获取课程列表

```bash
python func/getCourses.py
```

### 5. 运行自动化任务

**作业自动完成:**
```bash
# 编辑 func/getHomework.py 中的 TARGET_ASSIGNMENT_URL
python func/getHomework.py
```

**测验自动完成:**
```bash
# 编辑 func/getQuiz.py 中的 BASE_QUIZ_URL
python func/getQuiz.py
```

## 🔧 配置说明

所有路径和配置都在 `config.py` 中统一管理:

- `COOKIES_FILE` - Cookie 文件路径
- `ACCOUNT_INFO_FILE` - 账户信息文件路径
- `PERSONAL_INFO_FILE` - 个人信息文件路径
- `COURSE_FILE` - 课程数据文件路径
- `GEMINI_API_KEY` - Google Gemini API 密钥
- `CANVAS_BASE_URL` - Canvas 平台 URL

## 📝 核心功能

### 登录模块 (`login/`)

- **自动化登录**: 使用 Selenium 模拟人类行为登录
- **2FA 处理**: 自动生成并输入 TOTP 验证码
- **Cookie 管理**: 保存登录状态供后续使用

### 自动化模块 (`func/`)

#### 作业自动化 (`getHomework.py`)

1. 获取作业详情和要求
2. 使用 Gemini 2.5 Pro 分析并生成答案
3. 自动生成所需图片 (Gemini Flash Image)
4. 转换为 DOCX 格式
5. 自动提交到 Canvas

#### 测验自动化 (`getQuiz.py`)

1. 自动开始/继续测验
2. 解析题目和选项
3. 使用 Gemini API 选择答案
4. 自动提交测验

## ⚠️ 注意事项

1. **API 密钥安全**: 建议将 `GEMINI_API_KEY` 改为环境变量
2. **数据文件**: `account_info.json` 等敏感文件已加入 `.gitignore`
3. **路径管理**: 所有代码从根目录运行,路径通过 `config.py` 统一管理
4. **学术诚信**: 本工具仅供学习研究,使用需遵守学校相关规定

## 🛠️ 技术栈

- **Web 自动化**: Selenium + ChromeDriver
- **HTTP 请求**: requests + BeautifulSoup
- **AI 模型**: Google Gemini 2.5 Pro/Flash
- **文档处理**: python-docx, pypandoc, Pillow
- **其他**: pyotp (2FA), lxml, html2text

## 📄 许可

本项目仅供学习研究使用。
