"""Unified GitHub Dark Theme for Canvas LMS Automation"""

# === COLORS ===
COLORS = {
    'bg_primary': '#0a0a0a',
    'bg_secondary': '#111111',
    'bg_tertiary': '#1a1a1a',
    'bg_card': '#1e1e1e',
    'border': '#2a2a2a',
    'text_primary': '#ffffff',
    'text_secondary': '#b0b0b0',
    'text_muted': '#707070',
    'accent_blue': '#58a6ff',
    'accent_green': '#22c55e',
    'accent_purple': '#a371f7',
    'accent_orange': '#f59e0b',
    'accent_red': '#ef4444',
    'accent_cyan': '#39c5cf',
}

# Shorthand
C = COLORS


# === BASE STYLESHEET ===
def get_base_style():
    """Base stylesheet for all widgets"""
    return f"""
        QWidget {{
            background-color: {C['bg_primary']};
            color: {C['text_primary']};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
        }}
        QMainWindow {{
            background-color: {C['bg_primary']};
        }}
        QLabel {{
            background: transparent;
            border: none;
        }}
        QFrame {{
            border: none;
        }}
    """


# === LIST WIDGETS ===
def get_list_style():
    """Stylesheet for QListWidget"""
    return f"""
        QListWidget {{
            background-color: {C['bg_secondary']};
            border: none;
            border-radius: 8px;
            padding: 4px;
            outline: none;
        }}
        QListWidget::item {{
            background-color: transparent;
            border-radius: 6px;
            padding: 8px 12px;
            margin: 2px 4px;
        }}
        QListWidget::item:selected {{
            background-color: {C['bg_tertiary']};
            border: 1px solid {C['border']};
        }}
        QListWidget::item:hover:!selected {{
            background-color: {C['bg_card']};
        }}
    """


# === BUTTONS ===
def get_button_style(color='blue'):
    """Stylesheet for buttons"""
    accent = C.get(f'accent_{color}', C['accent_blue'])
    return f"""
        QPushButton {{
            background-color: {C['bg_tertiary']};
            color: {C['text_primary']};
            border: none;
            border-radius: 8px;
            padding: 10px 16px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {C['bg_card']};
        }}
        QPushButton:pressed {{
            background-color: {accent};
        }}
        QPushButton:disabled {{
            background-color: {C['bg_secondary']};
            color: {C['text_muted']};
        }}
    """


def get_primary_button_style(color='green'):
    """Stylesheet for primary action buttons"""
    accent = C.get(f'accent_{color}', C['accent_green'])
    return f"""
        QPushButton {{
            background-color: {accent};
            color: {C['text_primary']};
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {accent}dd;
        }}
        QPushButton:pressed {{
            background-color: {accent}bb;
        }}
    """


# === TEXT AREAS ===
def get_text_browser_style():
    """Stylesheet for QTextBrowser/QTextEdit"""
    return f"""
        QTextBrowser, QTextEdit {{
            background-color: {C['bg_tertiary']};
            border: none;
            border-radius: 8px;
            padding: 12px;
            color: {C['text_primary']};
            selection-background-color: {C['accent_blue']};
        }}
    """


# === COMBOBOX ===
def get_combobox_style():
    """Stylesheet for QComboBox"""
    return f"""
        QComboBox {{
            background-color: {C['bg_tertiary']};
            border: none;
            border-radius: 8px;
            padding: 10px 14px;
            color: {C['text_primary']};
            min-height: 20px;
        }}
        QComboBox:hover {{
            background-color: {C['bg_card']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        QComboBox::down-arrow {{
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {C['text_secondary']};
            margin-right: 10px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {C['bg_secondary']};
            border: none;
            selection-background-color: {C['accent_blue']};
            color: {C['text_primary']};
        }}
    """


# === SCROLLBAR ===
def get_scrollbar_style():
    """Stylesheet for scrollbars"""
    return f"""
        QScrollBar:vertical {{
            background: {C['bg_secondary']};
            width: 10px;
            border-radius: 5px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {C['border']};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {C['text_muted']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {C['bg_secondary']};
            height: 10px;
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal {{
            background: {C['border']};
            border-radius: 5px;
            min-width: 30px;
        }}
    """


# === INPUT FIELDS ===
def get_input_style():
    """Stylesheet for QLineEdit"""
    return f"""
        QLineEdit {{
            background-color: {C['bg_tertiary']};
            border: 1px solid {C['border']};
            border-radius: 8px;
            padding: 10px 14px;
            color: {C['text_primary']};
        }}
        QLineEdit:focus {{
            border-color: {C['accent_blue']};
        }}
        QLineEdit:disabled {{
            background-color: {C['bg_secondary']};
            color: {C['text_muted']};
        }}
    """


# === TAB WIDGET ===
def get_tab_style():
    """Stylesheet for QTabWidget"""
    return f"""
        QTabWidget::pane {{
            background-color: {C['bg_secondary']};
            border: none;
            border-radius: 8px;
        }}
        QTabBar::tab {{
            background-color: {C['bg_tertiary']};
            color: {C['text_secondary']};
            padding: 10px 20px;
            border: none;
            border-radius: 8px 8px 0 0;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {C['bg_secondary']};
            color: {C['text_primary']};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {C['bg_card']};
        }}
    """


# === CHECKBOX ===
def get_checkbox_style():
    """Stylesheet for QCheckBox"""
    return f"""
        QCheckBox {{
            color: {C['text_primary']};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 2px solid {C['border']};
            background-color: {C['bg_tertiary']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {C['accent_blue']};
            border-color: {C['accent_blue']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {C['accent_blue']};
        }}
    """


# === COMBINED STYLESHEET ===
def get_app_stylesheet():
    """Complete stylesheet for the entire application"""
    return (
        get_base_style() +
        get_list_style() +
        get_button_style() +
        get_text_browser_style() +
        get_combobox_style() +
        get_scrollbar_style() +
        get_input_style() +
        get_tab_style() +
        get_checkbox_style()
    )


# === UTILITY FUNCTIONS ===
def apply_theme(widget):
    """Apply GitHub Dark theme to a widget"""
    widget.setStyleSheet(get_app_stylesheet())


def get_status_color(status):
    """Get color for status indicators"""
    return {
        'success': C['accent_green'],
        'warning': C['accent_orange'],
        'error': C['accent_red'],
        'info': C['accent_blue'],
        'muted': C['text_muted'],
    }.get(status, C['text_primary'])


def get_urgency_color(hours_left):
    """Get color based on deadline urgency"""
    if hours_left <= 0:
        return C['accent_red']
    elif hours_left <= 24:
        return C['accent_orange']
    elif hours_left <= 72:
        return C['accent_blue']
    return C['accent_green']
