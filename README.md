# Canvas LMS Automation System

Penn State University Canvas平台自动化系统，带完整PyQt6图形界面和CLI工具。

## 🎯 核心特性

- **🖥️ 现代GUI**: PyQt6深色主题，模块化架构 (87%代码量减少)，浮动侧边栏
- **🎨 平滑动画**: 侧边栏悬停展开 (70px→200px, 200ms动画)，实时状态监控
- **🔐 智能登录**: Selenium自动化 + TOTP 2FA，24小时Cookie自动刷新
- **🤖 AI驱动**: 支持Gemini和Claude双引擎，可选Thinking模式
- **📚 作业自动化**: 分析要求 → 生成答案 → 转换DOCX → 自动提交
- **📝 测验自动化**: 视觉API处理图片题目 → AI选择答案 → 自动提交
- **📖 课程管理**: 统一文件系统，自动缓存tabs，markdown渲染
- **⌨️ 键盘导航**: WASD移动，C/T/F快速跳转，Shift组合键

## 📁 项目结构

```
canvas_decon/
├── main.py                 # GUI入口 (python main.py 启动)
├── config.py               # 全局配置 (路径、API密钥、默认prompts)
├── checkStatus.py          # 状态检查系统 (5个验证器)
├── clean.py                # 白名单垃圾清理
│
├── gui/                    # PyQt6 GUI系统 (模块化架构)
│   ├── qt.py              # 主应用类 (CanvasApp, 227行, 87%减少)
│   ├── utilQtInteract.py  # 按钮回调 + 线程管理
│   ├── cfgStyles.py       # Dark Next.js主题
│   ├── rdrDelegates.py    # 自定义渲染 (TodoItemDelegate, FileItemDelegate)
│   ├── mgrData.py         # JSON数据加载
│   ├── mgrDone.py         # 复选框状态持久化 (Done.txt)
│   ├── mgrCourseDetail.py # 课程详情管理
│   ├── mgrAutoDetail.py   # 自动化详情管理
│   ├── utilFormatters.py  # HTML格式化器
│   ├── wgtIOSToggle.py    # iOS风格开关组件
│   ├── wgtSidebar.py      # 浮动侧边栏 (70px→200px动画)
│   ├── cfgModel.py        # AI模型配置
│   ├── qt_utils/          # 模块化处理器
│   │   ├── window_handlers/     # 7个窗口处理器
│   │   ├── event_handlers/      # 键盘事件处理
│   │   ├── content_processors/  # HTML/Tab加载/预览
│   │   └── initializers/        # UI/Signal初始化器
│   └── ui/                # Qt Designer UI文件 (6个窗口)
│       ├── main.ui        # 主窗口
│       ├── launcher.ui    # 启动器覆盖层
│       ├── sitting.ui     # 设置窗口
│       ├── automation.ui  # 自动化窗口
│       ├── course_detail.ui    # 课程详情
│       └── autoDetail.ui       # 自动化详情
│
├── func/                   # 核心功能模块 (CLI + GUI兼容)
│   ├── getTodos.py        # 获取TODO + 下载文件 → todo/
│   ├── getCourses.py      # 获取课程列表 + tabs
│   ├── getHomework.py     # 作业自动化 (AI生成 + DOCX + 提交)
│   ├── getQuiz_ultra.py   # 测验自动化 (视觉API + 自动提交)
│   ├── getSyll.py         # 批量下载大纲
│   ├── utilPromptFiles.py # 统一AI调用接口 (Gemini/Claude)
│   ├── utilModelSelector.py # AI模型列表获取
│   └── mgrHistory.py      # 历史TODO归档
│
├── login/                  # 认证模块
│   ├── getCookie.py       # Selenium自动登录 (人类行为模拟)
│   └── getTotp.py         # TOTP验证码生成
│
├── Courses/                # 统一课程文件系统 (Git忽略)
│   └── {course_name}_{id}/
│       ├── Syll/          # 大纲文件
│       ├── Files/
│       │   └── Textbook/  # 教材PDFs
│       └── Tabs/          # Tab内容缓存 (markdown)
│
├── todo/                   # TODO工作目录 (Git忽略)
│   └── {assignment}_{timestamp}/
│       ├── files/         # 下载的参考文件
│       └── auto/
│           ├── input/     # 手动放置的输入文件
│           └── output/    # 自动化生成的输出
│
├── misc/jsons/             # 运行时数据 (Git忽略)
│   ├── cookies.json        # Session cookies
│   ├── todos.json          # TODO缓存
│   ├── course.json         # 课程缓存
│   ├── his_todo.json       # 历史TODO归档
│   ├── personal_info.json  # 个人信息
│   ├── learn_preferences.json  # 学习偏好
│   └── Done.txt            # 已完成标记
│
├── account_config.json     # 账户配置 (Git忽略, 保留在根目录)
└── requirements.txt        # Python依赖
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

**核心依赖**:
- PyQt6 (GUI框架)
- Selenium + webdriver-manager (登录自动化)
- requests, lxml, BeautifulSoup4 (HTTP + HTML解析)
- python-docx, Pillow, markdown (文档处理)
- google-generativeai (Gemini API)
- anthropic (Claude API)

### 2. 配置账户信息

创建 `account_config.json`:

```json
{
  "account": "your_email@psu.edu",
  "password": "your_password",
  "otp_key": "YOUR_TOTP_SECRET_BASE32",
  "gemini_api_key": "AIzaSy...",
  "claude_api_key": "sk-ant-api03-...",
  "preference": {
    "base_url": "https://psu.instructure.com"
  }
}
```

**获取TOTP密钥**: 在设置2FA时，扫描二维码前查看"手动输入密钥"，复制Base32字符串。

### 3. 启动GUI

```bash
python main.py
```

**首次启动流程**:
1. 自动弹出**Launcher覆盖层**
2. 点击右上角**Settings** → 输入账号信息 → Submit
3. 点击**Get Cookie** → 自动登录 + 保存cookies.json
4. 自动运行**Get Courses** + **Get TODOs**
5. 状态指示器全部变绿 ✅

## 📖 使用指南

### 主窗口导航

```
[Launcher覆盖层] (Alt+L或点击Back按钮)
├─ TODOs列表 (左侧)
│  └─ 双击 → 打开AutoDetail窗口
└─ Courses列表 (右侧)
   └─ 双击 → 打开CourseDetail窗口

