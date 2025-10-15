"""HTML Processor - Handles HTML to Markdown conversion and special page parsing (6 methods)"""
import sys, os, json, re
import requests
import html2text
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import config


class HTMLProcessor:
    """Handles HTML processing operations"""

    def __init__(self, app):
        """
        Args:
            app: CanvasApp instance
        """
        self.app = app

    def create_session(self):
        """Create a requests session with Canvas cookies"""
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
        has_modules_keyword = 'modules' in html_text.lower()
        if not has_modules_keyword:
            return False
        has_modules_dom = soup.find('div', id='context_modules') or soup.find('div', class_=lambda x: x and 'context_modules' in x)
        has_modules_env = 'ENV.MODULES_PATH' in html_text or '"modules_path"' in html_text
        has_modules_url = '/courses/' in html_text and '/modules' in html_text and 'context_modules' in html_text
        return bool(has_modules_dom or has_modules_env or has_modules_url)

    def parse_special_page(self, name, html_text, soup):
        """Parse special pages (grades, modules)"""
        if 'grades' in name.lower():
            return self.parse_grades_page(html_text, soup)
        elif self.is_modules_page(html_text, soup):
            return self.parse_modules_page(html_text, soup)
        return None

    def parse_grades_page(self, html_text, soup):
        """Parse grades page and extract submissions"""
        try:
            start = html_text.find('ENV = {')
            if start == -1:
                return "**Error:** No ENV found"
            bc, pos = 0, html_text.find('{', start)
            for i, c in enumerate(html_text[pos:], pos):
                if c == '{':
                    bc += 1
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

    def parse_modules_page(self, html_text, soup):
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
