"""Signal Initializer - Handles all signal/slot bindings"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from gui import utilQtInteract as qt_interact


class SignalInitializer:
    """Handles signal/slot binding for CanvasApp"""

    @staticmethod
    def init_button_bindings(app):
        """Initialize all button click bindings"""
        mw = app.main_window
        sw = app.sitting_window
        aw = app.automation_window
        cdw = app.course_detail_window
        adw = app.auto_detail_window

        # === MAIN WINDOW ===
        mw.backBtn.clicked.connect(app.launcher_handler.show)
        mw.getCookieBtn.clicked.connect(lambda: qt_interact.on_get_cookie_clicked(mw.consoleTabWidget, app))
        mw.getTodoBtn.clicked.connect(lambda: qt_interact.on_get_todo_clicked(mw.consoleTabWidget, app))
        mw.getCourseBtn.clicked.connect(lambda: qt_interact.on_get_course_clicked(mw.consoleTabWidget, app))
        mw.gSyllAllBtn.clicked.connect(lambda: qt_interact.on_gsyll_all_clicked(mw.consoleTabWidget))
        mw.cleanBtn.clicked.connect(app.sitting_handler.show_clean_dialog)
        mw.automationTopBtn.clicked.connect(app.automation_handler.open_top)
        mw.sittingBtn.clicked.connect(app.sitting_handler.open)
        mw.openFolderBtn.clicked.connect(app.main_handler.on_open_folder_clicked)
        mw.courseDetailBtn.clicked.connect(app.course_detail_handler.open)

        # Main list connections
        mw.categoryList.currentRowChanged.connect(app.main_handler.on_category_changed)
        mw.itemList.currentRowChanged.connect(app.main_handler.on_item_changed)
        mw.itemList.itemChanged.connect(app.main_handler.on_checkbox_changed)
        mw.itemList.itemDoubleClicked.connect(app.main_handler.on_item_double_clicked)

        # Filter connections
        for f in [mw.filterHomework, mw.filterQuiz, mw.filterDiscussion, mw.filterAutomatable]:
            f.stateChanged.connect(app.main_handler.apply_filters)

        # Console tab close
        mw.consoleTabWidget.tabCloseRequested.connect(app.main_handler.close_tab)

        # === SITTING WINDOW ===
        sw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(app.stacked_widget, mw))
        sw.submitBtn.clicked.connect(lambda: qt_interact.on_submit_clicked(
            sw.accountInput, sw.passwordInput, sw.keyInput, app.stacked_widget, mw
        ))
        sw.saveApiBtn.clicked.connect(app.sitting_handler.save_api_key)
        sw.savePrefBtn.clicked.connect(lambda: app.sitting_handler.save_preference(sw.baseUrlInput.text()))

        # API key focus handlers
        original_gemini_focus = sw.geminiApiInput.focusInEvent
        def gemini_focus_wrapper(event):
            app.sitting_handler.on_gemini_api_focus()
            original_gemini_focus(event)
        sw.geminiApiInput.focusInEvent = gemini_focus_wrapper

        original_claude_focus = sw.claudeApiInput.focusInEvent
        def claude_focus_wrapper(event):
            app.sitting_handler.on_claude_api_focus()
            original_claude_focus(event)
        sw.claudeApiInput.focusInEvent = claude_focus_wrapper

        # Task management
        sw.refreshTasksBtn.clicked.connect(app.sitting_handler.refresh_tasks_table)
        sw.stopTaskBtn.clicked.connect(app.sitting_handler.stop_selected_task)
        sw.stopAllTasksBtn.clicked.connect(app.sitting_handler.stop_all_tasks)

        # === AUTOMATION WINDOW ===
        aw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(app.stacked_widget, mw))
        aw.getTodoBtn.clicked.connect(lambda: qt_interact.on_get_todo_clicked(aw.consoleTabWidget, app))
        aw.cleanBtn.clicked.connect(lambda: qt_interact.on_clean_clicked(aw.consoleTabWidget))

        # Automation tabs (4 tabs: Auto Open, Auto Close, All Automatable, All Items)
        tab_prefixes = ['automatableOpen', 'automatableClose', 'automatable', 'allItems']
        for tab_idx, prefix in enumerate(tab_prefixes):
            category_list = getattr(aw, f'{prefix}CategoryList')
            item_list = getattr(aw, f'{prefix}ItemList')

            # Category filter
            category_list.currentRowChanged.connect(
                lambda idx, ti=tab_idx: app.automation_handler.on_category_changed(idx, ti)
            )

            # Item selection
            item_list.currentRowChanged.connect(
                lambda idx, ti=tab_idx: app.automation_handler.on_item_changed(idx, ti)
            )

            # Checkbox changes
            item_list.itemChanged.connect(app.automation_handler.on_checkbox_changed)

            # Double-click to open AutoDetail
            item_list.itemDoubleClicked.connect(app.automation_handler.on_item_double_clicked)

        # Console tab close
        aw.consoleTabWidget.tabCloseRequested.connect(app.automation_handler.close_tab)

        # === COURSE DETAIL WINDOW ===
        cdw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(app.stacked_widget, mw))
        cdw.openSyllabusFolderBtn.clicked.connect(app.course_detail_handler.on_open_syllabus_folder_clicked)
        cdw.openTextbookFolderBtn.clicked.connect(app.course_detail_handler.on_open_textbook_folder_clicked)
        cdw.deconTextbookBtn.clicked.connect(app.course_detail_handler.on_decon_textbook_clicked)
        cdw.loadFromDeconBtn.clicked.connect(lambda: qt_interact.on_load_from_decon_clicked(app, cdw.consoleTabWidget))
        cdw.learnMaterialBtn.clicked.connect(lambda: qt_interact.on_learn_material_clicked(app, cdw.consoleTabWidget))
        cdw.itemList.itemDoubleClicked.connect(app.course_detail_handler.on_item_double_clicked)
        cdw.categoryList.currentRowChanged.connect(app.course_detail_handler.on_category_changed)
        cdw.itemList.currentRowChanged.connect(app.course_detail_handler.on_item_changed)

        # Drag and drop
        cdw.itemList.dragEnterEvent = app.course_detail_handler.drag_enter
        cdw.itemList.dragMoveEvent = app.course_detail_handler.drag_move
        cdw.itemList.dropEvent = app.course_detail_handler.drag_drop

        # Removed: ios_toggle_course_detail signal (moved to sidebar)

        # === AUTO DETAIL WINDOW ===
        adw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(app.stacked_widget, mw))
        adw.hwFolderBtn.clicked.connect(app.auto_detail_handler.on_auto_folder_clicked)
        adw.quizFolderBtn.clicked.connect(app.auto_detail_handler.on_auto_folder_clicked)
        adw.hwDebugBtn.clicked.connect(app.auto_detail_handler.on_hw_debug_clicked)
        adw.quizDebugBtn.clicked.connect(app.auto_detail_handler.on_quiz_debug_clicked)
        adw.hwAgainBtn.clicked.connect(app.auto_detail_handler.on_hw_again_clicked)
        adw.quizAgainBtn.clicked.connect(app.auto_detail_handler.on_quiz_again_clicked)
        adw.hwUploadPreviewBtn.clicked.connect(app.auto_detail_handler.on_hw_preview_clicked)
        adw.quizStartPreviewBtn.clicked.connect(app.auto_detail_handler.on_quiz_preview_clicked)
        adw.hwSubmitBtn.clicked.connect(app.auto_detail_handler.on_hw_submit_clicked)
        adw.quizSubmitBtn.clicked.connect(app.auto_detail_handler.on_quiz_submit_clicked)
        adw.viewDetailBtn.clicked.connect(app.auto_detail_handler.on_view_detail_clicked)

        # Model selection
        adw.productComboBox.addItems(['Gemini', 'Claude'])
        adw.productComboBox.currentTextChanged.connect(app.auto_detail_handler.on_product_changed)
        adw.modelComboBox.currentTextChanged.connect(app.auto_detail_handler.on_model_changed)
        app.auto_detail_handler.init_model_selection()

        # === LAUNCHER OVERLAY ===
        app.launcher_overlay.dashboardBtn.clicked.connect(app.launcher_handler.hide)
        app.launcher_overlay.automationBtn.clicked.connect(lambda: (
            app.launcher_handler.hide(),
            app.automation_handler.open_top()
        ))
        app.launcher_overlay.settingsBtn.clicked.connect(lambda: qt_interact.on_login_clicked(
            mw, app.stacked_widget, sw, app
        ))
        app.launcher_overlay.courseList.itemDoubleClicked.connect(app.launcher_handler.on_course_double_clicked)
        app.launcher_overlay.todoList.itemDoubleClicked.connect(app.launcher_handler.on_todo_double_clicked)

        # === TOGGLE CONNECTIONS ===
        for toggle in [app.ios_toggle_main] + app.ios_toggles_auto:
            toggle.stateChanged.connect(app.main_handler.on_toggle_console_clicked)

        app.history_toggle.stateChanged.connect(app.main_handler.on_history_toggle_clicked)

        # === SIDEBAR NAVIGATION ===
        def navigate_to(page_id):
            """Handle sidebar navigation"""
            if page_id == 'launch':
                # Launch is overlay on Main window - switch to Main first
                app.stacked_widget.setCurrentWidget(mw)
                app.launcher_handler.show()
            elif page_id == 'main':
                # Main = close launcher overlay and show pure Main window
                app.stacked_widget.setCurrentWidget(mw)
                app.launcher_handler.hide()
            elif page_id == 'auto':
                app.automation_handler.open_top()
            elif page_id == 'sitting':
                app.stacked_widget.setCurrentWidget(sw)

        app.sidebar.navigate.connect(navigate_to)

        # === INITIAL STATE ===
        # Load login info and API settings
        app.sitting_handler.load_current_login_info()
        app.sitting_handler.load_api_settings()

        # Hide consoles initially
        for w in [mw.consoleTabWidget, aw.consoleTabWidget, cdw.consoleTabWidget]:
            w.setVisible(False)

        for t in [app.ios_toggle_main] + app.ios_toggles_auto:
            t.setChecked(False)
