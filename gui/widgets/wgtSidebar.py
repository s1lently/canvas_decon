"""Global Sidebar Widget - Floating design with hover expand animation"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFrame, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont


class SidebarToggle(QWidget):
    """Sidebar toggle item with label and IOSToggle widget"""

    def __init__(self, icon, text, toggle_widget, parent=None):
        super().__init__(parent)
        self.icon = icon
        self.text = text
        self.toggle = toggle_widget
        self.setFixedHeight(50)

        # Make clickable (will toggle the IOSToggle)
        self.setStyleSheet("background: transparent;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Icon label
        self.icon_label = QLabel(icon, self)
        self.icon_label.setGeometry(15, 0, 40, 50)
        self.icon_label.setFont(QFont('Arial', 20))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("color: #aaa;")

        # Text label (hidden initially)
        self.text_label = QLabel(text, self)
        self.text_label.setFont(QFont('Arial', 11))
        self.text_label.setStyleSheet("color: #fff; background: transparent;")
        self.text_label.setVisible(False)

        # Toggle widget (small size)
        self.toggle.setParent(self)
        self.toggle.setGeometry(155, 13, 35, 18)  # Smaller toggle at right edge when expanded
        self.toggle.setVisible(False)

    def resizeEvent(self, event):
        """Update positions when widget resizes"""
        super().resizeEvent(event)
        self.text_label.setGeometry(70, 15, 75, 20)
        self.toggle.setGeometry(155, 13, 35, 18)

    def show_text(self, visible):
        """Show/hide text and toggle (called by parent sidebar)"""
        self.text_label.setVisible(visible)
        self.toggle.setVisible(visible)

    def mousePressEvent(self, event):
        """Click anywhere to toggle"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle.setChecked(not self.toggle.isChecked())


