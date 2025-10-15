"""Course Detail Manager + Course Utils (merged)"""
import os, sys, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


def _sanitize_course_name(name):
    """Sanitize course name for folder - use only first 2 words"""
    # Extract first 2 words (e.g., "BISC 4" from "BISC 4, Section 001: Human Body")
    words = name.split()
    short_name = ' '.join(words[:2]) if len(words) >= 2 else name
    return "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in short_name).lower()


def _ensure_dirs(*paths):
    """Ensure all directories exist"""
    for p in paths:
        os.makedirs(p, exist_ok=True)


class CourseDetailManager:
    """Manages CourseDetail window data + folder structure"""

    def __init__(self, course_data, todos, history_todos=None):
        self.course = course_data
        self.todos = todos
        self.history_todos = history_todos or []
        self.course_id = str(course_data.get('id'))

        # Unified course folder structure: /Courses/CourseName_CourseID/
        safe_name = _sanitize_course_name(course_data.get('name', 'Unknown'))
        self.course_dir = os.path.join(config.COURSES_DIR, f"{safe_name}_{self.course_id}")
        self.syll_dir = os.path.join(self.course_dir, 'Syll')
        self.textbook_dir = os.path.join(self.course_dir, 'Files', 'Textbook')
        _ensure_dirs(self.course_dir, self.syll_dir, self.textbook_dir)

    def get_course_name(self):
        return self.course.get('name', 'Unknown')

    def get_categories(self):
        cats = ['Learn', 'Introduction', 'Homework (Upcoming)', 'Homework (Past)', 'Quiz (Upcoming)', 'Quiz (Past)']
        # Check if Discussions tab exists (check for 'Discussions' or 'discussions' in tabs)
        tabs = self.course.get('tabs', {})
        if 'Discussions' in tabs or any('discussion' in k.lower() for k in tabs.keys()):
            cats.extend(['Discussion (Upcoming)', 'Discussion (Past)'])
        cats.extend(['Syllabus', 'Tabs', 'Textbook'])
        return cats

    def get_items_for_category(self, category):
        if category == 'Learn':
            return self._get_learn()

        elif category == 'Introduction':
            return [{'name': self.get_course_name(), 'type': 'intro', 'data': self.course}]

        elif category == 'Homework (Upcoming)':
            return self._filter_by_url(lambda url: 'assignment' in url.lower() and 'quiz' not in url.lower(), use_history=False)

        elif category == 'Homework (Past)':
            return self._filter_by_url(lambda url: 'assignment' in url.lower() and 'quiz' not in url.lower(), use_history=True)

        elif category == 'Quiz (Upcoming)':
            return self._filter_by_url(lambda url: 'quiz' in url.lower(), use_history=False)

        elif category == 'Quiz (Past)':
            return self._filter_by_url(lambda url: 'quiz' in url.lower(), use_history=True)

        elif category == 'Discussion (Upcoming)':
            return self._filter_by_url(lambda url: 'discussion' in url.lower(), use_history=False)

        elif category == 'Discussion (Past)':
            return self._filter_by_url(lambda url: 'discussion' in url.lower(), use_history=True)

        elif category == 'Syllabus':
            return self._get_syllabus()

        elif category == 'Tabs':
            return self._get_tabs()

        elif category == 'Textbook':
            return self._get_textbook()

        return []

    def _filter_by_url(self, url_check, use_history=False):
        items = []
        source = self.history_todos if use_history else self.todos
        for todo in source:
            url = todo.get('redirect_url', '')
            match = re.search(r'/courses/(\d+)/', url)
            if not match or match.group(1) != self.course_id:
                continue
            if not url_check(url):
                continue

            items.append({
                'name': todo.get('name', 'Unknown'),
                'type': 'todo',
                'data': todo
            })
        return items

    def _get_syllabus(self):
        if 'Syllabus' not in self.course.get('tabs', {}):
            return []

        has_file = any(os.path.isfile(os.path.join(self.syll_dir, f)) for f in os.listdir(self.syll_dir)) if os.path.exists(self.syll_dir) else False

        return [{
            'name': 'Syllabus',
            'type': 'syllabus',
            'has_file': has_file,
            'data': {
                'url': f"{config.CANVAS_BASE_URL}{self.course['tabs']['Syllabus']}",
                'local_dir': self.syll_dir
            }
        }]

    def _get_tabs(self):
        items = []
        for tab_name, tab_url in self.course.get('tabs', {}).items():
            items.append({
                'name': tab_name,
                'type': 'tab',
                'data': {
                    'tab_name': tab_name,
                    'url': f"{config.CANVAS_BASE_URL}{tab_url}"
                }
            })
        return items

    def _get_textbook(self):
        if not os.path.exists(self.textbook_dir):
            return []

        files = [f for f in os.listdir(self.textbook_dir) if os.path.isfile(os.path.join(self.textbook_dir, f))]
        if not files:
            return [{'name': 'No textbook files', 'type': 'placeholder', 'data': {'folder': self.textbook_dir}}]

        items = []
        for filename in sorted(files):
            items.append({
                'name': filename,
                'type': 'textbook_file',
                'has_file': True,
                'data': {
                    'filename': filename,
                    'path': os.path.join(self.textbook_dir, filename),
                    'folder': self.textbook_dir
                }
            })
        return items

    def _get_learn(self):
        """Get files in Learn directory"""
        learn_dir = os.path.join(self.course_dir, 'Learn')

        if not os.path.exists(learn_dir):
            os.makedirs(learn_dir, exist_ok=True)
            os.makedirs(os.path.join(learn_dir, 'reports'), exist_ok=True)

        # Get all files in Learn directory (excluding reports subdirectory)
        files = []
        if os.path.exists(learn_dir):
            for item in os.listdir(learn_dir):
                item_path = os.path.join(learn_dir, item)
                if os.path.isfile(item_path):
                    files.append(item)

        if not files:
            return [{'name': 'No learning materials - drag files here or Load From Decon', 'type': 'placeholder', 'data': {'folder': learn_dir}}]

        items = []
        reports_dir = os.path.join(learn_dir, 'reports')

        # Natural sort (Chapter_1, Chapter_2, ..., Chapter_10)
        import re
        def natural_sort_key(s):
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

        for filename in sorted(files, key=natural_sort_key):
            # Check if report exists
            base_name = os.path.splitext(filename)[0]
            report_path = os.path.join(reports_dir, f"{base_name}.md")
            has_report = os.path.exists(report_path)

            items.append({
                'name': filename,
                'type': 'learn_file',
                'has_file': True,
                'has_report': has_report,
                'data': {
                    'filename': filename,
                    'path': os.path.join(learn_dir, filename),
                    'folder': learn_dir,
                    'report_path': report_path if has_report else None
                }
            })
        return items

    def get_learn_dir(self):
        """Get Learn directory path"""
        return os.path.join(self.course_dir, 'Learn')

    def get_syll_dir(self):
        return self.syll_dir

    def get_textbook_dir(self):
        return self.textbook_dir
