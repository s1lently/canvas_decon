# GUI 重构计划 - 从 34 文件到 9 文件

> 目标：Python 风格的简单 GUI，一个页面一个文件

---

## 当前问题

```
gui/ (34 .py 文件, 7341 行)
├── qt.py                    306行  路由
├── init.py                  271行  初始化
├── processors.py            227行  内容处理
├── base_handler.py           57行  基类
├── handlers/               2099行  7个handler (过度拆分)
├── core/                    594行  4个manager
├── details/                 456行  2个manager
├── widgets/                2314行  8个widget
├── learn/                   949行  3个文件
└── config/                   53行  2个配置
```

**核心问题：**
1. `wgtAutoDetailModern.py` 992行 - 50%是CSS，应该分离
2. 重复颜色定义 - `COLORS` 字典出现2次
3. Handler 假解耦 - 全部 `self.app.xxx`，不是真正的分离
4. 太多间接层 - qt.py → handler → manager → processor

---

## 目标结构

```
gui/ (9 .py 文件, ~6500 行)
├── app.py           ~500行  主应用 + 信号 + 路由
├── main_view.py     ~350行  主页面 + Launcher
├── auto_view.py     ~450行  自动化列表页
├── detail_view.py   ~700行  作业/测验详情 (最复杂的页面)
├── course_view.py   ~500行  课程详情
├── settings.py      ~300行  设置页
├── widgets.py       ~800行  共用控件 (Sidebar, Toggle, Toast, Delegates)
├── learn.py         ~700行  学习模块
├── styles.py        ~200行  样式 + 颜色
└── ui/              保留 .ui 文件
```

---

## 详细合并映射

### 1. app.py (~500行)
**合并来源：**
- `qt.py` (306行) - 主类 CanvasApp
- `init.py` (271行) - UIInitializer, SignalInitializer
- `base_handler.py` (57行) - 删除，不需要基类

**内容：**
```python
# app.py
class CanvasApp(QMainWindow):
    # 信号定义
    # __init__: 加载UI + 初始化
    # 页面切换方法
    # 全局事件处理
```

### 2. main_view.py (~350行)
**合并来源：**
- `handlers/main.py` (221行) - 主页面逻辑
- `handlers/launcher.py` (88行) - Launcher 逻辑
- `core/mgrData.py` (80行) - 数据加载
- `core/mgrDone.py` (43行) - Done 状态管理

**内容：**
```python
# main_view.py
class MainView:
    def __init__(self, app): ...
    def show_launcher(self): ...
    def on_category_changed(self): ...
    def on_item_double_clicked(self): ...
    # 包含数据加载和状态管理
```

### 3. auto_view.py (~450行)
**合并来源：**
- `handlers/automation.py` (131行) - 自动化列表
- `handlers/keyboard.py` (198行) - 键盘导航 (提取相关部分)

**内容：**
```python
# auto_view.py
class AutoView:
    def __init__(self, app): ...
    def populate_tabs(self): ...  # 4个tab
    def on_item_double_clicked(self): ...
    def handle_keyboard(self, event): ...
```

### 4. detail_view.py (~700行) ⭐最复杂
**合并来源：**
- `handlers/auto_detail.py` (539行) - 详情页handler
- `details/mgrAutoDetail.py` (197行) - HTML生成
- `widgets/wgtAutoDetailModern.py` (992行) → 精简到 ~300行
  - CSS 移到 styles.py
  - 只保留 UI 布局

**内容：**
```python
# detail_view.py
class DetailView(QWidget):
    # UI 布局 (从 wgtAutoDetailModern 简化)
    def __init__(self): ...
    def set_todo(self, todo): ...
    def on_again_clicked(self): ...
    def on_submit_clicked(self): ...
    def update_preview(self): ...
    def _generate_info_html(self): ...  # 从 mgrAutoDetail 移入
```

### 5. course_view.py (~500行)
**合并来源：**
- `handlers/course_detail.py` (622行) - 课程详情handler
- `details/mgrCourseDetail.py` (259行) - 课程数据管理
- `processors.py` (227行) - HTMLProcessor, TabLoader (相关部分)