[Main窗口] - 3列布局
├─ 类别列表 (左)
│  ├─ Courses    (C键快速跳转)
│  ├─ TODOs      (T键快速跳转)
│  └─ Files      (F键快速跳转)
├─ 项目列表 (中)
│  ├─ [筛选] Homework/Quiz/Discussion/Automatable
│  └─ [复选框] 标记完成 → 保存到Done.txt
└─ 详情视图 (右)
   └─ HTML格式化显示
```

**键盘快捷键**:
- `W/S` - 上下移动
- `A/D` - 左右切换列
- `C/T/F` - 跳转到Courses/TODOs/Files
- `Space` - 打开CourseDetail (Courses类别)
- `Shift+Space` - 打开AutoDetail (TODOs类别)
- `Shift+A` - 打开Automation窗口
- `Shift+C` - 打开Clean对话框

### 作业自动化工作流

```
[步骤1] 选择TODO
Main窗口 → TODOs类别 → 双击自动化作业 → 打开AutoDetail窗口

[步骤2] 配置参数
├─ Product: Gemini / Claude
├─ Model: gemini-2.5-pro / claude-sonnet-4-5 (自动拉取可用模型)
├─ Thinking: ON/OFF (Claude专属，8000 tokens预算)
└─ Prompt: 编辑或使用默认 (config.DEFAULT_PROMPTS['homework'])

[步骤3] 准备参考文件
├─ 自动显示: todo/{assignment}/files/ (getTodos下载的文件)
└─ 手动添加: todo/{assignment}/auto/input/ (放置额外PDFs)

