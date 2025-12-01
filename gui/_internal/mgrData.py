"""Data management for GUI"""
import os, json, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

class DataManager:
    """Centralized data management"""
    def __init__(self):
        self.data = {'courses': [], 'todos': [], 'history_todos': [], 'files': []}

    def load_all(self):
        """Load all data from files"""
        self._load_courses()
        self._load_todos()
        self._load_history_todos()
        self._load_files()

    def _load_courses(self):
        if os.path.exists(config.COURSE_FILE):
            try:
                with open(config.COURSE_FILE, 'r', encoding='utf-8') as f:
                    self.data['courses'] = json.load(f).get('courses', [])
            except (json.JSONDecodeError, IOError, KeyError):
                pass

    def _load_todos(self):
        tf = config.TODOS_FILE
        if os.path.exists(tf):
            try:
                with open(tf, 'r', encoding='utf-8') as f:
                    self.data['todos'] = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def _load_history_todos(self):
        hf = config.HIS_TODO_FILE
        if os.path.exists(hf):
            try:
                with open(hf, 'r', encoding='utf-8') as f:
                    self.data['history_todos'] = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def _load_files(self):
        if os.path.exists(config.TODO_DIR):
            self.data['files'] = [f for f in os.listdir(config.TODO_DIR) if os.path.isdir(os.path.join(config.TODO_DIR, f))]

    def get(self, key):
        """Get data by key"""
        return self.data.get(key, [])

    def classify_todo(self, todo):
        """Classify TODO and return metadata"""
        ad, url = todo.get('assignment_details', {}), todo.get('redirect_url', '').lower()
        types = ad.get('type', [])
        is_quiz, is_disc = 'quiz' in url, 'discussion' in url
        is_auto = any(t in types for t in ['online_quiz', 'online_upload', 'online_text_entry', 'discussion_topic'])
        is_hw = not (is_quiz or is_disc)

        # Determine if truly open for submission
        is_open = not ad.get('submitted', False)  # Not submitted

        # Check if locked
        if ad.get('locked_for_user', False):
            is_open = False

        # For quizzes, check if attempts remain
        if is_quiz and 'quiz_metadata' in ad:
            qm = ad['quiz_metadata']
            # If locked or no attempts left, not open
            if qm.get('locked_for_user', False):
                is_open = False
            elif qm.get('attempts_left', 1) <= 0:
                is_open = False

        return {
            'is_quiz': is_quiz, 'is_discussion': is_disc,
            'is_automatable': is_auto, 'is_homework': is_hw, 'is_open': is_open,
            'dots': {'homework': is_hw, 'quiz': is_quiz, 'discussion': is_disc, 'automatable': is_auto}
        }