**内容：**
```python
# course_view.py
class CourseView:
    def __init__(self, app): ...
    def set_course(self, course): ...
    def on_category_changed(self): ...
    def load_tab_content(self): ...
    def on_decon_textbook(self): ...
```

### 6. settings.py (~300行)
**合并来源：**
- `handlers/sitting.py` (300行) - 设置handler
- `core/mgrTask.py` (98行) - 任务管理 (相关部分)

**内容：**
```python
# settings.py
class SettingsView:
    def __init__(self, app): ...
    def show(self): ...
    def save_account(self): ...
    def save_api_key(self): ...
    def refresh_tasks(self): ...
```

### 7. widgets.py (~800行)
**合并来源：**
- `widgets/wgtSidebar.py` (327行) - 侧边栏
- `widgets/wgtMissionControl.py` (422行) - 任务控制
- `widgets/wgtIOSToggle.py` (99行) - 开关
- `widgets/wgtProgress.py` (100行) - 进度条
- `widgets/rdrToast.py` (188行) - 通知
- `widgets/rdrDelegates.py` (186行) - 列表渲染

**内容：**
```python
# widgets.py
class Sidebar(QWidget): ...
class MissionControl(QWidget): ...
class IOSToggle(QWidget): ...
class ProgressWidget(QWidget): ...
class Toast: ...
class TodoItemDelegate(QStyledItemDelegate): ...
```

### 8. learn.py (~700行)
**合并来源：**
- `learn/rdrLearnSitting.py` (641行) - 学习widget
- `learn/cfgLearnPrefs.py` (234行) - 学习偏好
- `learn/utilFormatters.py` (74行) - 格式化

**内容：**
```python
# learn.py
class LearnPreferences: ...
class LearnWidget(QWidget): ...
def format_course(course): ...
def format_todo(todo): ...
```

### 9. styles.py (~200行)
**合并来源：**
- `config/cfgStyles.py` (30行)
- `config/cfgModel.py` (23行) → 移到 app.py
- 从 `wgtAutoDetailModern.py` 提取的 CSS (~150行)
- 统一 COLORS 定义

**内容：**
```python
# styles.py
COLORS = {
    'bg_primary': '#0a0a0a',
    'bg_secondary': '#111111',
    # ... 统一颜色定义
}

DETAIL_VIEW_CSS = """..."""
MISSION_CONTROL_CSS = """..."""

def get_button_style(color): ...
```

---

## 执行步骤

### Phase 1: 准备工作 (30分钟)
1. [ ] 创建 `styles.py` - 提取所有颜色和CSS
2. [ ] 备份当前 gui/ 目录

### Phase 2: 核心合并 (2-3小时)
3. [ ] 创建 `app.py` - 合并 qt.py + init.py
4. [ ] 创建 `main_view.py` - 合并主页面相关
5. [ ] 创建 `auto_view.py` - 合并自动化页面
6. [ ] 创建 `detail_view.py` - 最复杂，需要仔细合并
7. [ ] 创建 `course_view.py` - 合并课程详情
8. [ ] 创建 `settings.py` - 合并设置

### Phase 3: 收尾 (1小时)
9. [ ] 创建 `widgets.py` - 合并所有小组件
10. [ ] 创建 `learn.py` - 合并学习模块
11. [ ] 删除旧文件和目录
12. [ ] 测试运行

---

## 风险控制

1. **每合并一个文件后测试** - `python -c "from gui.xxx import *"`
2. **保留旧文件直到确认** - 用 `_old/` 目录暂存
3. **业务逻辑不变** - 只是文件重组，不改功能

---

## 预期结果

| 指标 | 当前 | 目标 |
|-----|------|------|
| 文件数 | 34 | 9 |
| 目录数 | 10 | 1 |
| 总行数 | 7341 | ~6500 |
| 最大文件 | 992行 | ~700行 |

**核心收益：**
- 找代码只需看 9 个文件
- 一个页面一个文件，直观
- 没有假解耦，简单直接
