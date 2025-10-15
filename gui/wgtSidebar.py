"""Global Sidebar Widget - Floating design with hover expand animation"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFrame, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont


class SidebarButton(QWidget):
    """Sidebar button with hover expand animation"""
    clicked = pyqtSignal()

    def __init__(self, icon, text, parent=None):
        super().__init__(parent)
        self.icon = icon
        self.text = text
        self.setFixedHeight(50)
        self._text_visible = False

        # Use absolute positioning for overlay effect
        self.setStyleSheet("background: transparent;")

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

        # Text label (initially hidden, positioned to the left of icon)
        self.text_label = QLabel(text, self)
        self.text_label.setFont(QFont('Arial', 11))
        self.text_label.setStyleSheet("""
            QLabel {
                color: #fff;
                background-color: #2a2a2a;
                padding: 6px 12px;
                border-radius: 8px;
            }
        """)
        self.text_label.adjustSize()
        self.text_label.setVisible(False)

    def resizeEvent(self, event):
        """Update text label position when widget resizes"""
        super().resizeEvent(event)
        # Position text label to the right of icon
        self.text_label.setGeometry(
            70,  # x: right after icon (5 + 60 + 5)
            10,  # y: vertically centered
            120, # width
            30   # height
        )

    def show_text(self, visible):
        """Show/hide text label (called by parent sidebar)"""
        self._text_visible = visible
        self.text_label.setVisible(visible)


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
            ('⚙️', 'Sitting', 'sitting')
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
        """Update tool buttons (extensible interface)

        Args:
            actions: List of dicts with 'icon', 'text', 'callback'
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

        # Create buttons for each action
        for action in actions:
            btn = SidebarButton(action['icon'], action['text'])
            btn.clicked.connect(action['callback'])
            self.tools_container.addWidget(btn)
            self.tool_buttons.append(btn)

    def _get_default_tools(self):
        """Default tool actions (simple version, extensible for future)"""
        from gui import utilQtInteract as qt_interact

        return [
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
