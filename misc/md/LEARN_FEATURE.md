# Learn功能 - 完整实现文档

**实现日期：** 2025-10-15
**功能描述：** AI驱动的学习材料分析系统，支持多种文件类型自动生成学习报告

---

## 📋 功能概述

### 核心功能
1. **Load From Decon** - 从Textbook/decon/加载章节PDF到Learn目录
2. **Learn This Material** - 使用AI分析文件并生成markdown学习报告
3. **拖拽支持** - 支持直接拖拽文件到Learn类别
4. **智能排序** - 文件按自然排序显示（Chapter_1, Chapter_2, ...）
5. **状态指示** - 已生成报告的文件显示✅图标
6. **自动刷新** - 完成IO操作后自动重绘UI

---

## 📁 新增文件

### 1. `func/learn_material.py` (主模块)

**功能：** 处理各种文件类型并生成学习报告

**支持的文件类型：**

| 类型 | 扩展名 | AI模型 | 处理方式 |
|------|--------|--------|----------|
| 文本文件 | .py, .js, .java, .cpp, .c, .go, .rs, .txt, .md, .json, .xml, .html, .css | Claude (最新) | 直接分析代码/文本 |
| Excel | .xlsx | - | 转换为CSV → Gemini |
| Word | .docx | - | 转换为PDF → Gemini |
| PowerPoint | .pptx | - | 转换为PDF → Gemini |
| PDF | .pdf | Gemini (最新) | 直接上传分析 |
| CSV | .csv | Gemini (最新) | 直接上传分析 |

**核心函数：**

```python
def learn_material(file_path, course_dir, console=None):
    """主入口：分析任何学习材料并生成markdown报告

    返回：
        报告路径 (Learn/reports/filename.md) 或 None
    """

def load_from_decon(course_dir, console=None):
    """从Textbook/decon/加载所有章节PDF到Learn/

    返回：
        复制的文件路径列表
    """

def process_text_file(file_path, output_md_path, console=None):
    """使用Claude分析文本文件"""

def process_pdf_or_csv(file_path, output_md_path, console=None):
    """使用Gemini分析PDF/CSV"""

def convert_office_to_pdf(file_path, console=None):
    """转换Office文件为PDF/CSV"""
```

---

## 🔧 修改的文件

### 1. `gui/ui/course_detail.ui`

**新增按钮（第102-127行）：**
```xml
<widget class="QPushButton" name="loadFromDeconBtn">
    <property name="minimumSize">
        <width>140</width>
        <height>30</height>
    </property>
</widget>

<widget class="QPushButton" name="learnMaterialBtn">
    <property name="minimumSize">
        <width>150</width>
        <height>30</height>
    </property>
</widget>
```

---

### 2. `gui/course_detail_manager.py`

**新增类别（第41行）：**
```python
cats = ['Learn', 'Introduction', 'Homework (Upcoming)', ...]
```

**新增方法：**
```python
def _get_learn(self):
    """获取Learn目录中的文件，按自然排序

    返回格式：
    [{
        'name': 'Chapter_1.pdf',
        'type': 'learn_file',
        'has_file': True,
        'has_report': True/False,
        'data': {
            'filename': 'Chapter_1.pdf',
            'path': '/full/path/to/file',
            'folder': '/Learn/dir',
            'report_path': '/Learn/reports/Chapter_1.md' (如果存在)
        }
    }]
    """

def get_learn_dir(self):
    """返回Learn目录路径"""
```

**自然排序实现（第176-181行）：**
```python
import re
def natural_sort_key(s):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

for filename in sorted(files, key=natural_sort_key):
    # Chapter_1, Chapter_2, ..., Chapter_10 (正确顺序)
```

---

### 3. `gui/qt.py`

**新增信号类（第23-24行）：**
```python
class CourseDetailSignal(QObject):
    refresh_category = pyqtSignal()
```

