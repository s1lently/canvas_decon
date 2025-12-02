"""Modern AutoDetail Widget - GitHub Dark themed three-panel layout"""
import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QTextBrowser, QFrame, QSplitter,
    QScrollArea, QSizePolicy, QGridLayout, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

# Mission Control Dark theme colors (darker, cleaner)
COLORS = {
    'bg_primary': '#0a0a0a',      # Almost black
    'bg_secondary': '#111111',    # Very dark
    'bg_tertiary': '#1a1a1a',     # Dark cards
    'bg_card': '#1e1e1e',         # Card hover
    'border': '#2a2a2a',          # Subtle borders
    'text_primary': '#ffffff',    # Pure white
    'text_secondary': '#b0b0b0',  # Light gray
    'text_muted': '#707070',      # Muted gray
    'accent_blue': '#58a6ff',     # Blue
    'accent_green': '#22c55e',    # Brighter green
    'accent_purple': '#a371f7',   # Purple
    'accent_orange': '#f59e0b',   # Orange
    'accent_red': '#ef4444',      # Red
    'accent_cyan': '#39c5cf',     # Cyan
}


class ModernAutoDetailWidget(QWidget):
    """Modern three-panel AutoDetail widget with GitHub Dark theme"""

    # Signals for handler connection
    back_clicked = pyqtSignal()
    again_clicked = pyqtSignal()
    preview_clicked = pyqtSignal()
    folder_clicked = pyqtSignal()
    debug_clicked = pyqtSignal()
    submit_clicked = pyqtSignal()
    product_changed = pyqtSignal(str)
    model_changed = pyqtSignal(str)
    tab_changed = pyqtSignal(str)  # 'qeswa' or 'questions'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(self._get_base_stylesheet())
        self._init_ui()

    def _get_base_stylesheet(self):
        return f"""
            QWidget {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
                border: none;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QFrame {{
                border: none;
            }}
            QTextBrowser, QTextEdit {{
                background-color: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 8px;
                padding: 12px;
                color: {COLORS['text_primary']};
                selection-background-color: {COLORS['accent_blue']};
            }}
            QComboBox {{
                background-color: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                color: {COLORS['text_primary']};
                min-height: 20px;
            }}
            QComboBox:hover {{
                background-color: {COLORS['bg_card']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {COLORS['text_secondary']};
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_secondary']};
                border: none;
                selection-background-color: {COLORS['accent_blue']};
                color: {COLORS['text_primary']};
            }}
            QScrollBar:vertical {{
                background: {COLORS['bg_secondary']};
                width: 10px;
                border-radius: 5px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['text_muted']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """

    def _init_ui(self):
        """Initialize the three-panel UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === HEADER ===
        main_layout.addWidget(self._create_header())

        # === STATUS BAR ===
        main_layout.addWidget(self._create_status_bar())

        # === MAIN CONTENT (3 panels) ===
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Left Panel - Description
        content_layout.addWidget(self._create_left_panel(), 35)

        # Center Panel - Controls
        content_layout.addWidget(self._create_center_panel(), 35)

        # Right Panel - Preview
        content_layout.addWidget(self._create_right_panel(), 45)

        main_layout.addWidget(content, 1)

    def _create_header(self):
        """Create header with back button and course info"""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-bottom: 2px solid {COLORS['border']};
            }}
        """)
        header.setFixedHeight(70)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)

        # Left side: Back button + Course info
        left = QHBoxLayout()
        left.setSpacing(16)

        self.backBtn = self._create_button("Back", 'secondary', fixed_width=100)
        self.backBtn.clicked.connect(self.back_clicked.emit)
        left.addWidget(self.backBtn)

        # Course info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        self.courseNameLabel = QLabel("Course: CHEM 110")
        self.courseNameLabel.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {COLORS['accent_blue']}; background: transparent; border: none;")
        self.assignmentNameLabel = QLabel("Assignment: Homework_CH10")
        self.assignmentNameLabel.setStyleSheet(f"font-size: 14px; color: {COLORS['text_secondary']}; background: transparent; border: none;")
        info_layout.addWidget(self.courseNameLabel)
        info_layout.addWidget(self.assignmentNameLabel)
        left.addLayout(info_layout)

        layout.addLayout(left)
        layout.addStretch()

        # Right side: Badges
        badges = QHBoxLayout()
        badges.setSpacing(12)

        self.typeLabel = self._create_badge("Quiz", 'purple')
        self.dueDateLabel = self._create_badge("Due: 12/01/2025", 'red')
        badges.addWidget(self.typeLabel)
        badges.addWidget(self.dueDateLabel)

        layout.addLayout(badges)

        return header

    def _create_status_bar(self):
        """Create quiz status bar"""
        self.quizStatusBar = QFrame()
        self.quizStatusBar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        self.quizStatusBar.setFixedHeight(60)

        layout = QHBoxLayout(self.quizStatusBar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(24)

        # Status items - store both container and value label (no emoji icons)
        score_container, self.quizScoreLabel = self._create_status_item("S", "Score", "47.0 / 50.0", COLORS['accent_green'])
        attempts_container, self.quizAttemptsLabel = self._create_status_item("A", "Attempts", "1/3 (2 left)", COLORS['accent_blue'])
        questions_container, self.quizQuestionsLabel = self._create_status_item("Q", "Questions", "50", COLORS['accent_purple'])

        layout.addWidget(score_container)
        layout.addWidget(attempts_container)
        layout.addWidget(questions_container)
        layout.addStretch()

        # Status indicator (no emoji)
        self.quizTimeLabel = QLabel("Retryable")
        self.quizTimeLabel.setStyleSheet(f"""
            background: rgba(210, 153, 34, 0.15);
            color: {COLORS['accent_orange']};
            padding: 6px 14px;
            border-radius: 16px;
            font-size: 13px;
            font-weight: 500;
        """)
        layout.addWidget(self.quizTimeLabel)

        # Best score (hidden by default)
        self.quizBestLabel = QLabel("")
        self.quizBestLabel.setVisible(False)

        return self.quizStatusBar

    def _create_status_item(self, icon, label, value, color):
        """Create a status item widget. Returns (container_widget, value_label)"""
        widget = QWidget()
        widget.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Icon (letter in colored circle)
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            background-color: {color};
            color: white;
            padding: 0px;
            border-radius: 16px;
            font-size: 14px;
            font-weight: bold;
            border: none;
        """)
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']}; background: transparent; border: none;")
        value_widget = QLabel(value)
        value_widget.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS['text_primary']}; background: transparent; border: none;")
        value_widget.setObjectName(f"value_{label.lower()}")
        text_layout.addWidget(label_widget)
        text_layout.addWidget(value_widget)
        layout.addLayout(text_layout)

        return widget, value_widget

    def _create_left_panel(self):
        """Create left panel with description and reference files"""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Panel header
        header = self._create_panel_header("Description")
        layout.addWidget(header)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        # Info cards grid
        info_grid = QGridLayout()
        info_grid.setSpacing(12)

        self.pointsCard = self._create_info_card("Points", "50.0")
        self.statusCard = self._create_info_card("Status", "Submitted", highlight=True)
        info_grid.addWidget(self.pointsCard, 0, 0)
        info_grid.addWidget(self.statusCard, 0, 1)
        content_layout.addLayout(info_grid)

        # Description text
        self.assignmentDetailView = QTextBrowser()
        self.assignmentDetailView.setMinimumHeight(150)
        self.assignmentDetailView.setOpenExternalLinks(True)
        content_layout.addWidget(self.assignmentDetailView)

        # Reference files section
        ref_header = QLabel("Reference Files")
        ref_header.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['text_secondary']}; margin-top: 10px; background: transparent; border: none;")
        content_layout.addWidget(ref_header)

        self.refFilesView = QTextBrowser()
        self.refFilesView.setMaximumHeight(150)
        self.refFilesView.setOpenExternalLinks(True)
        content_layout.addWidget(self.refFilesView)

        content_layout.addStretch()
        layout.addWidget(content, 1)

        return panel

    def _create_center_panel(self):
        """Create center panel with model selector and action buttons"""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['bg_primary']};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Model selector card
        model_card = self._create_model_selector()
        layout.addWidget(model_card)

        # Action buttons grid
        actions = self._create_action_buttons()
        layout.addWidget(actions)

        # Prompt editor
        prompt_section = self._create_prompt_editor()
        layout.addWidget(prompt_section, 1)

        return panel

    def _create_model_selector(self):
        """Create model selector card"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border: none;
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("AI Model")
        title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS['text_secondary']}; background: transparent; border: none;")
        header.addWidget(title)
        header.addStretch()

        self.thinkingBadge = QLabel("Thinking Mode")
        self.thinkingBadge.setStyleSheet(f"""
            background: rgba(163, 113, 247, 0.15);
            color: {COLORS['accent_purple']};
            border: 1px solid {COLORS['accent_purple']};
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.3px;
        """)
        header.addWidget(self.thinkingBadge)
        layout.addLayout(header)

        # Dropdowns row
        row = QHBoxLayout()
        row.setSpacing(12)

        # Product dropdown
        product_layout = QVBoxLayout()
        product_label = QLabel("Product")
        product_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']}; background: transparent; border: none;")
        self.productComboBox = QComboBox()
        self.productComboBox.addItems(['Gemini', 'Claude'])
        self.productComboBox.currentTextChanged.connect(self.product_changed.emit)
        product_layout.addWidget(product_label)
        product_layout.addWidget(self.productComboBox)
        row.addLayout(product_layout, 1)

        # Model dropdown
        model_layout = QVBoxLayout()
        model_label = QLabel("Model")
        model_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']}; background: transparent; border: none;")
        self.modelComboBox = QComboBox()
        self.modelComboBox.currentTextChanged.connect(self.model_changed.emit)
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.modelComboBox)
        row.addLayout(model_layout, 2)

        layout.addLayout(row)

        # Thinking toggle widget (for Claude)
        self.thinkingToggleWidget = QWidget()
        self.thinkingToggleWidget.setStyleSheet("background: transparent; border: none;")
        thinking_layout = QHBoxLayout(self.thinkingToggleWidget)
        thinking_layout.setContentsMargins(0, 0, 0, 0)
        thinking_label = QLabel("Enable Thinking Mode")
        thinking_label.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']}; background: transparent; border: none;")
        thinking_layout.addWidget(thinking_label)
        thinking_layout.addStretch()
        # Placeholder for IOSToggle
        self.thinkingTogglePlaceholder = QWidget()
        self.thinkingTogglePlaceholder.setFixedSize(50, 24)
        self.thinkingTogglePlaceholder.setStyleSheet("background: transparent; border: none;")
        thinking_layout.addWidget(self.thinkingTogglePlaceholder)
        layout.addWidget(self.thinkingToggleWidget)
        self.thinkingToggleWidget.setVisible(False)

        return card

    def _create_action_buttons(self):
        """Create action buttons grid"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(12)

        # Row 1
        self.hwAgainBtn = self._create_button("Again", 'primary')
        self.quizAgainBtn = self.hwAgainBtn  # Alias
        self.hwAgainBtn.clicked.connect(self.again_clicked.emit)

        self.hwUploadPreviewBtn = self._create_button("Preview", 'secondary')
        self.quizStartPreviewBtn = self.hwUploadPreviewBtn  # Alias
        self.hwUploadPreviewBtn.clicked.connect(self.preview_clicked.emit)

        layout.addWidget(self.hwAgainBtn, 0, 0)
        layout.addWidget(self.hwUploadPreviewBtn, 0, 1)

        # Row 2
        self.hwFolderBtn = self._create_button("Folder", 'secondary')
        self.quizFolderBtn = self.hwFolderBtn  # Alias
        self.hwFolderBtn.clicked.connect(self.folder_clicked.emit)

        self.hwDebugBtn = self._create_button("Debug CLI", 'secondary')
        self.quizDebugBtn = self.hwDebugBtn  # Alias
        self.hwDebugBtn.clicked.connect(self.debug_clicked.emit)

        layout.addWidget(self.hwFolderBtn, 1, 0)
        layout.addWidget(self.hwDebugBtn, 1, 1)

        # Row 3: Submit (full width)
        self.hwSubmitBtn = self._create_button("Submit to Canvas", 'success')
        self.quizSubmitBtn = self.hwSubmitBtn  # Alias
        self.hwSubmitBtn.clicked.connect(self.submit_clicked.emit)
        layout.addWidget(self.hwSubmitBtn, 2, 0, 1, 2)

        return widget

    def _create_prompt_editor(self):
        """Create prompt editor section"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border: none;
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"background: transparent; border-bottom: 1px solid {COLORS['border']}; border-radius: 0;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 14)

        title = QLabel("Prompt Editor")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['text_secondary']}; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        reset_btn = QPushButton("Reset")
        reset_btn.setStyleSheet(self._get_small_button_style())
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(self._get_small_button_style())
        header_layout.addWidget(reset_btn)
        header_layout.addWidget(save_btn)

        layout.addWidget(header)

        # Editor
        self.promptEditBox = QTextEdit()
        self.promptEditBox.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_primary']};
                border: none;
                border-radius: 0;
                padding: 16px;
                font-family: 'SF Mono', 'Consolas', monospace;
                font-size: 13px;
                line-height: 1.6;
            }}
        """)
        layout.addWidget(self.promptEditBox, 1)

        return section

    def _create_right_panel(self):
        """Create right panel with preview"""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-left: 1px solid {COLORS['border']};
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tabs - functional switching between QesWA.md and questions.md
        tabs = QFrame()
        tabs.setStyleSheet(f"background: {COLORS['bg_tertiary']}; border-bottom: 1px solid {COLORS['border']};")
        tabs_layout = QHBoxLayout(tabs)
        tabs_layout.setContentsMargins(12, 0, 12, 0)
        tabs_layout.setSpacing(0)

        self.tabQesWA = QPushButton("QesWA.md")
        self.tabQuestions = QPushButton("questions.md")
        self._current_tab = 'qeswa'

        # Tab styles - minimalist with underline indicator
        self._tab_active_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-bottom: 2px solid {COLORS['accent_green']};
                padding: 10px 16px;
                font-size: 12px;
                font-weight: 600;
                color: {COLORS['text_primary']};
            }}
        """
        self._tab_inactive_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                padding: 10px 16px;
                font-size: 12px;
                font-weight: 500;
                color: {COLORS['text_muted']};
            }}
            QPushButton:hover {{
                color: {COLORS['text_secondary']};
                border-bottom: 2px solid {COLORS['border']};
            }}
        """

        self.tabQesWA.setStyleSheet(self._tab_active_style)
        self.tabQuestions.setStyleSheet(self._tab_inactive_style)
        self.tabQesWA.clicked.connect(lambda: self._switch_tab('qeswa'))
        self.tabQuestions.clicked.connect(lambda: self._switch_tab('questions'))

        tabs_layout.addWidget(self.tabQesWA)
        tabs_layout.addWidget(self.tabQuestions)
        tabs_layout.addStretch()

        layout.addWidget(tabs)

        # Preview content with custom CSS for question cards
        self.aiPreviewView = QTextBrowser()
        self.aiPreviewView.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLORS['bg_secondary']};
                border: none;
                padding: 20px;
            }}
        """)
        self.aiPreviewView.setOpenExternalLinks(True)
        # Set default stylesheet for HTML content
        self.aiPreviewView.document().setDefaultStyleSheet(self._get_preview_css())
        layout.addWidget(self.aiPreviewView, 1)

        # Status footer
        footer = QFrame()
        footer.setStyleSheet(f"background: transparent; border: none; border-top: 1px solid {COLORS['border']};")
        footer.setFixedHeight(50)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 0, 20, 0)

        self.previewStatusLabel = QLabel("Preview loaded - 50 questions")
        self.previewStatusLabel.setStyleSheet(f"font-size: 12px; color: {COLORS['text_muted']}; background: transparent; border: none;")
        footer_layout.addWidget(self.previewStatusLabel)
        footer_layout.addStretch()

        self.viewDetailBtn = self._create_button("View Detail", 'secondary', fixed_width=120)
        footer_layout.addWidget(self.viewDetailBtn)

        layout.addWidget(footer)

        return panel

    def _create_panel_header(self, title):
        """Create a panel header"""
        header = QFrame()
        header.setStyleSheet(f"background: transparent; border: none; border-bottom: 1px solid {COLORS['border']};")
        header.setFixedHeight(50)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        label = QLabel(title)
        label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {COLORS['text_secondary']};
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(label)
        layout.addStretch()

        return header

    def _create_info_card(self, label, value, highlight=False):
        """Create an info card"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 8px;
                padding: 6px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(1)

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"font-size: 10px; color: {COLORS['text_muted']}; background: transparent;")

        value_widget = QLabel(value)
        color = COLORS['accent_green'] if highlight else COLORS['text_primary']
        value_widget.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {color}; background: transparent;")

        layout.addWidget(label_widget)
        layout.addWidget(value_widget)

        return card

    def _create_badge(self, text, color_type):
        """Create a badge label with minimalist design"""
        colors = {
            'purple': (COLORS['accent_purple'], COLORS['bg_tertiary']),
            'red': (COLORS['accent_red'], COLORS['bg_tertiary']),
            'green': (COLORS['accent_green'], COLORS['bg_tertiary']),
            'blue': (COLORS['accent_blue'], COLORS['bg_tertiary']),
        }
        fg, bg = colors.get(color_type, colors['blue'])

        badge = QLabel(text)
        badge.setStyleSheet(f"""
            background: transparent;
            color: {fg};
            border: 1px solid {fg};
            padding: 1px 6px;
            border-radius: 2px;
            font-size: 9px;
            font-weight: 500;
            letter-spacing: 0.2px;
        """)
        badge.setFixedHeight(18)
        return badge

    def _create_button(self, text, style='secondary', fixed_width=None):
        """Create a styled button"""
        btn = QPushButton(text)

        styles = {
            'primary': f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1f6feb, stop:1 #58a6ff);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 14px 20px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #388bfd, stop:1 #79c0ff);
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1158c7, stop:1 #388bfd);
                }}
            """,
            'success': f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #238636, stop:1 #3fb950);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 14px 20px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2ea043, stop:1 #56d364);
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #196c2e, stop:1 #2ea043);
                }}
            """,
            'secondary': f"""
                QPushButton {{
                    background: {COLORS['bg_tertiary']};
                    color: {COLORS['text_primary']};
                    border: none;
                    border-radius: 12px;
                    padding: 14px 20px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {COLORS['bg_card']};
                }}
                QPushButton:pressed {{
                    background: {COLORS['bg_secondary']};
                }}
            """,
            'danger': f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #da3633, stop:1 #f85149);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 14px 20px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f85149, stop:1 #ff7b72);
                }}
            """,
        }

        btn.setStyleSheet(styles.get(style, styles['secondary']))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        if fixed_width:
            btn.setFixedWidth(fixed_width)

        return btn

    def _get_small_button_style(self):
        """Get style for small action buttons"""
        return f"""
            QPushButton {{
                background: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                color: {COLORS['text_secondary']};
            }}
            QPushButton:hover {{
                background: {COLORS['bg_card']};
                color: {COLORS['text_primary']};
            }}
        """

    def _get_preview_css(self):
        """Get CSS for HTML preview content (question cards styling)"""
        return f"""
            body {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_primary']};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                font-size: 14px;
                line-height: 1.6;
                margin: 0;
                padding: 0;
            }}
            h1, h2 {{
                color: {COLORS['accent_green']};
                font-weight: 600;
                margin: 0 0 16px 0;
            }}
            h1 {{ font-size: 24px; }}
            h2 {{ font-size: 18px; color: {COLORS['accent_blue']}; margin-top: 24px; }}
            h3 {{
                color: {COLORS['accent_purple']};
                font-size: 14px;
                font-weight: 600;
                margin: 16px 0 8px 0;
            }}
            .question-card {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
            }}
            .question-header {{
                display: flex;
                align-items: center;
                margin-bottom: 12px;
            }}
            .question-number {{
                background: linear-gradient(135deg, #8957e5, #a371f7);
                color: white;
                padding: 4px 10px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                margin-right: 12px;
            }}
            .question-id {{
                color: {COLORS['text_muted']};
                font-size: 12px;
                font-family: monospace;
            }}
            .question-text {{
                color: {COLORS['text_primary']};
                font-size: 14px;
                line-height: 1.6;
                margin-bottom: 16px;
            }}
            .answer-option {{
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 8px;
                background: transparent;
            }}
            .answer-option.selected {{
                background: rgba(63, 185, 80, 0.1);
                border: 1px solid rgba(63, 185, 80, 0.3);
            }}
            .answer-id {{
                color: {COLORS['accent_orange']};
                font-size: 11px;
                font-family: monospace;
                margin-right: 8px;
            }}
            .answer-text {{
                color: {COLORS['text_secondary']};
                font-size: 13px;
            }}
            .selected-marker {{
                color: {COLORS['accent_green']};
                font-weight: bold;
            }}
            ul {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            li {{
                padding: 8px 12px;
                margin: 4px 0;
                border-radius: 6px;
            }}
            li.selected {{
                background: rgba(63, 185, 80, 0.15);
                border-left: 3px solid {COLORS['accent_green']};
            }}
            code {{
                background: {COLORS['bg_tertiary']};
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'SF Mono', Consolas, monospace;
                font-size: 12px;
                color: {COLORS['accent_orange']};
            }}
            strong {{
                color: {COLORS['text_primary']};
                font-weight: 600;
            }}
            em {{
                color: {COLORS['accent_blue']};
            }}
            a {{
                color: {COLORS['accent_blue']};
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            hr {{
                border: none;
                border-top: 1px solid {COLORS['border']};
                margin: 16px 0;
            }}
            .file-item {{
                display: flex;
                align-items: center;
                padding: 12px 16px;
                background: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-bottom: 8px;
            }}
            .file-icon {{
                font-size: 20px;
                margin-right: 12px;
            }}
            .file-name {{
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
        """

    def _switch_tab(self, tab_name):
        """Switch between QesWA and questions tabs"""
        if tab_name == self._current_tab:
            return
        self._current_tab = tab_name
        if tab_name == 'qeswa':
            self.tabQesWA.setStyleSheet(self._tab_active_style)
            self.tabQuestions.setStyleSheet(self._tab_inactive_style)
        else:
            self.tabQesWA.setStyleSheet(self._tab_inactive_style)
            self.tabQuestions.setStyleSheet(self._tab_active_style)
        self.tab_changed.emit(tab_name)

    def update_available_tabs(self, has_qeswa, has_questions):
        """Update tab visibility based on available files"""
        self.tabQesWA.setVisible(has_qeswa)
        self.tabQuestions.setVisible(has_questions)
        # If current tab not available, switch to the other
        if not has_qeswa and self._current_tab == 'qeswa' and has_questions:
            self._switch_tab('questions')
        elif not has_questions and self._current_tab == 'questions' and has_qeswa:
            self._switch_tab('qeswa')

    # === Compatibility properties for existing handler ===
    @property
    def consoleTitle(self):
        """Compatibility: Return a dummy label"""
        return self._dummy_label

    @property
    def _dummy_label(self):
        if not hasattr(self, '_dummy'):
            self._dummy = QLabel()
        return self._dummy

    # Control widget visibility (quiz vs homework)
    @property
    def quizControlWidget(self):
        return self._quiz_control

    @property
    def hwControlWidget(self):
        return self._hw_control

    @property
    def _quiz_control(self):
        if not hasattr(self, '_qc'):
            self._qc = _DummyWidget()
        return self._qc

    @property
    def _hw_control(self):
        if not hasattr(self, '_hc'):
            self._hc = _DummyWidget()
        return self._hc


class _DummyWidget:
    """Dummy widget for compatibility"""
    def setVisible(self, visible):
        pass
