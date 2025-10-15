"""Learn Sitting Renderer - Creates 3-tab structure for Textbook in CourseDetail"""
import os
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                              QListWidget, QPushButton, QLabel, QComboBox,
                              QTextEdit, QTextBrowser, QGroupBox, QFormLayout,
                              QListWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from gui.learn_preferences import (load_preferences, save_preferences,
                                    get_available_products, get_available_models,
                                    get_resolved_product_model, set_product, set_model)


class LearnSittingWidget(QWidget):
    """3-Tab widget for Textbook: Tab1=Files, Tab2=Preferences, Tab3=Advanced"""

    def __init__(self, canvas_app, course_detail_mgr, parent=None):
        super().__init__(parent)
        self.canvas_app = canvas_app
        self.course_detail_mgr = course_detail_mgr
        self.prefs = load_preferences()

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Initialize UI structure"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 4px;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #10b981;
                color: white;
            }
        """)

        # Create 3 tabs
        self.tab1 = self.create_tab1_textbook()
        self.tab2 = self.create_tab2_preferences()
        self.tab3 = self.create_tab3_advanced()

        self.tab_widget.addTab(self.tab1, "📚 Textbook")
        self.tab_widget.addTab(self.tab2, "⚙️ Preferences")
        self.tab_widget.addTab(self.tab3, "🔧 Advanced")

        layout.addWidget(self.tab_widget)

    # ========== TAB 1: Textbook Files ==========
    def create_tab1_textbook(self):
        """Create Tab 1: Textbook file list + buttons"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Textbook files group
        textbook_group = QGroupBox("Textbook Files")
        textbook_layout = QVBoxLayout(textbook_group)

        self.textbook_list = QListWidget()
        self.textbook_list.setMinimumHeight(250)
        textbook_layout.addWidget(self.textbook_list)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_open_folder = QPushButton("📂 Open Folder")
        btn_decon = QPushButton("📄 Decon Textbook")
        btn_load_decon = QPushButton("📥 Load From Decon")

        btn_open_folder.clicked.connect(self.on_open_textbook_folder)
        btn_decon.clicked.connect(self.on_decon_textbook)
        btn_load_decon.clicked.connect(self.on_load_from_decon)

        btn_layout.addWidget(btn_open_folder)
        btn_layout.addWidget(btn_decon)
        btn_layout.addWidget(btn_load_decon)
        btn_layout.addStretch()

        textbook_layout.addLayout(btn_layout)
        layout.addWidget(textbook_group)

        # Learn materials group
        learn_group = QGroupBox("Learn Materials (from decon)")
        learn_layout = QVBoxLayout(learn_group)

        self.learn_list = QListWidget()
        self.learn_list.setMinimumHeight(200)
        learn_layout.addWidget(self.learn_list)

        # Buttons
        learn_btn_layout = QHBoxLayout()
        btn_open_learn = QPushButton("📂 Open Learn Folder")
        btn_batch = QPushButton("🚀 Batch Generate All")

        btn_open_learn.clicked.connect(self.on_open_learn_folder)
        btn_batch.clicked.connect(self.on_batch_generate)

        learn_btn_layout.addWidget(btn_open_learn)
        learn_btn_layout.addWidget(btn_batch)
        learn_btn_layout.addStretch()

        learn_layout.addLayout(learn_btn_layout)
        layout.addWidget(learn_group)

        return tab

    # ========== TAB 2: Preferences ==========
    def create_tab2_preferences(self):
        """Create Tab 2: Preferences display"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Model selection group
        model_group = QGroupBox("AI Model Selection")
        model_layout = QFormLayout(model_group)

        self.pref_product_combo = QComboBox()
        self.pref_product_combo.setMinimumHeight(35)
        self.pref_product_combo.addItems(get_available_products())
        self.pref_product_combo.currentTextChanged.connect(self.on_pref_product_changed)

        self.pref_model_combo = QComboBox()
        self.pref_model_combo.setMinimumHeight(35)
        self.pref_model_combo.currentTextChanged.connect(self.on_pref_model_changed)

        self.current_model_label = QLabel("-")
        self.current_model_label.setStyleSheet("color: #10b981; font-weight: bold;")

        model_layout.addRow("Product:", self.pref_product_combo)
        model_layout.addRow("Model:", self.pref_model_combo)
        model_layout.addRow("Current:", self.current_model_label)

        layout.addWidget(model_group)

        # Prompt preview group
        prompt_group = QGroupBox("Default Prompt Template")
        prompt_layout = QVBoxLayout(prompt_group)

        info_label = QLabel("Current prompt will be used as default when generating learning materials.\n"
                           "You can customize it in Tab 3 (Advanced).")
        info_label.setWordWrap(True)
        prompt_layout.addWidget(info_label)

        self.prompt_preview = QTextBrowser()
        self.prompt_preview.setMinimumHeight(250)
        self.prompt_preview.setMaximumHeight(400)
        prompt_layout.addWidget(self.prompt_preview)

        # Buttons
        prompt_btn_layout = QHBoxLayout()
        btn_edit = QPushButton("✏️ Edit in Tab 3")
        btn_reset = QPushButton("🔄 Reset to Default")

        btn_edit.clicked.connect(lambda: self.tab_widget.setCurrentIndex(2))
        btn_reset.clicked.connect(self.on_reset_prompt)

        prompt_btn_layout.addWidget(btn_edit)
        prompt_btn_layout.addWidget(btn_reset)
        prompt_btn_layout.addStretch()

        prompt_layout.addLayout(prompt_btn_layout)
        layout.addWidget(prompt_group)

        layout.addStretch()

        return tab

    # ========== TAB 3: Advanced ==========
    def create_tab3_advanced(self):
        """Create Tab 3: Advanced settings editor"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Model configuration group
        model_group = QGroupBox("Model Configuration")
        model_layout = QVBoxLayout(model_group)

        # Product
        model_layout.addWidget(QLabel("Product Selection:"))
        self.adv_product_combo = QComboBox()
        self.adv_product_combo.setMinimumHeight(35)
        self.adv_product_combo.addItems(get_available_products())
        self.adv_product_combo.currentTextChanged.connect(self.on_adv_product_changed_handler)
        model_layout.addWidget(self.adv_product_combo)

        # Model
        model_layout.addWidget(QLabel("Model Selection:"))
        self.adv_model_combo = QComboBox()
        self.adv_model_combo.setMinimumHeight(35)
        self.adv_model_combo.currentTextChanged.connect(self.on_adv_model_changed)
        model_layout.addWidget(self.adv_model_combo)

        # Available models list
        model_layout.addWidget(QLabel("Available Models:"))
        self.available_models_list = QTextBrowser()
        self.available_models_list.setMinimumHeight(100)
        self.available_models_list.setMaximumHeight(150)
        model_layout.addWidget(self.available_models_list)

        # Refresh button
        refresh_btn_layout = QHBoxLayout()
        btn_refresh_models = QPushButton("🔄 Refresh Models from API")
        btn_refresh_models.clicked.connect(self.on_refresh_models)
        refresh_btn_layout.addWidget(btn_refresh_models)
        refresh_btn_layout.addStretch()
        model_layout.addLayout(refresh_btn_layout)

        layout.addWidget(model_group)

        # Prompt editor group
        prompt_group = QGroupBox("Prompt Template Editor")
        prompt_layout = QVBoxLayout(prompt_group)

        prompt_layout.addWidget(QLabel("Template Type:"))
        self.prompt_type_combo = QComboBox()
        self.prompt_type_combo.setMinimumHeight(30)
        self.prompt_type_combo.addItems([
            "Text Files (Python, JS, etc.)",
            "PDF Documents",
            "CSV Data Files"
        ])
        self.prompt_type_combo.currentIndexChanged.connect(self.on_prompt_type_changed)
        prompt_layout.addWidget(self.prompt_type_combo)

        self.prompt_editor = QTextEdit()
        self.prompt_editor.setMinimumHeight(200)
        self.prompt_editor.setFont(QFont("Consolas, Monaco, monospace", 10))
        prompt_layout.addWidget(self.prompt_editor)

        # Buttons
        prompt_btn_layout = QHBoxLayout()
        btn_save = QPushButton("💾 Save All Settings")
        btn_reset_type = QPushButton("🔄 Reset This Template")
        btn_test = QPushButton("🧪 Test Prompt")

        btn_save.clicked.connect(self.on_save_all)
        btn_reset_type.clicked.connect(self.on_reset_prompt_type)
        btn_test.clicked.connect(self.on_test_prompt)

        prompt_btn_layout.addWidget(btn_save)
        prompt_btn_layout.addWidget(btn_reset_type)
        prompt_btn_layout.addWidget(btn_test)
        prompt_btn_layout.addStretch()

        prompt_layout.addLayout(prompt_btn_layout)
        layout.addWidget(prompt_group)

        return tab

    # ========== Data Loading ==========
    def load_data(self):
        """Load all data into widgets"""
        # Load textbook files
        self.refresh_textbook_list()
        self.refresh_learn_list()

        # Block signals during initial load to prevent unnecessary saves
        self.pref_product_combo.blockSignals(True)
        self.pref_model_combo.blockSignals(True)
        self.adv_product_combo.blockSignals(True)
        self.adv_model_combo.blockSignals(True)

        # Load preferences
        product = self.prefs.get('product', 'Auto')
        model = self.prefs.get('model', 'Auto')

        # Tab 2
        self.pref_product_combo.setCurrentText(product)
        models = get_available_models(product)
        self.pref_model_combo.clear()
        self.pref_model_combo.addItems(models)
        self.pref_model_combo.setCurrentText(model)

        # Tab 3
        self.adv_product_combo.setCurrentText(product)
        self.on_adv_product_changed(product)
        self.adv_model_combo.setCurrentText(model)
        self.update_available_models_list()

        # Unblock signals
        self.pref_product_combo.blockSignals(False)
        self.pref_model_combo.blockSignals(False)
        self.adv_product_combo.blockSignals(False)
        self.adv_model_combo.blockSignals(False)

        # Update displays
        self.update_current_model_display()
        self.update_prompt_preview()

        # Load prompt editor
        self.on_prompt_type_changed(0)

    def refresh_textbook_list(self):
        """Refresh textbook file list"""
        self.textbook_list.clear()
        textbook_dir = self.course_detail_mgr.get_textbook_dir()

        if not os.path.exists(textbook_dir):
            return

        files = sorted([f for f in os.listdir(textbook_dir)
                       if os.path.isfile(os.path.join(textbook_dir, f))])

        for filename in files:
            self.textbook_list.addItem(filename)

    def refresh_learn_list(self):
        """Refresh learn materials list"""
        self.learn_list.clear()
        learn_dir = self.course_detail_mgr.get_learn_dir()

        if not os.path.exists(learn_dir):
            return

        files = []
        for item in os.listdir(learn_dir):
            item_path = os.path.join(learn_dir, item)
            if os.path.isfile(item_path):
                files.append(item)

        # Natural sort
        import re
        def natural_sort_key(s):
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

        for filename in sorted(files, key=natural_sort_key):
            # Check if report exists
            reports_dir = os.path.join(learn_dir, 'reports')
            base_name = os.path.splitext(filename)[0]
            report_path = os.path.join(reports_dir, f"{base_name}.md")
            has_report = os.path.exists(report_path)

            item_text = f"{'✅' if has_report else '⭕'} {filename}"
            self.learn_list.addItem(item_text)

    # ========== Event Handlers: Tab 1 ==========
    def on_open_textbook_folder(self):
        """Open textbook folder"""
        import subprocess
        folder = self.course_detail_mgr.get_textbook_dir()
        subprocess.run(['open', folder])

    def on_decon_textbook(self):
        """Decon textbook (call existing handler)"""
        from gui import qt_interact
        qt_interact.on_decon_textbook_clicked(self.canvas_app)

    def on_load_from_decon(self):
        """Load from decon (call existing handler)"""
        from gui import qt_interact
        qt_interact.on_load_from_decon_clicked(self.canvas_app)
        # Refresh lists after load
        self.refresh_learn_list()

    def on_open_learn_folder(self):
        """Open learn folder"""
        import subprocess
        folder = self.course_detail_mgr.get_learn_dir()
        subprocess.run(['open', folder])

    def on_batch_generate(self):
        """Batch generate all learn materials"""
        from PyQt6.QtWidgets import QMessageBox
        import threading

        learn_dir = self.course_detail_mgr.get_learn_dir()
        reports_dir = os.path.join(learn_dir, 'reports')

        # Get all files in Learn directory
        if not os.path.exists(learn_dir):
            QMessageBox.warning(self, "No Files", "Learn directory is empty.")
            return

        files = []
        for item in os.listdir(learn_dir):
            item_path = os.path.join(learn_dir, item)
            if os.path.isfile(item_path):
                # Check if report already exists
                base_name = os.path.splitext(item)[0]
                report_path = os.path.join(reports_dir, f"{base_name}.md")
                if not os.path.exists(report_path):
                    files.append((item, item_path))

        if not files:
            QMessageBox.information(self, "All Done", "All files already have learning reports!")
            return

        # Confirm
        reply = QMessageBox.question(
            self,
            "Batch Generate",
            f"Generate learning reports for {len(files)} files?\n\n"
            f"Files:\n" + "\n".join([f"  • {f[0]}" for f in files[:10]]) +
            (f"\n  ... and {len(files) - 10} more" if len(files) > 10 else ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Create single console
        from gui.qt_interact import _create_console_tab
        console = _create_console_tab(self.canvas_app.main_window.consoleTabWidget, "Batch Learn")

        def run_batch():
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
            from learn_material import learn_material

            console.append("=" * 80)
            console.append(f"🚀 Batch Learn: {len(files)} files")
            console.append(f"Course: {self.course_detail_mgr.get_course_name()}")
            console.append("=" * 80)
            console.append("")

            success_count = 0
            failed_files = []

            for i, (filename, file_path) in enumerate(files, 1):
                console.append(f"[{i}/{len(files)}] Processing: {filename}")
                console.append("-" * 80)

                try:
                    report_path = learn_material(
                        file_path,
                        self.course_detail_mgr.course_dir,
                        console,
                        use_preferences=True
                    )

                    if report_path:
                        success_count += 1
                        console.append(f"✅ [{i}/{len(files)}] Success: {filename}\n")
                    else:
                        failed_files.append(filename)
                        console.append(f"❌ [{i}/{len(files)}] Failed: {filename}\n")

                except Exception as e:
                    failed_files.append(filename)
                    console.append(f"❌ [{i}/{len(files)}] Error: {filename}")
                    console.append(f"   {str(e)}\n")

            # Final summary
            console.append("=" * 80)
            console.append("📊 Batch Learn Summary")
            console.append("=" * 80)
            console.append(f"✅ Success: {success_count}/{len(files)}")
            if failed_files:
                console.append(f"❌ Failed:  {len(failed_files)}/{len(files)}")
                console.append("")
                console.append("Failed files:")
                for f in failed_files:
                    console.append(f"  • {f}")

            console.append("=" * 80)

            # Show notification
            from gui.toast_notification import show_toast
            if failed_files:
                show_toast(
                    self.canvas_app,
                    f"批量生成完成\n成功: {success_count}, 失败: {len(failed_files)}",
                    'warning',
                    5000
                )
            else:
                show_toast(
                    self.canvas_app,
                    f"批量生成全部成功！\n共 {success_count} 个文件",
                    'success',
                    5000
                )

            # Refresh list
            self.refresh_learn_list()

        # Start batch in background
        threading.Thread(target=run_batch, daemon=True).start()

    # ========== Event Handlers: Tab 2 ==========
    def on_pref_product_changed(self, product):
        """Product changed in preferences tab"""
        # Block signals to avoid recursive calls
        self.pref_model_combo.blockSignals(True)
        self.pref_model_combo.clear()
        models = get_available_models(product)
        self.pref_model_combo.addItems(models)
        self.pref_model_combo.blockSignals(False)

        # Save immediately
        set_product(product)

        # Auto-select first model (Auto)
        if models:
            self.pref_model_combo.setCurrentIndex(0)
            set_model(models[0])

        # Update current model display
        self.update_current_model_display()

        # Sync to Tab3
        self.adv_product_combo.blockSignals(True)
        self.adv_product_combo.setCurrentText(product)
        self.adv_product_combo.blockSignals(False)
        self.on_adv_product_changed(product)

        # Show toast notification
        try:
            resolved_product, resolved_model = get_resolved_product_model()
            from gui.toast_notification import show_toast
            show_toast(self.canvas_app, f"Product 已更改为 {product}\n当前模型: {resolved_model}", 'success', 3000)
        except Exception as e:
            from gui.toast_notification import show_toast
            show_toast(self.canvas_app, f"Product 已更改为 {product}", 'success', 3000)

    def on_pref_model_changed(self, model):
        """Model changed in preferences tab"""
        if not model:  # Ignore empty string
            return

        # Save immediately
        set_model(model)

        # Update current model display
        self.update_current_model_display()

        # Sync to Tab3
        self.adv_model_combo.blockSignals(True)
        self.adv_model_combo.setCurrentText(model)
        self.adv_model_combo.blockSignals(False)

        # Show toast notification
        try:
            resolved_product, resolved_model = get_resolved_product_model()
            from gui.toast_notification import show_toast
            if model == 'Auto':
                show_toast(self.canvas_app, f"Model 设为 Auto\n实际使用: {resolved_model}", 'success', 3000)
            else:
                show_toast(self.canvas_app, f"Model 已更改为 {model}", 'success', 3000)
        except Exception as e:
            from gui.toast_notification import show_toast
            show_toast(self.canvas_app, f"Model 已更改为 {model}", 'success', 3000)

    def update_current_model_display(self):
        """Update the current model display label"""
        try:
            product, model = get_resolved_product_model()
            self.current_model_label.setText(f"{product}: {model}")
        except Exception as e:
            self.current_model_label.setText(f"Error: {e}")

    def update_prompt_preview(self):
        """Update prompt preview in Tab 2"""
        # Get current prompt type based on common usage (default to PDF)
        prompt_type = 'pdf'
        custom_prompt = self.prefs.get('prompts', {}).get(prompt_type)

        if custom_prompt:
            self.prompt_preview.setPlainText(custom_prompt)
        else:
            # Show default prompt
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
            from learn_material import DEFAULT_PDF_PROMPT
            self.prompt_preview.setPlainText(DEFAULT_PDF_PROMPT)

    def on_reset_prompt(self):
        """Reset all prompts to default"""
        reply = QMessageBox.question(self, "Reset Prompt",
                                     "Reset all prompt templates to default?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.prefs['prompts'] = {'text': None, 'pdf': None, 'csv': None}
            save_preferences(self.prefs)
            self.update_prompt_preview()
            self.on_prompt_type_changed(self.prompt_type_combo.currentIndex())

    # ========== Event Handlers: Tab 3 ==========
    def on_adv_product_changed(self, product):
        """Product changed in advanced tab (internal, no saving)"""
        self.adv_model_combo.blockSignals(True)
        self.adv_model_combo.clear()
        models = get_available_models(product, use_cache=True)
        self.adv_model_combo.addItems(models)
        self.adv_model_combo.blockSignals(False)
        self.update_available_models_list()

    def on_adv_product_changed_handler(self, product):
        """Product changed in advanced tab (user action)"""
        # Update models list
        self.on_adv_product_changed(product)

        # Save immediately
        set_product(product)

        # Auto-select first model (Auto)
        models = get_available_models(product, use_cache=True)
        if models:
            self.adv_model_combo.setCurrentIndex(0)
            set_model(models[0])

        # Sync to Tab2
        self.pref_product_combo.blockSignals(True)
        self.pref_product_combo.setCurrentText(product)
        self.pref_product_combo.blockSignals(False)
        self.on_pref_product_changed(product)

        # Show toast
        try:
            resolved_product, resolved_model = get_resolved_product_model()
            from gui.toast_notification import show_toast
            show_toast(self.canvas_app, f"Product 已更改为 {product}\n当前模型: {resolved_model}", 'success', 3000)
        except:
            from gui.toast_notification import show_toast
            show_toast(self.canvas_app, f"Product 已更改为 {product}", 'success', 3000)

    def on_adv_model_changed(self, model):
        """Model changed in advanced tab (user action)"""
        if not model:  # Ignore empty string
            return

        # Save immediately
        set_model(model)

        # Sync to Tab2
        self.pref_model_combo.blockSignals(True)
        self.pref_model_combo.setCurrentText(model)
        self.pref_model_combo.blockSignals(False)
        self.update_current_model_display()

        # Show toast
        try:
            resolved_product, resolved_model = get_resolved_product_model()
            from gui.toast_notification import show_toast
            if model == 'Auto':
                show_toast(self.canvas_app, f"Model 设为 Auto\n实际使用: {resolved_model}", 'success', 3000)
            else:
                show_toast(self.canvas_app, f"Model 已更改为 {model}", 'success', 3000)
        except:
            from gui.toast_notification import show_toast
            show_toast(self.canvas_app, f"Model 已更改为 {model}", 'success', 3000)

    def update_available_models_list(self):
        """Update available models list display"""
        product = self.adv_product_combo.currentText()
        models = get_available_models(product, use_cache=True)
        self.available_models_list.setPlainText('\n'.join(models))

    def on_refresh_models(self):
        """Refresh model lists from API"""
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(self, "Refresh Models",
                                     "This will fetch the latest model list from Gemini and Claude APIs.\n\n"
                                     "Continue?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            from learn_preferences import refresh_available_models

            # Show loading message
            self.available_models_list.setPlainText("⏳ Fetching from API...")

            # Refresh in background (simple approach: just do it directly)
            refresh_available_models()

            # Reload combos
            current_product = self.adv_product_combo.currentText()
            self.adv_model_combo.clear()
            models = get_available_models(current_product, use_cache=True)
            self.adv_model_combo.addItems(models)

            # Update display
            self.update_available_models_list()

            QMessageBox.information(self, "Success", "Model lists refreshed successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh models:\n{e}")

    def on_prompt_type_changed(self, index):
        """Prompt type changed in advanced tab"""
        prompt_types = ['text', 'pdf', 'csv']
        prompt_type = prompt_types[index]

        custom_prompt = self.prefs.get('prompts', {}).get(prompt_type)

        if custom_prompt:
            self.prompt_editor.setPlainText(custom_prompt)
        else:
            # Load default prompt
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
            from learn_material import DEFAULT_TEXT_PROMPT, DEFAULT_PDF_PROMPT, DEFAULT_CSV_PROMPT

            defaults = {
                'text': DEFAULT_TEXT_PROMPT,
                'pdf': DEFAULT_PDF_PROMPT,
                'csv': DEFAULT_CSV_PROMPT
            }
            self.prompt_editor.setPlainText(defaults[prompt_type])

    def on_save_all(self):
        """Save all settings (now mainly for prompts, since product/model are auto-saved)"""
        # Save current prompt
        prompt_types = ['text', 'pdf', 'csv']
        prompt_type = prompt_types[self.prompt_type_combo.currentIndex()]
        prompt_text = self.prompt_editor.toPlainText().strip()

        # Only save if different from default
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from learn_material import DEFAULT_TEXT_PROMPT, DEFAULT_PDF_PROMPT, DEFAULT_CSV_PROMPT

        defaults = {
            'text': DEFAULT_TEXT_PROMPT,
            'pdf': DEFAULT_PDF_PROMPT,
            'csv': DEFAULT_CSV_PROMPT
        }

        from learn_preferences import set_prompt
        if prompt_text != defaults[prompt_type]:
            set_prompt(prompt_type, prompt_text)
        else:
            set_prompt(prompt_type, None)

        # Update Tab 2
        self.update_prompt_preview()

        from gui.toast_notification import show_toast
        show_toast(self.canvas_app, f"Prompt 模板已保存 ({prompt_type})", 'success', 3000)

    def on_reset_prompt_type(self):
        """Reset current prompt type to default"""
        reply = QMessageBox.question(self, "Reset Template",
                                     "Reset this template to default?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.on_prompt_type_changed(self.prompt_type_combo.currentIndex())

    def on_test_prompt(self):
        """Test current prompt"""
        QMessageBox.information(self, "Test Prompt",
                               "Prompt test feature coming soon!\n\n"
                               "This will allow you to test your prompt with a sample file.")