**初始化信号（第36-37行）：**
```python
self.course_detail_signal = CourseDetailSignal()
self.course_detail_signal.refresh_category.connect(self._refresh_current_category)
```

**新增刷新方法（第1365-1371行）：**
```python
def _refresh_current_category(self):
    """刷新CourseDetail当前类别"""
    if not self.course_detail_mgr: return
    cdw = self.course_detail_window
    current_row = cdw.categoryList.currentRow()
    if current_row >= 0:
        self.on_course_detail_category_changed(current_row)
```

**按钮绑定（第262-263行）：**
```python
cdw.loadFromDeconBtn.clicked.connect(lambda: qt_interact.on_load_from_decon_clicked(self))
cdw.learnMaterialBtn.clicked.connect(lambda: qt_interact.on_learn_material_clicked(self))
```

**拖拽支持（第545-573行）：**
```python
def _course_item_drop(self, event):
    """支持拖拽到Textbook或Learn类别"""
    category_text = current_category.text()

    if category_text not in ['Textbook', 'Learn']:
        QMessageBox.warning(...)
        return

    # 获取目标目录
    if category_text == 'Textbook':
        target_dir = self.course_detail_mgr.get_textbook_dir()
    else:  # Learn
        target_dir = self.course_detail_mgr.get_learn_dir()

    # 复制文件
    shutil.copy2(file_path, dest_path)
```

**Learn文件显示（第678-680行）：**
```python
'learn_file': lambda: f"<h2 style='color: #3b82f6;'>📚 {data['filename']}</h2>" +
                     f"<p><strong>Path:</strong> {data['path']}</p>" +
                     (f"<p><strong>Report:</strong> <a href='file://{data['report_path']}'>{...}</a> ✅</p>"
                      if data.get('report_path') else
                      "<p><strong>Report:</strong> Not generated yet. Click 'Learn This Material' to generate.</p>"),
```

**Learn类别使用FileItemDelegate（第661行）：**
```python
cdw.itemList.setItemDelegate(delegates.FileItemDelegate(cdw.itemList)
    if category in ['Syllabus', 'Textbook', 'Learn'] else QStyledItemDelegate())
```

---

### 4. `gui/qt_interact.py`

**线程安全Console（第8-21行）：**
```python
class ThreadSafeConsole:
    """线程安全的QTextEdit wrapper"""
    def __init__(self, console_widget):
        self.console = console_widget

    def append(self, text):
        """使用QMetaObject.invokeMethod确保在主线程执行"""
        QMetaObject.invokeMethod(
            self.console,
            "append",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, str(text))
        )
```

**更新_create_console_tab（第23-48行）：**
```python
def _create_console_tab(tw, name, with_progress=False):
    """返回ThreadSafeConsole wrapper"""
    if with_progress:
        console_widget, progress_widget = create_console_with_progress(tw, name)
        return ThreadSafeConsole(console_widget), progress_widget
    else:
        # ... 创建console
        return ThreadSafeConsole(console)
```

**新增处理函数：**