[步骤4] 生成预览
点击 Preview → 后台运行 → 生成到 auto/output/
├─ answer.md (markdown答案)
├─ answer.docx (Word文档)
└─ *.png (如果prompt请求生成图片)

[步骤5] 查看预览
├─ aiPreviewView自动刷新 (markdown渲染 + CSS样式)
├─ 点击 "Open Folder" → 打开输出目录
└─ 点击 "Debug" → CLI模式执行 (独立进程，方便调试)

[步骤6] 提交
├─ 点击 Submit → 确认对话框
├─ 4步上传流程: Token → S3 → Confirm → Submit
└─ 状态: "Status: Submitted successfully"
```

### 测验自动化工作流

```
[步骤1] 选择Quiz TODO
Main窗口 → TODOs类别 → 双击Quiz → AutoDetail窗口

[步骤2] 配置参数
├─ Product: Gemini / Claude
├─ Model: gemini-2.5-pro / claude-sonnet-4-5
├─ Thinking: ON (推荐，Claude专属)
└─ Prompt: 编辑或使用默认 (config.DEFAULT_PROMPTS['quiz'])

[步骤3] 生成预览
点击 Preview → 后台运行:
├─ 自动访问 /quizzes/{qid}/take (开始quiz)
├─ lxml XPath解析题目 + 选项
├─ 并发下载所有图片 (20 workers)
│   ├─ questions: auto/output/images/q_{qid}_{i}.png
│   └─ answers: auto/output/images/a_{aid}_{i}.png
├─ 上传图片到AI (Gemini URI / Claude base64)
├─ AI返回答案字典: {"question_123": "answer_456"}
└─> 生成预览文件:
    ├─ questions.html (原始HTML)
    ├─ questions.md (格式化预览)
    └─ QesWA.md (带✅标记的答案)

[步骤4] 查看预览
├─ aiPreviewView渲染 (嵌入base64图片)
├─ 检查答案准确性
└─ 统计: Total {N} | Answered {M} | Unanswered {K}

[步骤5] 提交
├─ 点击 Submit → 确认对话框
├─ POST /quizzes/{qid}/submissions (隐藏字段 + 答案)
└─ 状态: "Status: Submitted successfully"
```

### 课程详情浏览

```
[打开CourseDetail]
Main窗口 → Courses类别 → 双击课程 → CourseDetail窗口

[6个类别]
├─ Introduction    # 课程基本信息
├─ Homework        # 筛选出作业类TODO
├─ Quiz            # 筛选出测验类TODO
├─ Discussion      # 筛选出讨论类TODO
├─ Syllabus        # 大纲 (双击→打开Syll/文件夹)
├─ Tabs            # 所有课程tabs (单击→自动缓存+渲染)
└─ Textbook        # 教材PDFs (双击→打开文件夹)

[Tab自动缓存机制]
单击Tab → 检查 Courses/.../Tabs/{safe_name}.md
├─ [存在] 立即加载 (无网络请求)
└─ [不存在] 后台fetch → 转markdown → 保存 → 渲染
    ├─ [特殊处理] Grades页面 → 解析ENV.submissions JSON
    └─ [特殊处理] Modules页面 → API获取模块列表

[快捷键]
├─ Space → 在浏览器打开Tab URL
├─ F → 打开当前类别文件夹 (Syll/Tabs/Textbook)
└─ Double-click → 打开本地文件夹
```

## 🔧 状态监控系统

```
5个状态指示器 (颜色: 红🔴/绿🟢/黄🟡)
├─ Account   # account_config.json完整性
├─ Cookie    # cookies.json有效性 (<24h + API测试)
├─ TODOs     # todos.json非空
├─ Network   # Canvas API可达性
└─ Courses   # course.json非空

[自动修复]
├─ Cookie过期 → 自动运行getCookie
├─ Course缺失 → 自动运行getCourses
└─ TODO缺失 → 自动运行getTodos

