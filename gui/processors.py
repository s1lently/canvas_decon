"""Content Processors - HTML conversion, tab loading, preview loading"""
import os, json, re, threading
import requests
import html2text
from bs4 import BeautifulSoup

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


class HTMLProcessor:
    """HTML to Markdown conversion and special page parsing"""

    def __init__(self, app):
        self.app = app

    def create_session(self):
        """Create authenticated session"""
        with open(config.COOKIES_FILE) as f:
            cookies = {c['name']: c['value'] for c in json.load(f)}
        s = requests.Session()
        s.cookies.update(cookies)
        s.headers['User-Agent'] = 'Mozilla/5.0'
        return s

    def html_to_md(self, soup):
        """Convert HTML to Markdown"""
        content = soup.find('div', id='content') or soup.body
        if not content:
            return None
        h = html2text.HTML2Text()
        h.ignore_links = h.ignore_images = False
        h.body_width = 0
        return h.handle(str(content))

    def is_modules_page(self, html_text, soup):
        """Check if page is a modules page"""
        if 'modules' not in html_text.lower():
            return False
        has_dom = soup.find('div', id='context_modules') or soup.find('div', class_=lambda x: x and 'context_modules' in x)
        has_env = 'ENV.MODULES_PATH' in html_text or '"modules_path"' in html_text
        has_url = '/courses/' in html_text and '/modules' in html_text and 'context_modules' in html_text
        return bool(has_dom or has_env or has_url)

    def parse_special_page(self, name, html_text, soup):
        """Parse special pages (grades, modules)"""
        if 'grades' in name.lower():
            return self._parse_grades(html_text, soup)
        elif self.is_modules_page(html_text, soup):
            return self._parse_modules(html_text, soup)
        return None

    def _parse_grades(self, html_text, soup):
        """Parse grades page"""
        try:
            start = html_text.find('ENV = {')
            if start == -1:
                return "**Error:** No ENV found"
            bc, pos = 0, html_text.find('{', start)
            for i, c in enumerate(html_text[pos:], pos):
                if c == '{': bc += 1
                elif c == '}':
                    bc -= 1
                    if bc == 0:
                        env = json.loads(html_text[pos:i+1])
                        break
            else:
                return "**Error:** Incomplete ENV"
            subs = env.get('submissions', [])
            if not subs:
                return "**No grades**"
            md = ["## Grades\n", "| Assignment | Score | Status |", "|------------|-------|--------|"]
            for s in subs:
                aid = s.get('assignment_id', '')
                link = soup.find('a', href=re.compile(f'/assignments/{aid}'))
                name = link.get_text(strip=True) if link else f"Assignment {aid}"
                score = s.get('score')
                if s.get('excused'):
                    md.append(f"| {name} | Excused | Excused |")
                elif score:
                    md.append(f"| {name} | {score:.1f} | ✅ Graded |")
                else:
                    md.append(f"| {name} | - | ⏳ Not submitted |")
            return '\n'.join(md)
        except Exception as e:
            return f"**Error:** {e}"

    def _parse_modules(self, html_text, soup):
        """Parse modules page using Canvas API"""
        try:
            cid = re.search(r'/courses/(\d+)/', html_text)
            if not cid:
                return "**Error:** No course ID"
            s = self.create_session()
            s.headers['Accept'] = 'application/json+canvas-string-ids'
            r = s.get(f'https://psu.instructure.com/api/v1/courses/{cid.group(1)}/modules', params={'include[]': ['items']}, timeout=10)
            r.raise_for_status()
            md = [f"## Modules ({len(r.json())} total)\n"]
            for m in r.json():
                state = {'completed': '✅', 'started': '🔄', 'locked': '🔒'}.get(m.get('state'), '📦')
                md.append(f"\n### {state} {m.get('name', '?')}")
                items = m.get('items', [])
                if items:
                    md.append("| Item | Type | Local |")
                    md.append("|------|------|-------|")
                    for i in items:
                        title, typ = i.get('title', '?'), i.get('type', '?')
                        local = '🟢' if os.path.exists(os.path.join(config.TODO_DIR, title)) else '-'
                        md.append(f"| {title} | {typ} | {local} |")
            return '\n'.join(md)
        except Exception as e:
            return f"**Error:** {e}"


