# GEMINI.md - Agent Context & Workspace

This file serves as a persistent context and scratchpad for Gemini agents working on the `canvas_decon` project. It tracks recent changes, ongoing tasks, and architectural notes.

## 📅 Last Updated
**Date:** November 21, 2025
**Agent:** Gemini

## 🔄 Recent Changes (Uncommitted / In-Progress)

### 1. Concurrent Data Fetching (Massive Speedup)
- **`func/getTodos.py`**: Refactored to use `concurrent.futures.ThreadPoolExecutor` (20 workers) for fetching assignment details and downloading files.
  - Added `get_todos_concurrent` and `process_and_save_todos_concurrent`.
  - Improved planner item fetching with parallel page probes.
- **`func/getHistoryTodos.py`**: Also updated to use concurrency (10-20 workers) for fetching graded submissions and converting them.
  - Implemented smarter pagination detection (probing 'last' link).

### 2. Robust AI Status Feedback
- **`func/utilPromptFiles.py`**: Added `status_callback` parameter to `call_ai` and `_gemini`.
  - Now pipes "429 Rate Limit" warnings directly to the GUI console via callback.
  - Improved 429 error detection (string matching + code check).
- **`gui/.../course_detail_window_handler.py`**: Updated to pass `console.append` as the status callback during textbook processing.

## 🔄 Recent Commits (Nov 2025)

### 1. Robust API Handling & Config Hot-Reload (Commit `13e2b5f`)
- **Retry Logic:** Implemented `tenacity` (or similar logic) for handling `429 Too Many Requests`.
- **Context Optimization:** Reduced PDF context size.

### 2. UI/UX Fixes (Oct 2025)
- **Drag-and-Drop:** Fixed in `Textbook` tab (`DropListWidget`).
- **HTML Formatters:** Refactored for readability.

## 🛠️ Current Architecture Notes

- **Entry Point:** `main.py` -> `gui/qt.py`
- **Concurrency:** Moving from simple threads to `ThreadPoolExecutor` for IO-bound tasks (Canvas API is slow!).
- **AI Interface:** Unified in `utilPromptFiles.py`.

## 📝 Todo / Upcoming Tasks

- [ ] **Commit Changes:** The concurrent refactors in `getTodos.py` and `getHistoryTodos.py` are currently *uncommitted*.
- [ ] **Verify functionality:** Ensure the new concurrent fetching doesn't trigger Canvas rate limits (429) too aggressively.
- [ ] **Codebase cleanup:** Check for unused files in `misc/old/`.

## 💡 Tips for Future Agents

- **Git History:** Check `git log` AND `git diff`! Significant work might be uncommitted.
- **Testing:** Run `python func/getTodos.py` to test the new concurrent fetcher in CLI mode.