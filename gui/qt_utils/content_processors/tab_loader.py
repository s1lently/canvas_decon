"""Tab Loader - Handles tab content loading and caching"""
import sys, os, threading, re
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import config
from gui.qt_utils.content_processors.html_processor import HTMLProcessor


class TabLoader:
    """Handles tab loading operations"""

    def __init__(self, app, course_detail_mgr):
        """
        Args:
            app: CanvasApp instance
            course_detail_mgr: CourseDetailManager instance
        """
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
                except:
                    pass
        threading.Thread(target=worker, daemon=True).start()

    def load_or_fetch_tab(self, tab_name, url):
        """Load tab content from cache or fetch from server"""
        safe_tab_name = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in tab_name)
        md_path = os.path.join(self.course_detail_mgr.course_dir, 'Tabs', f"{safe_tab_name}.md")
        if os.path.exists(md_path):
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    self.app.tab_content_signal.update_html.emit(f"MARKDOWN:{f.read()}")
            except Exception as e:
                self.app.course_detail_window.detailView.setHtml(f"<h2 style='color: #ef4444;'>Error</h2><p>{e}</p>")
        else:
            self.app.course_detail_window.detailView.setHtml(f"<h2 style='color: #eab308;'>Loading...</h2><p>Fetching {tab_name}...</p>")
            self.fetch_tab_content(tab_name, url)

    def fetch_tab_content(self, tab_name, url):
        """Fetch tab content from server in background thread"""
        def fetch_worker():
            try:
                session = self.processor.create_session()
                print(f"[INFO] Fetching {tab_name} from {url}")
                response = session.get(url, timeout=10)
                response.raise_for_status()
                if response.history:
                    print(f"[INFO] Server redirects detected for {tab_name}")
                if "window.location.href" in response.text:
                    js_redirect = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", response.text)
                    if js_redirect:
                        redirect_url = js_redirect.group(1)
                        if redirect_url.startswith('/'):
                            redirect_url = f"https://psu.instructure.com{redirect_url}"
                        print(f"[INFO] Following JS redirect to: {redirect_url}")
                        response = session.get(redirect_url, timeout=10)
                        response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                markdown = self.processor.parse_special_page(tab_name, response.text, soup) if ('grades' in url.lower() or 'Grades' in tab_name or self.processor.is_modules_page(response.text, soup)) else self.processor.html_to_md(soup)
                if markdown:
                    safe_tab_name = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in tab_name)
                    tabs_dir = os.path.join(self.course_detail_mgr.course_dir, 'Tabs')
                    os.makedirs(tabs_dir, exist_ok=True)
                    save_path = os.path.join(tabs_dir, f"{safe_tab_name}.md")
                    full_markdown = f"# {tab_name}\n\nSource: {url}\n\n---\n\n{markdown}"
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(full_markdown)
                    self.app.tab_content_signal.update_html.emit(f"MARKDOWN:{full_markdown}")
                    print(f"[INFO] Saved {tab_name} to {save_path}")
                else:
                    self.app.tab_content_signal.update_html.emit(f"<h2 style='color: #ef4444;'>Error</h2><p>No content found for {tab_name}</p>")
            except Exception as e:
                self.app.tab_content_signal.update_html.emit(f"<h2 style='color: #ef4444;'>Error</h2><p>Failed to fetch {tab_name}: {str(e)}</p>")
                print(f"[ERROR] Failed to fetch {tab_name}: {e}")
        threading.Thread(target=fetch_worker, daemon=True).start()