class TabLoader:
    """Tab content loading and caching"""

    def __init__(self, app, course_detail_mgr):
        self.app = app
        self.course_detail_mgr = course_detail_mgr
        self.processor = HTMLProcessor(app)

    def prefetch_all_tabs(self):
        """Prefetch all missing tabs in background"""
        def worker():
            tabs = self.course_detail_mgr.course.get('tabs', {})
            tabs_dir = os.path.join(self.course_detail_mgr.course_dir, 'Tabs')
            os.makedirs(tabs_dir, exist_ok=True)
            s = self.processor.create_session()
            for name, path in tabs.items():
                safe = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in name)
                md_path = os.path.join(tabs_dir, f"{safe}.md")
                if os.path.exists(md_path):
                    continue
                try:
                    url = f"{config.CANVAS_BASE_URL}{path}"
                    r = s.get(url, timeout=10)
                    soup = BeautifulSoup(r.text, 'html.parser')
                    md = self.processor.parse_special_page(name, r.text, soup) if 'grades' in name.lower() or self.processor.is_modules_page(r.text, soup) else self.processor.html_to_md(soup)
                    if md:
                        with open(md_path, 'w', encoding='utf-8') as f:
                            f.write(f"# {name}\n\nSource: {url}\n\n---\n\n{md}")
                        print(f"[INFO] Prefetched {name}")
                except Exception:
                    pass
        threading.Thread(target=worker, daemon=True).start()

    def load_or_fetch_tab(self, tab_name, url):
        """Load tab content from cache or fetch"""
        safe = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in tab_name)
        md_path = os.path.join(self.course_detail_mgr.course_dir, 'Tabs', f"{safe}.md")
        if os.path.exists(md_path):
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    self.app.tab_content_signal.update_html.emit(f"MARKDOWN:{f.read()}")
            except Exception as e:
                self.app.course_detail_window.detailView.setHtml(f"<h2 style='color: #ef4444;'>Error</h2><p>{e}</p>")
        else:
            self.app.course_detail_window.detailView.setHtml(f"<h2 style='color: #eab308;'>Loading...</h2><p>Fetching {tab_name}...</p>")
            self._fetch_tab(tab_name, url)

    def _fetch_tab(self, tab_name, url):
        """Fetch tab content in background"""
        def worker():
            try:
                s = self.processor.create_session()
                r = s.get(url, timeout=10)
                r.raise_for_status()
                # Handle JS redirects
                if "window.location.href" in r.text:
                    js_redirect = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", r.text)
                    if js_redirect:
                        redirect_url = js_redirect.group(1)
                        if redirect_url.startswith('/'):
                            redirect_url = f"https://psu.instructure.com{redirect_url}"
                        r = s.get(redirect_url, timeout=10)
                        r.raise_for_status()
                soup = BeautifulSoup(r.text, 'html.parser')
                md = self.processor.parse_special_page(tab_name, r.text, soup) if ('grades' in url.lower() or 'Grades' in tab_name or self.processor.is_modules_page(r.text, soup)) else self.processor.html_to_md(soup)
                if md:
                    safe = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in tab_name)
                    tabs_dir = os.path.join(self.course_detail_mgr.course_dir, 'Tabs')
                    os.makedirs(tabs_dir, exist_ok=True)
                    save_path = os.path.join(tabs_dir, f"{safe}.md")
                    full_md = f"# {tab_name}\n\nSource: {url}\n\n---\n\n{md}"
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(full_md)
                    self.app.tab_content_signal.update_html.emit(f"MARKDOWN:{full_md}")
                else:
                    self.app.tab_content_signal.update_html.emit(f"<h2 style='color: #ef4444;'>Error</h2><p>No content for {tab_name}</p>")
            except Exception as e:
                self.app.tab_content_signal.update_html.emit(f"<h2 style='color: #ef4444;'>Error</h2><p>Failed: {e}</p>")
        threading.Thread(target=worker, daemon=True).start()


class PreviewLoader:
    """AI preview loading for AutoDetail"""

    def __init__(self, app, auto_detail_mgr):
        self.app = app
        self.auto_detail_mgr = auto_detail_mgr

    def load_preview(self):
        """Load AI preview if files exist"""
        if not self.auto_detail_mgr:
            return None
        folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder')
        if not folder:
            return None
        output_dir = os.path.join(folder, 'auto', 'output')
        if not os.path.exists(output_dir):
            return None
        if self.auto_detail_mgr.is_quiz:
            return self.auto_detail_mgr.load_quiz_preview(output_dir)
        elif self.auto_detail_mgr.is_homework:
            return self.auto_detail_mgr.load_homework_preview(output_dir)
        return None

    def refresh_preview(self):
        """Refresh preview panel"""
        if not self.auto_detail_mgr:
            return
        preview_html = self.load_preview()
        if preview_html:
            self.app.auto_detail_window.aiPreviewView.setHtml(preview_html)
            self.app.auto_detail_window.previewStatusLabel.setText("Status: Preview loaded")
