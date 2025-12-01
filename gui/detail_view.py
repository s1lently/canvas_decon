"""Detail View - AutoDetail Window Handler (merged from handlers/auto_detail.py + details/mgrAutoDetail.py)"""
import sys, os, json, threading, re, base64
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from gui._internal import cfgModel as model_config
from gui.styles import COLORS as C


class DetailView:
    """Handles AutoDetail window operations"""

    def __init__(self, app):
        self.app = app
        self.adw = app.auto_detail_window
        self._quiz_status_timer = None
        self._current_quiz_url = None

    @property
    def mgr(self):
        return self.app.auto_detail_mgr

    # === QUIZ STATUS TIMER ===
    def start_quiz_timer(self, url):
        """Start quiz status polling (500ms)"""
        if self._quiz_status_timer is None:
            self._quiz_status_timer = QTimer()
            self._quiz_status_timer.setInterval(500)
            self._quiz_status_timer.timeout.connect(self._fetch_quiz_status)

        self._current_quiz_url = url
        if not self._quiz_status_timer.isActive():
            self._fetch_quiz_status()
            self._quiz_status_timer.start()

    def stop_quiz_timer(self):
        """Stop quiz status polling"""
        if self._quiz_status_timer and self._quiz_status_timer.isActive():
            self._quiz_status_timer.stop()
        self._current_quiz_url = None

    def _fetch_quiz_status(self):
        """Fetch quiz status in background"""
        if not self._current_quiz_url:
            return

        url = self._current_quiz_url

        def fetch():
            try:
                from func.getQuizStatus import get_quiz_status
                status = get_quiz_status(url)
                self.app.signals.quiz_status_update.emit(status)
            except Exception as e:
                print(f"[QuizStatus] Error: {e}")

        threading.Thread(target=fetch, daemon=True).start()

    def update_quiz_status_bar(self, status):
        """Update quiz status bar with status data"""
        self.adw.quizStatusBar.setVisible(True)

        if status.get('status') == 'error':
            self.adw.quizScoreLabel.setText(f"Error: {status.get('error', 'Unknown')[:30]}")
            self.adw.quizScoreLabel.setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
            self.adw.quizBestLabel.setText("")
            self.adw.quizAttemptsLabel.setText("")
            self.adw.quizTimeLabel.setText("")
            return

        # Score
        if status.get('current_score') is not None:
            score, total = status['current_score'], status.get('points_possible', 0)
            color = '#22c55e' if score == total else '#60a5fa'
            self.adw.quizScoreLabel.setText(f"Score: {score}/{total}")
            self.adw.quizScoreLabel.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
        else:
            self.adw.quizScoreLabel.setText("Score: --/--")
            self.adw.quizScoreLabel.setStyleSheet("font-size: 14px; font-weight: bold; color: #9ca3af;")

        # Best score
        if status.get('highest_score') is not None and status['highest_score'] != status.get('current_score'):
            self.adw.quizBestLabel.setText(f"Best: {status['highest_score']}")
            self.adw.quizBestLabel.setVisible(True)
        else:
            self.adw.quizBestLabel.setText("")

        # Attempts
        used, allowed, left = status.get('attempts_used', 0), status.get('allowed_attempts', 1), status.get('attempts_left', 0)
        if allowed == -1:
            self.adw.quizAttemptsLabel.setText(f"Attempts: {used}/∞")
            self.adw.quizAttemptsLabel.setStyleSheet("font-size: 13px; color: #22c55e;")
        elif left == 0:
            self.adw.quizAttemptsLabel.setText(f"Attempts: {used}/{allowed} (Done)")
            self.adw.quizAttemptsLabel.setStyleSheet("font-size: 13px; color: #ef4444;")
        else:
            self.adw.quizAttemptsLabel.setText(f"Attempts: {used}/{allowed} ({left} left)")
            self.adw.quizAttemptsLabel.setStyleSheet("font-size: 13px; color: #eab308;")

        # Status indicator
        if status.get('in_progress'):
            if status.get('time_remaining') is not None:
                mins, secs = status['time_remaining'] // 60, status['time_remaining'] % 60
                self.adw.quizTimeLabel.setText(f"In Progress - {mins}:{secs:02d}")
            else:
                self.adw.quizTimeLabel.setText("In Progress")
            self.adw.quizTimeLabel.setStyleSheet("font-size: 13px; font-weight: bold; color: #f59e0b;")
        elif status.get('attempts_used', 0) == 0:
            self.adw.quizTimeLabel.setText("Not Started")
            self.adw.quizTimeLabel.setStyleSheet("font-size: 13px; font-weight: bold; color: #9ca3af;")
        elif left == 0:
            self.adw.quizTimeLabel.setText("Completed")
            self.adw.quizTimeLabel.setStyleSheet("font-size: 13px; font-weight: bold; color: #22c55e;")
        else:
            time_str = f" ({status['time_limit']}min)" if status.get('time_limit') else ""
            self.adw.quizTimeLabel.setText(f"Retryable{time_str}")
            self.adw.quizTimeLabel.setStyleSheet("font-size: 13px; font-weight: bold; color: #eab308;")

    # === POPULATE WINDOW ===
    def populate_window(self):
        """Populate AutoDetail window with TODO data"""
        if not self.mgr:
            return

        info = self._get_identification_info()
        self.adw.courseNameLabel.setText(f"Course: {info['course']}")
        self.adw.assignmentNameLabel.setText(f"Assignment: {info['assignment']}")
        self.adw.typeLabel.setText(f"Type: {info['type']}")
        self.adw.dueDateLabel.setText(f"Due: {info['due_date']}")
        self.adw.assignmentDetailView.setHtml(self._get_assignment_detail_html())
        self.adw.refFilesView.setHtml(self._get_reference_files_html())

        is_quiz, is_homework = self.mgr.is_quiz, self.mgr.is_homework
        self.adw.quizControlWidget.setVisible(is_quiz)
        self.adw.hwControlWidget.setVisible(is_homework)
        self.adw.consoleTitle.setText(f"{info['type']} Automation Console")

        preview_html = self._load_preview()
        self.adw.aiPreviewView.setHtml(preview_html if preview_html else self._get_preview_placeholder_html())
        self.adw.previewStatusLabel.setText("Status: Preview loaded" if preview_html else "Status: No preview generated yet")

        config.ensure_dirs()
        self._ensure_assignment_folder()

        prompt_type = 'quiz' if is_quiz else 'homework'
        self.adw.promptEditBox.setPlainText(config.DEFAULT_PROMPTS.get(prompt_type, ''))

        # Quiz status bar
        if is_quiz:
            url = self.mgr.todo.get('redirect_url') or self.mgr.todo.get('assignment', {}).get('html_url')
            if url:
                if url.startswith('/'):
                    url = f"{config.CANVAS_BASE_URL}{url}"
                self.start_quiz_timer(url)
            self.adw.quizStatusBar.setVisible(True)
        else:
            self.stop_quiz_timer()
            self.adw.quizStatusBar.setVisible(False)

    def _ensure_assignment_folder(self):
        """Create assignment folder if needed"""
        if not self.mgr.todo.get('assignment_details', {}).get('assignment_folder'):
            from func.getTodos import create_assignment_folder
            folder = create_assignment_folder(
                config.TODO_DIR,
                self.mgr.todo.get('name', 'Unknown'),
                self.mgr.todo.get('due_date')
            )
            if 'assignment_details' not in self.mgr.todo:
                self.mgr.todo['assignment_details'] = {}
            self.mgr.todo['assignment_details']['assignment_folder'] = folder

            # Save to todos.json
            try:
                todos = json.load(open(config.TODOS_FILE))
                for t in todos:
                    if t.get('name') == self.mgr.todo.get('name') and t.get('due_date') == self.mgr.todo.get('due_date'):
                        if 'assignment_details' not in t:
                            t['assignment_details'] = {}
                        t['assignment_details']['assignment_folder'] = folder
                        break
                json.dump(todos, open(config.TODOS_FILE, 'w'), indent=2)
            except Exception:
                pass

    # === MODEL SELECTION ===
    def init_model_selection(self):
        """Initialize model selection"""
        cfg = model_config.load_default_config()
        product, model = cfg.get('product', 'Gemini'), cfg.get('model', 'gemini-2.5-pro')

        idx = self.adw.productComboBox.findText(product)
        if idx >= 0:
            self.adw.productComboBox.setCurrentIndex(idx)

        all_models = model_config.get_all_models()
        self.adw.modelComboBox.clear()
        self.adw.modelComboBox.addItems(all_models.get(product, []))

        idx = self.adw.modelComboBox.findText(model)
        if idx >= 0:
            self.adw.modelComboBox.setCurrentIndex(idx)

        self.adw.thinkingToggleWidget.setVisible(product == 'Claude')

    def on_product_changed(self, product):
        """Handle product selection change"""
        all_models = model_config.get_all_models()
        self.adw.modelComboBox.clear()
        self.adw.modelComboBox.addItems(all_models.get(product, []))
        self.adw.thinkingToggleWidget.setVisible(product == 'Claude')

    def on_model_changed(self, model):
        """Handle model selection change"""
        product = self.adw.productComboBox.currentText()
        model_config.save_default_config(product, model)

    # === BUTTON HANDLERS ===
    def on_folder_clicked(self):
        """Open assignment folder"""
        if not self.mgr:
            return
        folder = self.mgr.todo.get('assignment_details', {}).get('folder')
        if folder:
            path = os.path.join(config.TODO_DIR, folder)
            if os.path.exists(path):
                self.app.open_folder(path)

    def on_debug_clicked(self):
        """Debug (run CLI)"""
        if not self.mgr:
            return
        url = self._get_url()
        if not url:
            return

        import subprocess
        script = 'getQuiz_ultra.py' if self.mgr.is_quiz else 'getHomework.py'
        subprocess.Popen([
            sys.executable, os.path.join(config.ROOT_DIR, 'func', script),
            '--url', url,
            '--product', self.adw.productComboBox.currentText(),
            '--model', self.adw.modelComboBox.currentText()
        ], cwd=config.ROOT_DIR)

    def on_again_clicked(self):
        """Regenerate preview"""
        if not self.mgr:
            return
        if self.mgr.is_quiz:
            self._on_quiz_again()
        else:
            self._on_hw_again()

    def _on_hw_again(self):
        """Regenerate homework"""
        url = self._get_url()
        if not url:
            return

        product = self.adw.productComboBox.currentText()
        model = self.adw.modelComboBox.currentText()
        prompt = self.adw.promptEditBox.toPlainText().strip() or config.DEFAULT_PROMPTS['homework']
        folder = self.mgr.todo.get('assignment_details', {}).get('assignment_folder')

        if not folder:
            self.adw.previewStatusLabel.setText("Status: Error - No assignment folder")
            return

        # Collect reference files
        ref_files = []
        for f in (self.mgr.todo.get('assignment_details') or {}).get('files') or []:
            if fp := f.get('local_path'):
                if os.path.exists(fp):
                    ref_files.append(fp)

        def run(progress=None):
            try:
                if progress:
                    progress.update(status="Starting homework generation...", progress=5)
                from func import getHomework
                getHomework.run_gui(url, product, model, prompt, ref_files, folder, progress=progress)
                if progress:
                    progress.update(status="Preview generated", progress=100)
                self.app.signals.auto_detail_status.emit("Status: Preview generated")
                self.app.signals.preview_refresh.emit()
            except Exception as e:
                import traceback
                traceback.print_exc()
                if progress:
                    progress.update(error=str(e))
                self.app.signals.auto_detail_status.emit(f"Status: Error - {str(e)}")

        self._run_task("Homework Generation", run)
        self.adw.previewStatusLabel.setText("Status: Generating...")

    def _on_quiz_again(self, auto_start=False):
        """Regenerate quiz"""
        url = self._get_url()
        if not url:
            return

        product = self.adw.productComboBox.currentText()
        model = self.adw.modelComboBox.currentText()
        prompt = self.adw.promptEditBox.toPlainText().strip() or config.DEFAULT_PROMPTS['quiz']
        thinking = self.app.thinking_toggle.isChecked() if product == 'Claude' else False
        folder = self.mgr.todo.get('assignment_details', {}).get('assignment_folder')

        if not folder:
            self.adw.previewStatusLabel.setText("Status: Error - No assignment folder")
            return

        def run(progress=None):
            try:
                if progress:
                    progress.update(status="Checking quiz status...", progress=5)
                from func import getQuiz_ultra
                result = getQuiz_ultra.run_gui(url, product, model, prompt, folder, thinking=thinking, auto_start=auto_start, progress=progress)

                if result.get('status') == 'not_started':
                    if progress:
                        progress.update(status="Quiz not started", progress=100)
                    self.app.signals.auto_detail_status.emit("Status: Quiz not started")
                    self.app.signals.quiz_not_started.emit()
                    return

                self.app._last_quiz_result = result
                if progress:
                    progress.update(status="Preview generated", progress=100)
                self.app.signals.auto_detail_status.emit("Status: Preview generated")
                self.app.signals.preview_refresh.emit()
            except Exception as e:
                import traceback
                traceback.print_exc()
                if progress:
                    progress.update(error=str(e))
                self.app.signals.auto_detail_status.emit(f"Status: Error - {str(e)}")

        self._run_task("Quiz Generation", run)
        self.adw.previewStatusLabel.setText("Status: Checking quiz status...")

    def on_quiz_not_started(self):
        """Handle quiz not started - show confirmation"""
        reply = QMessageBox.question(
            self.adw, 'Quiz Not Started',
            'This quiz has not been started yet.\n\nDo you want to START the quiz now?\n\nThis will begin a timed attempt!',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._on_quiz_again(auto_start=True)
        else:
            self.adw.previewStatusLabel.setText("Status: Quiz not started - cancelled")

    def on_preview_clicked(self):
        """Generate preview (same as Again)"""
        self.on_again_clicked()

    def refresh_preview(self):
        """Refresh preview panel"""
        if not self.mgr:
            return
        preview_html = self._load_preview()
        if preview_html:
            self.adw.aiPreviewView.setHtml(preview_html)
            self.adw.previewStatusLabel.setText("Status: Preview loaded")

    def on_submit_clicked(self):
        """Submit to Canvas"""
        if not self.mgr:
            return
        if self.mgr.is_quiz:
            self._on_quiz_submit()
        else:
            self._on_hw_submit()

    def _on_hw_submit(self):
        """Submit homework"""
        url = self._get_url()
        if not url:
            return

        reply = QMessageBox.question(self.adw, 'Confirm Submission', 'Submit homework to Canvas?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        def run():
            try:
                from func import getHomework
                success = getHomework.submit_to_canvas(url)
                msg = "Submitted successfully" if success else "Submission failed"
                self.adw.previewStatusLabel.setText(f"Status: {msg}")
                self.app.show_toast("Homework 提交成功！" if success else "Homework 提交失败", 'success' if success else 'error')
            except Exception as e:
                self.adw.previewStatusLabel.setText(f"Status: Error - {str(e)}")
                self.app.show_toast(f"提交错误: {str(e)}", 'error')

        threading.Thread(target=run, daemon=True).start()
        self.adw.previewStatusLabel.setText("Status: Submitting...")

    def _on_quiz_submit(self):
        """Submit quiz"""
        reply = QMessageBox.question(self.adw, 'Confirm Submission', 'Submit quiz answers to Canvas?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        def run():
            try:
                from func import getQuiz_ultra
                if not hasattr(self.app, '_last_quiz_result'):
                    self.app.signals.auto_detail_status.emit("Status: No preview data - generate first")
                    self.app.show_toast("需要先生成预览", 'warning')
                    return
                result = self.app._last_quiz_result
                getQuiz_ultra.submit(result['session'], result['url'], result['doc'], result['questions'], result['answers'], skip_confirm=True)
                self.app.signals.auto_detail_status.emit("Status: Submitted successfully")
                self.app.show_toast("Quiz 提交成功！", 'success')
            except Exception as e:
                self.app.signals.auto_detail_status.emit(f"Status: Error - {str(e)}")
                self.app.show_toast(f"提交错误: {str(e)}", 'error')

        threading.Thread(target=run, daemon=True).start()
        self.adw.previewStatusLabel.setText("Status: Submitting...")

    def on_view_detail_clicked(self):
        """View detail (placeholder)"""
        pass

    def on_tab_changed(self, tab_name):
        """Handle tab change"""
        preview_html = self._load_preview(tab_name)
        if preview_html:
            self.adw.aiPreviewView.setHtml(preview_html)

    # === HELPERS ===
    def _get_url(self):
        """Get current URL"""
        url = self.mgr.todo.get('redirect_url') or self.mgr.todo.get('assignment', {}).get('html_url')
        if url and url.startswith('/'):
            url = f"{config.CANVAS_BASE_URL}{url}"
        return url

    def _run_task(self, name, func):
        """Run task with Mission Control or thread"""
        if hasattr(self.app, 'mission_control'):
            self.app.mission_control.start_task(name, func)
        else:
            threading.Thread(target=func, daemon=True).start()

    # === HTML GENERATION ===
    def _get_identification_info(self):
        """Get identification info"""
        due_str = "No due date"
        if self.mgr.due_date:
            try:
                dt = datetime.fromisoformat(self.mgr.due_date.replace('Z', '+00:00'))
                due_str = dt.strftime("%m/%d/%Y %I:%M %p")
            except Exception:
                due_str = self.mgr.due_date
        return {
            'course': self.mgr.course_name,
            'assignment': self.mgr.assignment_name,
            'type': self.mgr.type_str,
            'due_date': due_str
        }

    def _get_assignment_detail_html(self):
        """Get assignment detail HTML"""
        desc = self.mgr.assignment_details.get('desc', '') or ''
        desc = '' if not desc.strip() or desc.strip() == 'null' else desc
        if not desc:
            desc = f'<p style="color:{C["text_muted"]};">No description available</p>'
        return f'<div style="color:{C["text_primary"]};font-family:-apple-system,sans-serif;font-size:14px;line-height:1.6;">{desc}</div>'

    def _get_preview_placeholder_html(self):
        """Get preview placeholder HTML"""
        return f'''<div style="text-align:center;padding:80px 20px;">
            <div style="font-size:32px;margin-bottom:16px;color:{C['text_muted']};">[ Preview ]</div>
            <div style="color:{C['text_secondary']};font-size:14px;">No preview generated yet</div>
            <div style="color:{C['text_muted']};font-size:12px;margin-top:8px;">Click "Again" to generate answers</div>
        </div>'''

    def _get_reference_files_html(self):
        """Get reference files HTML"""
        if self.mgr.is_quiz:
            return ''
        if not self.mgr.is_homework:
            return f'<div style="text-align:center;padding:20px;color:{C["text_secondary"]};">Not supported for this type</div>'

        folder = self.mgr.assignment_details.get('assignment_folder')
        if not folder:
            return f'''<div style="background:{C['bg_tertiary']};border:1px solid {C['accent_orange']};border-radius:8px;padding:16px;text-align:center;color:{C['accent_orange']};">
                <div style="font-weight:600;margin-bottom:4px;">Warning</div>
                <div style="font-size:12px;">No assignment folder found</div>
            </div>'''

        file_items = []
        for dir_path in [os.path.join(folder, 'auto', 'input'), os.path.join(folder, 'files')]:
            if not os.path.exists(dir_path):
                continue
            for f in os.listdir(dir_path):
                fp = os.path.join(dir_path, f)
                if not os.path.isfile(fp):
                    continue
                sz = os.path.getsize(fp)
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if sz < 1024:
                        break
                    sz /= 1024.0
                ext = f.lower().split('.')[-1] if '.' in f else ''
                labels = {'pdf': 'PDF', 'xlsx': 'XLS', 'xls': 'XLS', 'doc': 'DOC', 'docx': 'DOC', 'txt': 'TXT', 'png': 'IMG', 'jpg': 'IMG', 'jpeg': 'IMG'}
                label = labels.get(ext, 'FILE')
                file_items.append(f'''
                    <div style="background:{C['bg_tertiary']};border:1px solid {C['border']};border-radius:8px;padding:10px 14px;margin:6px 0;">
                        <span style="background:{C['accent_purple']};color:white;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;margin-right:10px;">{label}</span>
                        <span style="color:{C['text_primary']};font-size:13px;">{f}</span>
                        <span style="color:{C['text_muted']};font-size:11px;margin-left:8px;">{sz:.1f} {unit}</span>
                    </div>
                ''')

        if not file_items:
            return f'''<div style="background:{C['bg_tertiary']};border:1px solid {C['border']};border-radius:8px;padding:16px;text-align:center;">
                <div style="color:{C['text_secondary']};font-size:13px;">No reference files</div>
                <div style="font-size:11px;color:{C['text_muted']};margin-top:4px;">Drop files into auto/input/</div>
            </div>'''

        return ''.join(file_items)

    def _load_preview(self, tab_name=None):
        """Load preview HTML"""
        if not self.mgr:
            return None
        folder = self.mgr.todo.get('assignment_details', {}).get('assignment_folder')
        if not folder:
            return None
        output_dir = os.path.join(folder, 'auto', 'output')
        if not os.path.exists(output_dir):
            return None

        if self.mgr.is_quiz:
            has_qeswa = os.path.exists(os.path.join(output_dir, 'QesWA.md'))
            has_questions = os.path.exists(os.path.join(output_dir, 'questions.md'))
            self.adw.update_available_tabs(has_qeswa, has_questions)

            files = ['questions.md', 'QesWA.md'] if tab_name == 'questions' else ['QesWA.md', 'questions.md']
            for fn in files:
                fp = os.path.join(output_dir, fn)
                if os.path.exists(fp):
                    try:
                        return self._markdown_to_html(open(fp, encoding='utf-8').read(), fn, output_dir)
                    except Exception:
                        pass
        elif self.mgr.is_homework:
            fp = os.path.join(output_dir, 'answer.md')
            if os.path.exists(fp):
                return self._markdown_to_html(open(fp, encoding='utf-8').read(), 'answer.md', output_dir)

        return None

    def _markdown_to_html(self, content, filename, base_dir=None):
        """Convert markdown to styled HTML"""
        import markdown as md_lib
        html = md_lib.markdown(content, extensions=['extra', 'nl2br', 'tables'])

        # Embed images for quiz
        if base_dir and self.mgr.is_quiz:
            images_dir = os.path.join(base_dir, 'images')
            if os.path.exists(images_dir):
                def replace_img(match):
                    fn = match.group(1)
                    img_path = os.path.join(images_dir, fn)
                    if os.path.exists(img_path):
                        try:
                            with open(img_path, 'rb') as f:
                                data = base64.b64encode(f.read()).decode()
                            ext = fn.split('.')[-1].lower()
                            mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
                            return f'<img src="data:{mime};base64,{data}" style="max-width:280px;border:1px solid {C["border"]};border-radius:8px;margin:8px 0;"/>'
                        except Exception:
                            pass
                    return match.group(0)
                html = re.sub(r'\(Imgs:\s*([a-zA-Z0-9_]+\.(?:png|jpg|jpeg|gif|webp))\)', replace_img, html, flags=re.IGNORECASE)
                html = re.sub(r'<code>([^<>]+\.(?:png|jpg|jpeg|gif|webp))</code>', replace_img, html, flags=re.IGNORECASE)

        # Style list items
        html = html.replace('<ul>', '<div class="answer-list">').replace('</ul>', '</div>')
        html = html.replace('<ol>', '<div class="answer-list">').replace('</ol>', '</div>')
        html = html.replace('✅', '<span class="selected-marker">[*]</span>')

        # Selected answers
        html = re.sub(
            r'<li>\s*<span class="selected-marker">\[\*\]</span>\s*<code>([^<]+)</code>:\s*(.*?)</li>',
            rf'<div style="background:rgba(34,197,94,0.15);border-left:3px solid {C["accent_green"]};padding:8px 12px;margin:8px 0;border-radius:0 6px 6px 0;"><span style="color:{C["accent_green"]};font-weight:bold;">[*]</span> <code style="background:{C["bg_tertiary"]};color:{C["accent_orange"]};padding:2px 6px;border-radius:4px;font-size:11px;">\g<1></code>: \g<2></div>',
            html
        )
        # Non-selected
        html = re.sub(
            r'<li>\s*<code>([^<]+)</code>:\s*(.*?)</li>',
            rf'<div style="padding:8px 12px;margin:8px 0;color:{C["text_secondary"]};"><span style="color:{C["text_muted"]};">[ ]</span> <code style="background:{C["bg_tertiary"]};color:{C["accent_orange"]};padding:2px 6px;border-radius:4px;font-size:11px;">\g<1></code>: \g<2></div>',
            html
        )
        html = re.sub(
            r'<li>\s*\[\*\]\s*<code>([^<]+)</code>:\s*(.*?)</li>',
            rf'<div style="background:rgba(34,197,94,0.15);border-left:3px solid {C["accent_green"]};padding:8px 12px;margin:8px 0;border-radius:0 6px 6px 0;"><span style="color:{C["accent_green"]};font-weight:bold;">[*]</span> <code style="background:{C["bg_tertiary"]};color:{C["accent_orange"]};padding:2px 6px;border-radius:4px;font-size:11px;">\g<1></code>: \g<2></div>',
            html
        )
        html = re.sub(r'<li>(.*?)</li>', r'<div style="padding:4px 0;">\1</div>', html)
        html = re.sub(r'<span class="selected-marker">\[\*\]</span>', rf'<span style="color:{C["accent_green"]};font-weight:bold;">[*]</span>', html)

        css = f'''
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: {C['text_primary']}; background: {C['bg_secondary']}; }}
            h1 {{ color: {C['accent_green']}; font-size: 22px; font-weight: 600; margin: 0 0 20px 0; padding-bottom: 12px; border-bottom: 2px solid {C['accent_green']}; }}
            h2 {{ color: {C['accent_blue']}; font-size: 16px; font-weight: 600; margin: 24px 0 12px 0; padding: 12px; background: {C['bg_tertiary']}; border-radius: 8px; border-left: 3px solid {C['accent_purple']}; }}
            h3 {{ color: {C['accent_purple']}; font-size: 14px; font-weight: 600; margin: 16px 0 8px 0; }}
            p {{ margin: 8px 0; color: {C['text_primary']}; }}
            code {{ background: {C['bg_tertiary']}; padding: 2px 6px; border-radius: 4px; font-family: 'SF Mono', Consolas, monospace; font-size: 12px; color: {C['accent_orange']}; }}
            pre {{ background: {C['bg_primary']}; padding: 16px; border-radius: 8px; border: 1px solid {C['border']}; overflow-x: auto; }}
            ul, ol {{ padding-left: 0; list-style: none; margin: 12px 0; }}
            li {{ display: block; margin: 6px 0; }}
            a {{ color: {C['accent_blue']}; text-decoration: none; }}
            strong {{ color: {C['text_primary']}; }}
            em {{ color: {C['accent_blue']}; font-style: italic; }}
            hr {{ border: none; border-top: 1px solid {C['border']}; margin: 20px 0; }}
            img {{ max-width: 100%; border-radius: 8px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
            th, td {{ border: 1px solid {C['border']}; padding: 8px 12px; text-align: left; }}
            th {{ background: {C['bg_tertiary']}; font-weight: 600; }}
        '''
        return f'<style>{css}</style>{html}'
