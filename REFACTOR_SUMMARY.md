# Refactor Summary (2025-12-01)

## Phase 1: Flatten gui/qt_utils/

**Before:**
```
gui/qt_utils/
├── window_handlers/   (7 files)
├── event_handlers/    (1 file)
├── content_processors/(3 files)
├── initializers/      (2 files)
└── base_handler.py
```

**After:**
```
gui/
├── handlers/          (7 files, short names)
├── processors.py      (merged 3 → 1)
├── init.py            (merged 2 → 1)
└── base_handler.py
```

**Changes:**
- Removed 4 directories
- Merged content_processors/* → processors.py (256→227 lines)
- Merged initializers/* → init.py (383→271 lines)
- Renamed handlers to short names (e.g., main_window_handler.py → main.py)
- Net: -166 lines

---

## Phase 2: Merge func/ AI Modules

**Before:**
```
func/
├── utilModels.py       (149 lines) - Model listing
└── utilPromptFiles.py  (162 lines) - AI API calls
```

**After:**
```
func/
└── ai.py               (189 lines) - Combined
```

**Changes:**
- Merged 2 files into 1
- Net: -123 lines

---

## Current Structure

```
canvas_decon/
├── config.py           # Global config
├── main.py             # Entry point
├── core/               # Core utilities (4 files)
│   ├── exceptions.py
│   ├── security.py
│   ├── canvas_api.py
│   └── log.py
├── func/               # Business logic (13 files)
│   ├── ai.py           # NEW: AI model + API
│   ├── getTodos.py
│   ├── getHomework.py
│   ├── getQuiz_ultra.py
│   └── ...
└── gui/                # UI layer
    ├── qt.py           # Main app
    ├── init.py         # NEW: Initializers merged
    ├── processors.py   # NEW: Content processors merged
    ├── handlers/       # NEW: Flattened handlers
    ├── core/
    ├── details/
    ├── widgets/
    ├── learn/
    └── config/
```

---

## Stats

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| gui/ directories | 10+ | 7 | -30% |
| func/ files | 16 | 14 | -12% |
| Total lines removed | - | - | ~289 |

---

## Not Changed (Preserved)

- **Business logic**: getHomework, getQuiz_ultra, getTodos - 完全保留
- **Login flow**: getCookie, getTotp - 不变
- **sys.path.insert**: 保留向后兼容 (32处)
  - 若要移除，需 `pip install -e .`

---

## Next Steps (Optional)

1. **Further simplification:**
   - Merge gui/core/ + gui/details/ → gui/managers/
   - Merge gui/config/ → gui/styles.py

2. **Clean imports:**
   - Run `pip install -e .` then remove sys.path.insert

3. **Replace print() → log:**
   - Use `from core.log import log`
