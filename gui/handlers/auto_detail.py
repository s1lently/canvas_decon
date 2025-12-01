"""AutoDetail Window Handler - Manages AutoDetail window (17 methods)"""
import sys, os, json, threading
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import config
from gui.base_handler import BaseHandler
from gui.config import cfgModel as model_config


class AutoDetailWindowHandler(BaseHandler):
    """Handles AutoDetail window operations"""

    def __init__(self, app):
        super().__init__(app)
        # Quiz status timer (500ms interval)
        self._quiz_status_timer = None
        self._current_quiz_url = None

    def _init_quiz_status_timer(self):
        """Initialize quiz status timer"""
        if self._quiz_status_timer is None:
            self._quiz_status_timer = QTimer()
            self._quiz_status_timer.setInterval(500)  # 0.5 seconds
            self._quiz_status_timer.timeout.connect(self._fetch_quiz_status)

    def start_quiz_status_timer(self, url):
        """Start the quiz status timer"""
        self._init_quiz_status_timer()
        self._current_quiz_url = url
        if not self._quiz_status_timer.isActive():
            self._fetch_quiz_status()  # Initial fetch
            self._quiz_status_timer.start()

    def stop_quiz_status_timer(self):
        """Stop the quiz status timer"""
        if self._quiz_status_timer and self._quiz_status_timer.isActive():
            self._quiz_status_timer.stop()
        self._current_quiz_url = None

    def _fetch_quiz_status(self):
        """Fetch quiz status in background thread"""
        if not self._current_quiz_url:
            return

        url = self._current_quiz_url

        def fetch():
            try:
                from func.getQuizStatus import get_quiz_status
                status = get_quiz_status(url)
                self.app.auto_detail_signal.quiz_status_update.emit(status)
            except Exception as e:
                print(f"[QuizStatus] Error: {e}")

        threading.Thread(target=fetch, daemon=True).start()

    def update_quiz_status_bar(self, status):
        """Update quiz status bar labels with status data"""
        adw = self.auto_detail_window
        if not adw:
            return

        # Show/hide status bar
        adw.quizStatusBar.setVisible(True)

        if status.get('status') == 'error':
            adw.quizScoreLabel.setText(f"Error: {status.get('error', 'Unknown')[:30]}")
            adw.quizScoreLabel.setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
            adw.quizBestLabel.setText("")
            adw.quizAttemptsLabel.setText("")
            adw.quizTimeLabel.setText("")
            return

        # Score
        if status.get('current_score') is not None:
            score = status['current_score']
            total = status.get('points_possible', 0)
            score_color = '#22c55e' if score == total else '#60a5fa'
            adw.quizScoreLabel.setText(f"Score: {score}/{total}")
            adw.quizScoreLabel.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {score_color};")
        else:
            adw.quizScoreLabel.setText("Score: --/--")
            adw.quizScoreLabel.setStyleSheet("font-size: 14px; font-weight: bold; color: #9ca3af;")

        # Best score
        if status.get('highest_score') is not None:
            best = status['highest_score']
            if best != status.get('current_score'):
                adw.quizBestLabel.setText(f"Best: {best}")
                adw.quizBestLabel.setVisible(True)
            else:
                adw.quizBestLabel.setText("")
        else:
            adw.quizBestLabel.setText("")

        # Attempts
        used = status.get('attempts_used', 0)
        allowed = status.get('allowed_attempts', 1)
        left = status.get('attempts_left', 0)

        if allowed == -1:
            adw.quizAttemptsLabel.setText(f"Attempts: {used}/∞")
            adw.quizAttemptsLabel.setStyleSheet("font-size: 13px; color: #22c55e;")
        elif left == 0:
            adw.quizAttemptsLabel.setText(f"Attempts: {used}/{allowed} (Done)")
            adw.quizAttemptsLabel.setStyleSheet("font-size: 13px; color: #ef4444;")
        else:
            adw.quizAttemptsLabel.setText(f"Attempts: {used}/{allowed} ({left} left)")
            adw.quizAttemptsLabel.setStyleSheet("font-size: 13px; color: #eab308;")

        # Status indicator (always show current state, no emojis)
        if status.get('in_progress'):
            if status.get('time_remaining') is not None:
                mins = status['time_remaining'] // 60
                secs = status['time_remaining'] % 60
                adw.quizTimeLabel.setText(f"In Progress - {mins}:{secs:02d}")
                adw.quizTimeLabel.setStyleSheet("font-size: 13px; font-weight: bold; color: #f59e0b;")
            else:
                adw.quizTimeLabel.setText("In Progress")
                adw.quizTimeLabel.setStyleSheet("font-size: 13px; font-weight: bold; color: #f59e0b;")
        elif status.get('attempts_used', 0) == 0:
            # Never attempted
            adw.quizTimeLabel.setText("Not Started")
            adw.quizTimeLabel.setStyleSheet("font-size: 13px; font-weight: bold; color: #9ca3af;")
        elif left == 0:
            # No attempts left
            adw.quizTimeLabel.setText("Completed")
            adw.quizTimeLabel.setStyleSheet("font-size: 13px; font-weight: bold; color: #22c55e;")
        else:
            # Has attempts, not in progress
            time_str = f" ({status['time_limit']}min)" if status.get('time_limit') else ""
            adw.quizTimeLabel.setText(f"Retryable{time_str}")
            adw.quizTimeLabel.setStyleSheet("font-size: 13px; font-weight: bold; color: #eab308;")

    def populate_window(self):
        """Populate autoDetail window with TODO data"""
        if not self.auto_detail_mgr:
            return
        adw = self.auto_detail_window
        info = self.auto_detail_mgr.get_identification_info()
        adw.courseNameLabel.setText(f"Course: {info['course']}")
        adw.assignmentNameLabel.setText(f"Assignment: {info['assignment']}")
        adw.typeLabel.setText(f"Type: {info['type']}")
        adw.dueDateLabel.setText(f"Due: {info['due_date']}")
        adw.assignmentDetailView.setHtml(self.auto_detail_mgr.get_assignment_detail_html())
        adw.refFilesView.setHtml(self.auto_detail_mgr.get_reference_files_html())
        is_quiz = self.auto_detail_mgr.is_quiz
        is_homework = self.auto_detail_mgr.is_homework
        adw.quizControlWidget.setVisible(is_quiz)
        adw.hwControlWidget.setVisible(is_homework)
        adw.consoleTitle.setText(f"{info['type']} Automation Console")
        preview_html = self.load_preview()
        adw.aiPreviewView.setHtml(preview_html if preview_html else self.auto_detail_mgr.get_preview_placeholder_html())
        adw.previewStatusLabel.setText("Status: Preview loaded" if preview_html else "Status: No preview generated yet")
        config.ensure_dirs()
        if not self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder'):
            from func.getTodos import create_assignment_folder
            assignment_name = self.auto_detail_mgr.todo.get('name', 'Unknown')
            due_date = self.auto_detail_mgr.todo.get('due_date')
            assignment_folder = create_assignment_folder(config.TODO_DIR, assignment_name, due_date)
            if 'assignment_details' not in self.auto_detail_mgr.todo:
                self.auto_detail_mgr.todo['assignment_details'] = {}
            self.auto_detail_mgr.todo['assignment_details']['assignment_folder'] = assignment_folder
            try:
                todos_data = json.load(open(config.TODOS_FILE))
                for todo in todos_data:
                    if (todo.get('name') == self.auto_detail_mgr.todo.get('name') and
                        todo.get('due_date') == self.auto_detail_mgr.todo.get('due_date')):
                        if 'assignment_details' not in todo:
                            todo['assignment_details'] = {}
                        todo['assignment_details']['assignment_folder'] = assignment_folder
                        break
                json.dump(todos_data, open(config.TODOS_FILE, 'w'), indent=2)
            except Exception as e:
                print(f"Warning: Failed to save assignment_folder to todos.json: {e}")
        prompt_type = 'quiz' if is_quiz else 'homework'
        adw.promptEditBox.setPlainText(config.DEFAULT_PROMPTS.get(prompt_type, ''))

        # Quiz status bar: start timer for quizzes
        if is_quiz:
            url = self.auto_detail_mgr.todo.get('redirect_url') or self.auto_detail_mgr.todo.get('assignment', {}).get('html_url')
            if url:
                if url.startswith('/'):
                    url = f"{config.CANVAS_BASE_URL}{url}"
                self.start_quiz_status_timer(url)
            adw.quizStatusBar.setVisible(True)
        else:
            self.stop_quiz_status_timer()
            adw.quizStatusBar.setVisible(False)

    def load_preview(self, tab_name=None):
        """Load AI preview (quiz or homework) if files exist"""
        if not self.auto_detail_mgr:
            return None
        assignment_folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder')
        if not assignment_folder:
            return None
        output_dir = os.path.join(assignment_folder, 'auto', 'output')
        if not os.path.exists(output_dir):
            return None

        # For quiz, check which tab to load
        if self.auto_detail_mgr.is_quiz:
            has_qeswa = os.path.exists(os.path.join(output_dir, 'QesWA.md'))
            has_questions = os.path.exists(os.path.join(output_dir, 'questions.md'))
            # Update tab visibility
            self.auto_detail_window.update_available_tabs(has_qeswa, has_questions)

            if tab_name == 'questions' and has_questions:
                return self.auto_detail_mgr.load_quiz_preview(output_dir, prefer_questions=True)
            else:
                return self.auto_detail_mgr.load_quiz_preview(output_dir)
        elif self.auto_detail_mgr.is_homework:
            return self.auto_detail_mgr.load_homework_preview(output_dir)
        return None

    def on_tab_changed(self, tab_name):
        """Handle tab change - reload preview with different file"""
        preview_html = self.load_preview(tab_name)
        if preview_html:
            self.auto_detail_window.aiPreviewView.setHtml(preview_html)

    def update_status(self, status_text):
        """Slot function to update AutoDetail status label from background thread"""
        if self.auto_detail_window:
            self.auto_detail_window.previewStatusLabel.setText(status_text)

    def init_model_selection(self):
        """Initialize model selection from default.json"""
        cfg = model_config.load_default_config()
        product, model = cfg.get('product', 'Gemini'), cfg.get('model', 'gemini-2.5-pro')
        idx = self.auto_detail_window.productComboBox.findText(product)
        if idx >= 0:
            self.auto_detail_window.productComboBox.setCurrentIndex(idx)
        all_models = model_config.get_all_models()
        self.auto_detail_window.modelComboBox.clear()
        self.auto_detail_window.modelComboBox.addItems(all_models.get(product, []))
        idx = self.auto_detail_window.modelComboBox.findText(model)
        if idx >= 0:
            self.auto_detail_window.modelComboBox.setCurrentIndex(idx)
        # Show thinking toggle only for Claude
        self.auto_detail_window.thinkingToggleWidget.setVisible(product == 'Claude')

    def on_product_changed(self, product):
        """Handle product selection change"""
        all_models = model_config.get_all_models()
        self.auto_detail_window.modelComboBox.clear()
        self.auto_detail_window.modelComboBox.addItems(all_models.get(product, []))
        self.auto_detail_window.thinkingToggleWidget.setVisible(product == 'Claude')

    def on_model_changed(self, model):
        """Handle model selection change"""
        product = self.auto_detail_window.productComboBox.currentText()
        model_config.save_default_config(product, model)

    def on_auto_folder_clicked(self):
        """Open assignment folder from AutoDetail"""
        if not self.auto_detail_mgr:
            return
        folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('folder')
        if folder:
            fp = os.path.join(config.TODO_DIR, folder)
            if os.path.exists(fp):
                self.app._open_folder(fp)

    def on_debug_clicked(self):
        """Unified debug handler - delegates to hw or quiz based on type"""
        if not self.auto_detail_mgr:
            return
        if self.auto_detail_mgr.is_quiz:
            self.on_quiz_debug_clicked()
        else:
            self.on_hw_debug_clicked()

    def on_hw_debug_clicked(self):
        """Debug homework (run CLI with current settings)"""
        if not self.auto_detail_mgr:
            return
        adw = self.auto_detail_window
        url = self.auto_detail_mgr.todo.get('redirect_url') or self.auto_detail_mgr.todo.get('assignment', {}).get('html_url')
        if not url:
            return
        if url.startswith('/'):
            url = f"{config.CANVAS_BASE_URL}{url}"
        product = adw.productComboBox.currentText()
        model = adw.modelComboBox.currentText()
        import subprocess
        subprocess.Popen([sys.executable, os.path.join(config.ROOT_DIR, 'func/getHomework.py'),
                         '--url', url, '--product', product, '--model', model],
                        cwd=config.ROOT_DIR)

    def on_quiz_debug_clicked(self):
        """Debug quiz (run CLI with current settings)"""
        if not self.auto_detail_mgr:
            return
        adw = self.auto_detail_window
        url = self.auto_detail_mgr.todo.get('redirect_url') or self.auto_detail_mgr.todo.get('assignment', {}).get('html_url')
        if not url:
            return
        if url.startswith('/'):
            url = f"{config.CANVAS_BASE_URL}{url}"
        product = adw.productComboBox.currentText()
        model = adw.modelComboBox.currentText()
        import subprocess
        subprocess.Popen([sys.executable, os.path.join(config.ROOT_DIR, 'func/getQuiz_ultra.py'),
                         '--url', url, '--product', product, '--model', model],
                        cwd=config.ROOT_DIR)

    def on_again_clicked(self):
        """Unified again handler - delegates to hw or quiz based on type"""
        if not self.auto_detail_mgr:
            return
        if self.auto_detail_mgr.is_quiz:
            self.on_quiz_again_clicked()
        else:
            self.on_hw_again_clicked()

    def on_hw_again_clicked(self):
        """Regenerate homework with current settings"""
        if not self.auto_detail_mgr:
            return
        adw = self.auto_detail_window
        url = self.auto_detail_mgr.todo.get('redirect_url') or self.auto_detail_mgr.todo.get('assignment', {}).get('html_url')
        if not url:
            return
        if url.startswith('/'):
            url = f"{config.CANVAS_BASE_URL}{url}"
        product = adw.productComboBox.currentText()
        model = adw.modelComboBox.currentText()
        prompt = adw.promptEditBox.toPlainText().strip() or config.DEFAULT_PROMPTS['homework']
        ref_files = []
        todo_files = (self.auto_detail_mgr.todo.get('assignment_details') or {}).get('files') or []
        for f in todo_files:
            if fp := f.get('local_path'):
                if os.path.exists(fp):
                    ref_files.append(fp)
        assignment_folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder')
        if not assignment_folder:
            adw.previewStatusLabel.setText("Status: Error - No assignment folder")
            return

        def run(progress=None):
            try:
                if progress:
                    progress.update(status="Starting homework generation...", progress=5)
                from func import getHomework
                result = getHomework.run_gui(url, product, model, prompt, ref_files, assignment_folder, progress=progress)
                if progress:
                    progress.update(status="Preview generated", progress=100)
                self.app.auto_detail_signal.status_update.emit("Status: Preview generated")
                self.app.auto_detail_signal.preview_refresh.emit()
            except Exception as e:
                import traceback
                traceback.print_exc()
                if progress:
                    progress.update(error=str(e))
                self.app.auto_detail_signal.status_update.emit(f"Status: Error - {str(e)}")

        # Use Mission Control if available
        if hasattr(self.app, 'mission_control'):
            self.app.mission_control.start_task("Homework Generation", run)
        else:
            threading.Thread(target=run, daemon=True).start()
        adw.previewStatusLabel.setText("Status: Generating...")

    def on_quiz_again_clicked(self, auto_start=False):
        """Regenerate quiz answers with current settings"""
        if not self.auto_detail_mgr:
            return
        adw = self.auto_detail_window
        url = self.auto_detail_mgr.todo.get('redirect_url') or self.auto_detail_mgr.todo.get('assignment', {}).get('html_url')
        if not url:
            return
        if url.startswith('/'):
            url = f"{config.CANVAS_BASE_URL}{url}"
        product = adw.productComboBox.currentText()
        model = adw.modelComboBox.currentText()
        prompt = adw.promptEditBox.toPlainText().strip() or config.DEFAULT_PROMPTS['quiz']
        thinking = self.app.thinking_toggle.isChecked() if product == 'Claude' else False
        assignment_folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder')
        if not assignment_folder:
            adw.previewStatusLabel.setText("Status: Error - No assignment folder")
            return

        def run(progress=None):
            try:
                if progress:
                    progress.update(status="Checking quiz status...", progress=5)
                from func import getQuiz_ultra
                result = getQuiz_ultra.run_gui(url, product, model, prompt, assignment_folder, thinking=thinking, auto_start=auto_start, progress=progress)

                # Check if quiz is not started
                if result.get('status') == 'not_started':
                    if progress:
                        progress.update(status="Quiz not started", progress=100)
                    self.app.auto_detail_signal.status_update.emit("Status: Quiz not started")
                    self.app.auto_detail_signal.quiz_not_started.emit()
                    return

                self.app._last_quiz_result = result
                if progress:
                    progress.update(status="Preview generated", progress=100)
                self.app.auto_detail_signal.status_update.emit("Status: Preview generated")
                self.app.auto_detail_signal.preview_refresh.emit()
            except Exception as e:
                import traceback
                traceback.print_exc()
                if progress:
                    progress.update(error=str(e))
                self.app.auto_detail_signal.status_update.emit(f"Status: Error - {str(e)}")

        # Use Mission Control if available
        if hasattr(self.app, 'mission_control'):
            self.app.mission_control.start_task("Quiz Generation", run)
        else:
            threading.Thread(target=run, daemon=True).start()
        adw.previewStatusLabel.setText("Status: Checking quiz status...")

    def on_quiz_not_started(self):
        """Handle quiz not started - show confirmation dialog"""
        adw = self.auto_detail_window
        reply = QMessageBox.question(
            adw,
            'Quiz Not Started',
            'This quiz has not been started yet.\n\nDo you want to START the quiz now?\n\n⚠️ This will begin a timed attempt!',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Re-run with auto_start=True
            self.on_quiz_again_clicked(auto_start=True)
        else:
            adw.previewStatusLabel.setText("Status: Quiz not started - cancelled")

    def on_preview_clicked(self):
        """Unified preview handler - delegates to hw or quiz based on type"""
        if not self.auto_detail_mgr:
            return
        if self.auto_detail_mgr.is_quiz:
            self.on_quiz_preview_clicked()
        else:
            self.on_hw_preview_clicked()

    def on_hw_preview_clicked(self):
        """Generate homework preview (same as Again)"""
        self.on_hw_again_clicked()

    def on_quiz_preview_clicked(self):
        """Generate quiz preview (same as Again)"""
        self.on_quiz_again_clicked()

    def refresh_preview(self):
        """Refresh preview panel in AutoDetail window"""
        if not self.auto_detail_mgr:
            return
        adw = self.auto_detail_window
        preview_html = self.load_preview()
        if preview_html:
            adw.aiPreviewView.setHtml(preview_html)
            adw.previewStatusLabel.setText("Status: Preview loaded")

    def on_submit_clicked(self):
        """Unified submit handler - delegates to hw or quiz based on type"""
        if not self.auto_detail_mgr:
            return
        if self.auto_detail_mgr.is_quiz:
            self.on_quiz_submit_clicked()
        else:
            self.on_hw_submit_clicked()

    def on_hw_submit_clicked(self):
        """Submit homework to Canvas"""
        if not self.auto_detail_mgr:
            return
        adw = self.auto_detail_window
        url = self.auto_detail_mgr.todo.get('redirect_url') or self.auto_detail_mgr.todo.get('assignment', {}).get('html_url')
        if not url:
            return
        reply = QMessageBox.question(adw, 'Confirm Submission',
                                     'Submit homework to Canvas?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        def run():
            try:
                from func import getHomework
                success = getHomework.submit_to_canvas(url)
                if success:
                    adw.previewStatusLabel.setText("Status: Submitted successfully")
                    self.app.show_toast("Homework 提交成功！", 'success')
                else:
                    adw.previewStatusLabel.setText("Status: Submission failed")
                    self.app.show_toast("Homework 提交失败", 'error')
            except Exception as e:
                adw.previewStatusLabel.setText(f"Status: Error - {str(e)}")
                self.app.show_toast(f"提交错误: {str(e)}", 'error')

        threading.Thread(target=run, daemon=True).start()
        adw.previewStatusLabel.setText("Status: Submitting...")

    def on_quiz_submit_clicked(self):
        """Submit quiz to Canvas"""
        if not self.auto_detail_mgr:
            return
        adw = self.auto_detail_window
        reply = QMessageBox.question(adw, 'Confirm Submission',
                                     'Submit quiz answers to Canvas?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        def run():
            try:
                from func import getQuiz_ultra
                if not hasattr(self.app, '_last_quiz_result'):
                    self.app.auto_detail_signal.status_update.emit("Status: No preview data - generate first")
                    self.app.show_toast("需要先生成预览", 'warning')
                    return
                result = self.app._last_quiz_result
                s = result['session']
                doc = result['doc']
                url = result['url']
                qs = result['questions']
                ans = result['answers']
                getQuiz_ultra.submit(s, url, doc, qs, ans, skip_confirm=True)
                self.app.auto_detail_signal.status_update.emit("Status: Submitted successfully")
                self.app.show_toast("Quiz 提交成功！", 'success')
            except Exception as e:
                self.app.auto_detail_signal.status_update.emit(f"Status: Error - {str(e)}")
                self.app.show_toast(f"提交错误: {str(e)}", 'error')

        threading.Thread(target=run, daemon=True).start()
        adw.previewStatusLabel.setText("Status: Submitting...")

    def on_view_detail_clicked(self):
        """View detail (placeholder for future implementation)"""
        pass