```python
def on_load_from_decon_clicked(canvas_app):
    """Load From Decon按钮处理

    流程：
    1. 在主线程提取数据和创建console
    2. 启动worker thread执行load_from_decon()
    3. 完成后emit信号触发UI刷新
    """
    # 主线程：提取数据
    course_dir = canvas_app.course_detail_mgr.course_dir
    course_name = canvas_app.course_detail_mgr.get_course_name()

    # 主线程：创建console
    console = _create_console_tab(canvas_app.main_window.consoleTabWidget, "Load From Decon")

    def run(console):
        # Worker线程：执行IO
        copied_files = load_from_decon(course_dir, console)

        if copied_files:
            console.append(f"\n✅ Successfully loaded {len(copied_files)} chapters")
            # 触发UI刷新（线程安全）
            canvas_app.course_detail_signal.refresh_category.emit()

    _run_in_thread(run, console, "Load From Decon")


def on_learn_material_clicked(canvas_app):
    """Learn This Material按钮处理

    流程：
    1. 检查是否选中Learn文件
    2. 在主线程提取数据和创建console
    3. 启动worker thread执行learn_material()
    4. 完成后emit信号触发UI刷新
    """
    # 检查选中项
    current_item = cdw.itemList.currentItem()
    if not current_item:
        QMessageBox.warning(...)
        return

    # 获取数据（UserRole + 1）
    item_data = current_item.data(Qt.ItemDataRole.UserRole + 1)
    if not item_data or item_data.get('type') != 'learn_file':
        QMessageBox.warning(...)
        return

    # 主线程：提取数据和创建console
    file_path = item_data['data']['path']
    console = _create_console_tab(...)

    def run(console):
        # Worker线程：执行AI分析
        report_path = learn_material(file_path, course_dir, console)

        if report_path:
            console.append("✅ Learning report generated!")
            # 显示预览
            console.append(report_content[:1000])
            # 触发UI刷新
            canvas_app.course_detail_signal.refresh_category.emit()

    _run_in_thread(run, console, f"Learn: {filename}")
```

---

### 5. `func/model_selector.py`

**新增函数（第57-106行）：**
```python
def get_best_anthropic_model(api_key=None):
    """获取最佳Claude模型

    优先级：sonnet-4 > opus-3 > sonnet-3.5

    返回：
        'claude-sonnet-4-20250514' (或最新可用模型)
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        models = client.models.list()

        claude_models = [m.id for m in models.data if m.id.startswith('claude-')]

        best_model = sorted(
            claude_models,
            key=lambda x: ('sonnet-4' in x, 'opus-3' in x, 'sonnet-3.5' in x),
            reverse=True
        )[0]

        return best_model
    except:
        return 'claude-sonnet-4-20250514'  # Fallback
```

---

## 📂 目录结构

```
Courses/
└── 课程名/
    ├── Learn/                    # 新增：学习材料目录
    │   ├── Chapter_1.pdf         # 拖拽或Load From Decon的文件
    │   ├── Chapter_2.pdf
    │   ├── model_selector.py     # 可以拖拽代码文件
    │   └── reports/              # 自动创建
    │       ├── Chapter_1.md      # AI生成的学习报告
    │       ├── Chapter_2.md
    │       └── model_selector.md
    ├── Files/
    │   └── Textbook/
    │       └── decon/            # Decon Textbook生成的章节
    │           ├── Chapter_1.pdf
    │           └── Chapter_2.pdf
    └── Syll/
```

---

## 🔄 工作流程

### 流程1: Load From Decon

```
用户点击 "Load From Decon"
    ↓
on_load_from_decon_clicked (主线程)
    ├─ 提取 course_dir, course_name
    ├─ 创建 ThreadSafeConsole
    └─ 启动 worker thread
        ↓
load_from_decon (worker thread)
    ├─ 查找 Textbook/decon/*.pdf
    ├─ 复制到 Learn/
    └─ 返回文件列表
        ↓
emit refresh_category.emit() (worker thread)
    ↓ (Qt自动切换到主线程)
_refresh_current_category (主线程)
    ↓
on_course_detail_category_changed
    ↓
✅ UI刷新，显示新文件
```

### 流程2: Learn This Material

```
用户选中文件 → 点击 "Learn This Material"
    ↓
on_learn_material_clicked (主线程)
    ├─ 检查选中项
    ├─ 提取 file_path, course_dir
    ├─ 创建 ThreadSafeConsole
    └─ 启动 worker thread
        ↓
learn_material (worker thread)
    ├─ 检测文件类型
    ├─ 文本文件 → process_text_file (Claude)
    ├─ Office文件 → convert → process_pdf_or_csv (Gemini)
    └─ PDF/CSV → process_pdf_or_csv (Gemini)
        ↓
    AI分析 → 生成markdown报告
        ↓
    保存到 Learn/reports/filename.md
        ↓
emit refresh_category.emit()
    ↓
✅ UI刷新，显示✅图标
```