[后台线程]
├─ status_update_thread (每30秒刷新)
└─ archive_thread (每5分钟归档过期TODO)
```

## 🎨 视觉特性

### TodoItemDelegate - 紧急度渐变背景

```
基于due_date的动态着色:
├─ 过期 (hours_left <= 0)
│   └─> 深红色 (r=100, g=0, alpha=150)
└─ 未过期
    ├─> t = min(hours_left / 168, 1.0)  # 168h = 7天
    ├─> urgency = exp(-3 * t)           # 指数衰减
    ├─> r = int(urgency^0.7 * 100)      # 红色分量
    ├─> g = int((1-urgency^1.5) * 100)  # 绿色分量
    └─> alpha = 60 + urgency * 90       # 透明度

[右侧叠加] (从右到左)
├─ 🔴🔵🟣🟡 彩色圆点 (Automatable/Discussion/Quiz/Homework)
├─ HW/QZ/DS 类型标签
└─> mm/dd 截止日期
```

### IOSToggle - 动画开关

```
特性:
├─ 200ms平滑动画 (InOutCubic缓动)
├─ 背景颜色: #2a2a2a (OFF) → #3b82f6 (ON)
├─ 白色圆形thumb滑动
└─ 全窗口同步 (signal/slot连接)

用途:
├─ Console显示/隐藏
└─ History模式切换 (蓝色半透明 + 过期TODO)
```

## 🧠 AI调用系统

### 统一接口 (func/utilPromptFiles.py)

```python
call_ai(prompt, product, model, files=[], uploaded_info=None, thinking=False)

[Gemini分支]
├─ 预上传: genai.upload_file(path) → uri
├─ 调用: GenerativeModel(model).generate_content([prompt, file_obj_1, ...])
└─ 返回: response.text

[Claude分支]
├─ 预处理: base64编码文件 (image/document)
├─ 构建content: [{"type": "text"}, {"type": "image", "source": {...}}, ...]
├─ [thinking模式] params["thinking"] = {"type": "enabled", "budget_tokens": 8000}
└─ 返回: block.text
```

### Prompt系统

**作业Prompt** (config.DEFAULT_PROMPTS['homework']):
- 决策逻辑: 需要课程资料 → 检查PDF附件 / 个人经验 → 直接写作
- 答案要求: 纯英文、简单句式、避免复杂词汇
- 格式规则:
  - ❌ 禁止: 分隔线(----)、代码块(```)、bullet points(*, -)
  - ✅ 使用: **1)** **2)**粗体编号、a. b. c.字母编号
- 图片请求: `[gen_img]\n{name: xxx.png\ndes: 详细描述}`
- 个人信息: 自动注入personal_info.json内容

**测验Prompt** (config.DEFAULT_PROMPTS['quiz']):
- 关键指令: DO NOT just pick first option - use knowledge
- 图片映射:
  - Gemini: `[See: https://generativelanguage.googleapis.com/...]`
  - Claude: `[See: Image 3]` (序号引用)
- 返回格式: 纯JSON `{"question_id": "answer_id"}`
- 严格模式: NO explanations, NO markdown

## 📂 数据文件说明

### account_config.json (必须手动创建)

```json
{
  "account": "abc123@psu.edu",
  "password": "YourPassword123",
  "otp_key": "JBSWY3DPEHPK3PXP",
  "gemini_api_key": "AIzaSyBZTx5UDH...",
  "claude_api_key": "sk-ant-api03-BO8dm...",
  "preference": {
    "base_url": "https://psu.instructure.com"
  }
}
```

### personal_info.json (可选，用于个性化作业)

```json
{
  "name": "John Doe",
  "age": 20,
  "weight_kg": 70,
  "weight_lbs": 154,
  "height_cm": 175,
  "height_inches": 69,
  "gender": "Male",
  "location": "Middletown, PA"
}
```

