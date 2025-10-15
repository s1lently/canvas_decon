# GUI文件命名规范化总结

## 重构完成时间
2025-10-15

## 命名规范

### 3字母前缀系统
| 前缀 | 含义 | 示例 |
|------|------|------|
| `mgr` | Manager 管理器 | `mgrData.py` |
| `rdr` | Renderer 渲染器/UI组件 | `rdrToast.py` |
| `wgt` | Widget 组件 | `wgtIOSToggle.py` |
| `util` | Utility 工具类 | `utilFormatters.py` |
| `cfg` | Config 配置类 | `cfgStyles.py` |

## 重命名清单

### Managers (5个)
- `auto_detail_manager.py` → `mgrAutoDetail.py`
- `course_detail_manager.py` → `mgrCourseDetail.py`
- `data_manager.py` → `mgrData.py`
- `done_manager.py` → `mgrDone.py`
- `task_manager.py` → `mgrTask.py`

### Renderers (3个)
- `delegates.py` → `rdrDelegates.py`
- `learn_sitting_renderer.py` → `rdrLearnSitting.py`
- `toast_notification.py` → `rdrToast.py`

### Widgets (2个)
- `ios_toggle.py` → `wgtIOSToggle.py`
- `progress_widget.py` → `wgtProgress.py`

### Utils (2个)
- `formatters.py` → `utilFormatters.py`
- `qt_interact.py` → `utilQtInteract.py`

### Config (3个)
- `learn_preferences.py` → `cfgLearnPrefs.py`
- `model_config.py` → `cfgModel.py`
- `styles.py` → `cfgStyles.py`

## 更新的文件 (17个)

### 核心文件
1. `main.py` - 更新 cfgStyles 导入
2. `gui/qt.py` - 更新所有核心导入

### Handler文件 (9个)
3. `gui/qt_utils/initializers/ui_initializer.py`
4. `gui/qt_utils/initializers/signal_initializer.py`
5. `gui/qt_utils/window_handlers/launcher_handler.py`
6. `gui/qt_utils/window_handlers/main_window_handler.py`
7. `gui/qt_utils/window_handlers/automation_window_handler.py`
8. `gui/qt_utils/window_handlers/course_detail_window_handler.py`
9. `gui/qt_utils/window_handlers/auto_detail_window_handler.py`
10. `gui/qt_utils/window_handlers/sitting_window_handler.py`
11. `gui/qt_utils/event_handlers/keyboard_handler.py`

### 其他GUI文件 (2个)
12. `gui/utilQtInteract.py`
13. `gui/rdrLearnSitting.py`

## 导入示例

### 旧方式 (已废弃)
```python
from gui.data_manager import DataManager
from gui import formatters
from gui.toast_notification import show_toast
```

### 新方式 (当前)
```python
from gui.mgrData import DataManager
from gui import utilFormatters
from gui.rdrToast import show_toast
```

## 优势

1. **一眼识别类型** - 通过前缀立即知道模块功能
2. **分类清晰** - 5种类型覆盖所有GUI组件
3. **统一风格** - 与func/目录的getXxx风格一致
4. **易于维护** - 新文件可快速归类

## 测试结果

✅ 所有导入测试通过  
✅ 完整应用启动测试通过  
✅ Handler加载验证通过  

**总计：15个文件重命名 + 17个文件导入更新**
