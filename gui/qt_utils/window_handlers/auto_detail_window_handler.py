"""AutoDetail Window Handler - Manages AutoDetail window (17 methods)"""
import sys, os, json, threading
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import config
from gui.qt_utils.base_handler import BaseHandler
from gui import cfgModel as model_config


class AutoDetailWindowHandler(BaseHandler):
    """Handles AutoDetail window operations"""

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

    def load_preview(self):
        """Load AI preview (quiz or homework) if files exist"""
        if not self.auto_detail_mgr:
            return None
        assignment_folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder')
        if not assignment_folder:
            return None
        output_dir = os.path.join(assignment_folder, 'auto', 'output')
        if not os.path.exists(output_dir):
            return None
        if self.auto_detail_mgr.is_quiz:
            return self.auto_detail_mgr.load_quiz_preview(output_dir)
        elif self.auto_detail_mgr.is_homework:
            return self.auto_detail_mgr.load_homework_preview(output_dir)
        return None

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

        def run():
            try:
                from func import getHomework
                result = getHomework.run_gui(url, product, model, prompt, ref_files, assignment_folder)
                self.app.auto_detail_signal.status_update.emit("Status: Preview generated")
                self.app.auto_detail_signal.preview_refresh.emit()
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.app.auto_detail_signal.status_update.emit(f"Status: Error - {str(e)}")

        threading.Thread(target=run, daemon=True).start()
        adw.previewStatusLabel.setText("Status: Generating...")

    def on_quiz_again_clicked(self):
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

        def run():
            try:
                from func import getQuiz_ultra
                result = getQuiz_ultra.run_gui(url, product, model, prompt, assignment_folder, thinking=thinking)
                self.app._last_quiz_result = result
                self.app.auto_detail_signal.status_update.emit("Status: Preview generated")
                self.app.auto_detail_signal.preview_refresh.emit()
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.app.auto_detail_signal.status_update.emit(f"Status: Error - {str(e)}")

        threading.Thread(target=run, daemon=True).start()
        adw.previewStatusLabel.setText("Status: Generating...")

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