### todos.json (自动生成)

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
      "is_quiz": true,
      "submitted": false,
      "locked_for_user": false,
      "folder": "Week_5_Quiz_20251020_235900",
      "assignment_folder": "/full/path/to/todo/Week_5_Quiz_20251020_235900",
      "quiz_metadata": {
        "question_count": 15,
        "attempt": 0,
        "allowed_attempts": 2,
        "attempts_left": 2,
        "time_limit": 60,
        "locked_for_user": false
      }
    }
  }
]
```

### Done.txt (自动生成，复选框状态)

```
https://psu.instructure.com/courses/2418560/assignments/17474475
https://psu.instructure.com/courses/2418560/quizzes/5363417
```

## 🛠️ CLI模式

所有`func/`模块支持独立CLI运行：

```bash
# 获取Cookie (自动登录)
python login/getCookie.py

# 获取课程列表
python func/getCourses.py
# 输出: course.json

# 获取TODOs + 下载文件
python func/getTodos.py
# 输出: todos.json + todo/{assignment}/files/

# 作业自动化 (需要先编辑TARGET_ASSIGNMENT_URL)
python func/getHomework.py --url "..." --product Gemini --model gemini-2.5-pro
# 输出: output/answer.md + output/answer.docx

# 测验自动化 (需要先编辑BASE_QUIZ_URL)
python func/getQuiz_ultra.py --url "..." --product Claude --model claude-sonnet-4-5
# 输出: output/questions.html + output/QesWA.md + output/images/

# 批量下载大纲
python func/getSyll.py
# 输出: Courses/{course_name}_{id}/Syll/

# 状态检查
python checkStatus.py
# 输出: Account/Cookie/TODOs/Network/Courses状态

# 清理非白名单文件
python clean.py
# 交互式确认 → 删除
```

## ⚠️ 注意事项

### 安全性

1. **API密钥**: 不要硬编码，使用account_config.json
2. **敏感文件**: 已加入.gitignore (cookies.json, account_config.json, personal_info.json, *.json)
3. **TOTP密钥**: 妥善保管otp_key，泄露等同于泄露2FA

### 学术诚信

本工具仅供学习研究使用。使用前请确保：
- 了解学校关于AI辅助学习的政策
- 理解自动生成的答案内容
- 不违反课程Honor Code
- 对提交内容负责

### 技术限制

1. **Cookie有效期**: 24小时自动过期，需要重新登录
2. **API配额**: Gemini/Claude有每日请求限制
3. **Quiz限制**: 只支持选择题，不支持填空/简答
4. **图片识别**: 依赖AI视觉能力，复杂图表可能识别不准

## 🔗 依赖项

```
PyQt6>=6.6.0
Selenium>=4.15.0
webdriver-manager>=4.0.0
requests>=2.31.0
lxml>=4.9.0
beautifulsoup4>=4.12.0
html2text>=2020.1.16
markdown>=3.5.0
python-docx>=1.1.0
Pillow>=10.1.0
google-generativeai>=0.3.0
anthropic>=0.18.0
pyotp>=2.9.0
```

## 📝 开发指南

### 添加新功能

1. **GUI添加按钮**: 编辑`gui/ui/*.ui` (Qt Designer)
2. **绑定回调**: `gui/qt.py:init_button_bindings()`
3. **实现逻辑**:
   - 短操作 → `gui/qt_interact.py`直接实现
   - 长操作 → `func/`新建模块 + 线程调用
4. **测试**: GUI + CLI双模式测试

### 调试技巧

1. **Console标签**: 每个长操作都有独立console输出
2. **Debug按钮**: AutoDetail窗口 → 在独立进程运行脚本
3. **错误截图**: Selenium失败时自动保存error_screenshot.png
4. **日志**: 所有API调用打印到控制台

### 代码规范

- 所有路径使用`config.py`定义
- 线程函数必须接受`console`参数 (可选)
- GUI函数避免使用`input()` (改用QMessageBox)
- 文件操作使用`os.makedirs(exist_ok=True)`

## 📜 许可

MIT License - 仅供学习研究使用
