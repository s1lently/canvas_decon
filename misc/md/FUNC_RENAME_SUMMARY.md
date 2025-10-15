# func/ 目录命名规范化总结

## 重构完成时间
2025-10-15

## 命名规范

### 前缀系统
| 前缀 | 含义 | 示例 |
|------|------|------|
| `getXxx` | 获取/抓取数据 | `getTodos.py` |
| `procXxx` | 处理/加工数据 | `procLearnMaterial.py` |
| `mgrXxx` | 管理器 | `mgrHistory.py` |
| `utilXxx` | 工具函数 | `utilPromptFiles.py` |

## 重命名清单

### 保持不变 (getXxx规范, 7个)
- `getCourses.py` ✓
- `getHistoryTodos.py` ✓
- `getHomework.py` ✓
- `getQuiz_ultra.py` ✓
- `getSyll.py` ✓
- `getTodos.py` ✓
- `__init__.py` ✓

### 已重命名 (6个)
- `history_manager.py` → `mgrHistory.py`
- `learn_material.py` → `procLearnMaterial.py`
- `model_selector.py` → `utilModelSelector.py`
- `pdf_bookmark_extractor.py` → `utilPdfBookmark.py`
- `pdf_splitter.py` → `utilPdfSplitter.py`
- `upPromptFiles.py` → `utilPromptFiles.py`

### 废弃文件 (9个 - 已移除)
整个 `func/util/` 目录移至 `misc/old/func/util_deprecated/`：
- `ask_with_pdf.py`
- `gCO.py`
- `getAPI.py`
- `getAss.py`
- `getHTML.py`
- `getQuiz_short.py`
- `gqu.py`
- `sel_test.py`
- `stQz.py`

## 更新的文件 (9个)

### func/目录内部 (3个)
1. `func/getHomework.py` - 更新 utilPromptFiles 导入
2. `func/getQuiz_ultra.py` - 更新 utilPromptFiles 导入
3. `func/getHistoryTodos.py` - 更新 mgrHistory 导入
4. `func/procLearnMaterial.py` - 更新 utilModelSelector, utilPromptFiles 导入

### gui/目录引用 (5个)
5. `gui/qt_utils/window_handlers/course_detail_window_handler.py` - 更新4个util导入
6. `gui/qt_utils/window_handlers/main_window_handler.py` - 更新 mgrHistory 导入
7. `gui/rdrLearnSitting.py` - 更新 procLearnMaterial 导入
8. `gui/utilQtInteract.py` - 更新 procLearnMaterial, cfgLearnPrefs 导入
9. `gui/qt_utils/initializers/ui_initializer.py` - 更新 mgrHistory 导入
10. `gui/cfgLearnPrefs.py` - 更新 utilModelSelector 导入

## 导入示例

### 旧方式 (已废弃)
```python
from func import upPromptFiles
from func.history_manager import load_history
from func.learn_material import batch_learn_from_files
```

### 新方式 (当前)
```python
from func import utilPromptFiles
from func.mgrHistory import load_history
from func.procLearnMaterial import batch_learn_from_files
```

## func/ 最终结构

```
func/
├── __init__.py
│
├── getXxx.py (6个) - 数据获取
│   ├── getCourses.py
│   ├── getHistoryTodos.py
│   ├── getHomework.py
│   ├── getQuiz_ultra.py
│   ├── getSyll.py
│   └── getTodos.py
│
├── procXxx.py (1个) - 数据处理
│   └── procLearnMaterial.py
│
├── mgrXxx.py (1个) - 管理器
│   └── mgrHistory.py
│
└── utilXxx.py (4个) - 工具函数
    ├── utilModelSelector.py
    ├── utilPdfBookmark.py
    ├── utilPdfSplitter.py
    └── utilPromptFiles.py
```

## 优势

1. **统一前缀规范** - getXxx/procXxx/mgrXxx/utilXxx 清晰分类
2. **移除冗余代码** - 删除9个未使用的util工具文件
3. **易于理解** - 文件名立即表明功能类型
4. **便于维护** - 新文件可快速归类到对应前缀

## 测试结果

✅ 所有6个重命名模块导入测试通过  
✅ 所有getXxx模块导入测试通过  
✅ 跨模块引用测试通过  
✅ GUI与func交叉导入测试通过  
✅ func/util/ 已成功移除  

**总计：6个文件重命名 + 9个文件移除 + 10个文件导入更新**