---

## 🐛 问题修复记录

### 问题1: AttributeError - item_data是bool

**错误：**
```python
AttributeError: 'bool' object has no attribute 'get'
```

**原因：**
使用了错误的UserRole
- `Qt.ItemDataRole.UserRole` = has_file (bool)
- `Qt.ItemDataRole.UserRole + 1` = item_data (dict)

**修复：**
```python
# ❌ 错误
item_data = current_item.data(Qt.ItemDataRole.UserRole)

# ✅ 正确
item_data = current_item.data(Qt.ItemDataRole.UserRole + 1)
```

---

### 问题2: Segmentation Fault (跨线程UI操作)

**错误：**
```
QObject: Cannot create children for a parent that is in a different thread.
zsh: segmentation fault
```

**原因：**
1. 在worker thread中访问`canvas_app.main_window.consoleTabWidget`创建console
2. 在worker thread中直接调用`console.append()`修改QTextEdit

**修复方案：**

1. **创建ThreadSafeConsole wrapper**
```python
class ThreadSafeConsole:
    def append(self, text):
        QMetaObject.invokeMethod(
            self.console, "append",
            Qt.ConnectionType.QueuedConnection,  # 确保在主线程执行
            Q_ARG(str, str(text))
        )
```

2. **在主线程创建所有UI对象**
```python
# ✅ 正确：主线程创建console
console = _create_console_tab(canvas_app.main_window.consoleTabWidget, name)

def run(console):
    # worker thread只调用console.append()
    console.append("message")

_run_in_thread(run, console, name)
```

---

### 问题3: 完成后不刷新UI

**问题：**
Load From Decon和Learn完成后，需要手动切换category才能看到新文件/报告

**修复：**

1. **添加信号类**
```python
class CourseDetailSignal(QObject):
    refresh_category = pyqtSignal()
```

2. **连接刷新方法**
```python
self.course_detail_signal.refresh_category.connect(self._refresh_current_category)

def _refresh_current_category(self):
    current_row = cdw.categoryList.currentRow()
    if current_row >= 0:
        self.on_course_detail_category_changed(current_row)
```

3. **worker完成后emit**
```python
# 在worker thread中安全调用
canvas_app.course_detail_signal.refresh_category.emit()
```

---

### 问题4: 文件排序错误

**问题：**
```
Chapter_1.pdf
Chapter_10.pdf  ← 错误位置
Chapter_2.pdf
```

**修复：**
```python
def natural_sort_key(s):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

for filename in sorted(files, key=natural_sort_key):
    # Chapter_1, Chapter_2, ..., Chapter_10 ✅
```

---

## 🎯 测试清单

- [x] 拖拽文件到Learn类别
- [x] Load From Decon按钮
- [x] Learn This Material按钮
- [x] 文本文件 (.py) → Claude分析
- [x] PDF文件 → Gemini分析
- [x] 完成后自动刷新UI
- [x] 报告✅图标显示
- [x] 文件自然排序
- [x] 线程安全（无Segmentation Fault）

---

## 📊 性能特点

| 操作 | 线程 | AI调用 | 刷新方式 |
|------|------|--------|----------|
| Load From Decon | Worker | 无 | 信号自动刷新 |
| Learn (文本) | Worker | Claude (最新) | 信号自动刷新 |
| Learn (PDF) | Worker | Gemini (最新) | 信号自动刷新 |
| 拖拽文件 | 主线程 | 无 | 立即刷新 |

---

## 🔮 未来优化

1. ✅ 支持批量Learn（选中多个文件）
2. ✅ 报告缓存（避免重复生成）
3. ✅ Markdown预览（在detailView中渲染HTML）
4. ✅ 进度条显示（AI分析进度）

---

**文档版本：** 1.0
**最后更新：** 2025-10-15