class SidebarButton(QWidget):
    """Sidebar button with hover expand animation"""
    clicked = pyqtSignal()

    def __init__(self, icon, text, parent=None):
        super().__init__(parent)
        self.icon = icon
        self.text = text
        self.setFixedHeight(50)
        self._text_visible = False

        # Make entire widget clickable
        self.setStyleSheet("background: transparent;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Icon button (always visible)
        self.icon_btn = QPushButton(icon, self)
        self.icon_btn.setGeometry(5, 0, 60, 50)
        self.icon_btn.setFont(QFont('Arial', 20))
        self.icon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                color: #aaa;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
                color: #fff;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        self.icon_btn.clicked.connect(self.clicked.emit)

        # Text button (initially hidden, clickable)
        self.text_btn = QPushButton(text, self)
        self.text_btn.setFont(QFont('Arial', 11))
        self.text_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.text_btn.setStyleSheet("""
            QPushButton {
                color: #fff;
                background-color: #2a2a2a;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: 12px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #4a4a4a;
            }
        """)
        self.text_btn.clicked.connect(self.clicked.emit)
        self.text_btn.setVisible(False)

    def resizeEvent(self, event):
        """Update text button position when widget resizes"""
        super().resizeEvent(event)
        # Position text button to the right of icon
        self.text_btn.setGeometry(
            70,  # x: right after icon (5 + 60 + 5)
            10,  # y: vertically centered
            120, # width
            30   # height
        )

    def show_text(self, visible):
        """Show/hide text button (called by parent sidebar)"""
        self._text_visible = visible
        self.text_btn.setVisible(visible)


class GlobalSidebar(QWidget):
    """Right-side floating global sidebar with hover expand animation

    Design:
    - Floating overlay (doesn't occupy space)
    - Hover to expand with animation
    - Top section: Dynamic tools (extensible)
    - Bottom section: Fixed navigation
    """

    # Signals for navigation
    navigate = pyqtSignal(str)  # 'launch', 'main', 'auto', 'sitting'

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.tool_buttons = []
        self.nav_buttons = []  # Store navigation buttons
        self.collapsed_width = 70
        self.expanded_width = 200
        self._init_ui()

    def _init_ui(self):
        """Initialize sidebar UI"""
        # Don't use setFixedWidth - it blocks animation!
        self.setMinimumWidth(self.collapsed_width)
        self.setMaximumWidth(self.collapsed_width)  # Will be increased by animation
        self.setStyleSheet("""
            GlobalSidebar {
                background-color: rgba(26, 26, 26, 240);
                border-left: 2px solid #555;
            }
        """)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(8)

        # === TOP SECTION: Tools (extensible) ===
        self.tools_container = QVBoxLayout()
        self.tools_container.setSpacing(5)
        layout.addLayout(self.tools_container)

        # Initialize with default tools (can be updated later)
        self.update_tools(None)

        # === SEPARATOR ===
        layout.addSpacing(10)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #666; border: none;")
        separator.setFixedHeight(2)
        layout.addWidget(separator)
        layout.addSpacing(10)

        # === BOTTOM SECTION: Navigation (fixed) ===
        nav_items = [
            ('🏠', 'Launch', 'launch'),
            ('📋', 'Main', 'main'),
            ('⚡', 'Auto', 'auto'),
            ('⚙️', 'Settings', 'sitting')
        ]

        for icon, text, nav_id in nav_items:
            btn = SidebarButton(icon, text)
            # Fix lambda: no 'checked' parameter needed for custom signal
            btn.clicked.connect(lambda nid=nav_id: self.navigate.emit(nid))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        # Animation for minimumWidth (more reliable than maximumWidth)
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Connect finished signal once (for collapse lock)
        self._collapse_on_finish = False
        self.animation.finished.connect(self._on_animation_finished)

        # Update x position during animation to keep right-aligned
        def on_width_change(width):
            if self.parent():
                parent_width = self.parent().width()
                new_x = parent_width - width
                self.move(new_x, self.y())

        self.animation.valueChanged.connect(on_width_change)

    def _on_animation_finished(self):
        """Handle animation finished - lock max width if collapsing"""
        if self._collapse_on_finish:
            self.setMaximumWidth(self.collapsed_width)
            self._collapse_on_finish = False

    def enterEvent(self, event):
        """Expand on hover"""
        self._collapse_on_finish = False
        self.animation.stop()
        # Allow expansion by setting max width
        self.setMaximumWidth(self.expanded_width)
        # Animate minimum width to expand
        self.animation.setStartValue(self.minimumWidth())
        self.animation.setEndValue(self.expanded_width)
        self.animation.start()
        # Show all text labels
        for btn in self.tool_buttons + self.nav_buttons:
            btn.show_text(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Collapse on leave"""
        self.animation.stop()
        # Animate minimum width to collapse
        self.animation.setStartValue(self.minimumWidth())
        self.animation.setEndValue(self.collapsed_width)
        self._collapse_on_finish = True  # Lock max width after animation
        self.animation.start()
        # Hide all text labels
        for btn in self.tool_buttons + self.nav_buttons:
            btn.show_text(False)
        super().leaveEvent(event)

    def update_tools(self, actions=None):
        """Update tool buttons/toggles (extensible interface)

        Args:
            actions: List of dicts with:
                     - type: 'button' or 'toggle'
                     - icon: emoji string
                     - text: label text
                     - callback: function (for buttons)
                     - widget: IOSToggle widget (for toggles)
                     If None, use default fixed tools

        Future usage:
            handler.get_toolbar_actions() returns action list
            sidebar.update_tools(handler.get_toolbar_actions())
        """
        # Clear existing tool buttons
        for btn in self.tool_buttons:
            btn.deleteLater()
        self.tool_buttons.clear()

        # Use default tools if no actions provided
        if actions is None:
            actions = self._get_default_tools()

        # Create buttons/toggles for each action
        for action in actions:
            if action.get('type') == 'toggle':
                # Create toggle item
                item = SidebarToggle(action['icon'], action['text'], action['widget'])
                self.tools_container.addWidget(item)
                self.tool_buttons.append(item)
            else:
                # Create button item (default)
                btn = SidebarButton(action['icon'], action['text'])
                btn.clicked.connect(action['callback'])
                self.tools_container.addWidget(btn)
                self.tool_buttons.append(btn)

    def _get_default_tools(self):
        """Default tool actions (simple version, extensible for future)"""
        from gui.core import utilQtInteract as qt_interact
        from gui.widgets.wgtIOSToggle import IOSToggle

        # Create console toggle for sidebar
        if not hasattr(self.app, 'sidebar_console_toggle'):
            self.app.sidebar_console_toggle = IOSToggle(width=35, height=18)
            # Connect to console toggle handler
            self.app.sidebar_console_toggle.stateChanged.connect(
                self.app.main_handler.on_toggle_console_clicked
            )

        return [
            {
                'type': 'toggle',
                'icon': '💬',
                'text': 'Console',
                'widget': self.app.sidebar_console_toggle
            },
            {
                'icon': '🍪',
                'text': 'Get Cookie',
                'callback': lambda: qt_interact.on_get_cookie_clicked(
                    self.app.main_window.consoleTabWidget, self.app
                )
            },
            {
                'icon': '📝',
                'text': 'Get TODO',
                'callback': lambda: qt_interact.on_get_todo_clicked(
                    self.app.main_window.consoleTabWidget, self.app
                )
            },
            {
                'icon': '📚',
                'text': 'Get Course',
                'callback': lambda: qt_interact.on_get_course_clicked(
                    self.app.main_window.consoleTabWidget, self.app
                )
            },
            {
                'icon': '📖',
                'text': 'Get Syll All',
                'callback': lambda: qt_interact.on_gsyll_all_clicked(
                    self.app.main_window.consoleTabWidget
                )
            },
            {
                'icon': '🧹',
                'text': 'Clean',
                'callback': self.app.sitting_handler.show_clean_dialog
            }
        ]
