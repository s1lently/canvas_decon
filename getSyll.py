import requests, json, os, re, logging, html2text
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[
    logging.FileHandler('syllabus_extractor.log', 'w', encoding='utf-8'),
    logging.StreamHandler()
])
logger = logging.getLogger(__name__)

def simplify_course_name(full_name):
    if match := re.search(r'([A-Z]{2,5}\s+\d+[A-Z]?)', full_name): return match.group(1)
    return ' '.join(full_name.split()[:2]).replace(':', '')

class SyllabusExtractor:
    def __init__(self, course_id, simple_course_name):
        self.course_id, self.course_name = course_id, simple_course_name
        self.log_prefix, self.successes = f"[{self.course_name}]", []
        self.base_url, self.api_base = "https://psu.instructure.com", "https://psu.instructure.com/api/v1"
        with open('cookies.json') as f: self.cookies = {c['name']: c['value'] for c in json.load(f)}
        self.save_dir = f"{self.course_id}/syll"
        os.makedirs(self.save_dir, exist_ok=True)

    def _get_request(self, url):
        try:
            r = requests.get(url, cookies=self.cookies); r.raise_for_status(); return r
        except requests.HTTPError as e: logger.error(f"{self.log_prefix} Request failed for {url}: {e}")

    def _get_api(self, path):
        full_path = path if path.startswith('http') else f"{self.api_base}{'/' if not path.startswith('/') else ''}{path}"
        if response := self._get_request(full_path):
            return response.json() if response.headers.get('content-type', '').startswith('application/json') else None

    def _download_file(self, file_id, source):
        filename = (self._get_api(f"/files/{file_id}") or {}).get('filename')
        download_url = f"{self.base_url}/courses/{self.course_id}/files/{file_id}/download?download_frd=1"
        logger.info(f"{self.log_prefix} Attempting download from: {download_url}")
        if not (response := self._get_request(download_url)): return False

        if not filename and (cd := response.headers.get('content-disposition')):
            if match := re.search(r'filename="([^"]+)"', cd): filename = match.group(1)
        filename = filename or f"syllabus_{source}_{file_id}_NO_EXTENSION"
        
        save_path = os.path.join(self.save_dir, re.sub(r'[\\/*?:"<>|]', "_", filename))
        with open(save_path, 'wb') as f: f.write(response.content)
        logger.info(f"{self.log_prefix} Saved '{filename}' via {source}")
        self.successes.append(source); return True

    def method1_course_page(self):
        logger.info(f"{self.log_prefix} Starting Method 1 (Regex)")
        if not (response := self._get_request(f"{self.base_url}/courses/{self.course_id}")): return
        pattern = re.compile(r'Syllabus.*?href=\\"(https:\/\/psu\.instructure\.com\/courses\/' + re.escape(str(self.course_id)) + r'\/files\/(\d+)[^"]*)\\"', re.I | re.S)
        if match := pattern.search(response.text):
            logger.info(f"{self.log_prefix} Found syllabus via regex! File ID: {match.group(2)}")
            self._download_file(match.group(2), "M1 (Regex)")

    def method2_modules(self):
        logger.info(f"{self.log_prefix} Starting Method 2 (Modules)")
        if not (modules := self._get_api(f"/courses/{self.course_id}/modules")): return
        for module in modules:
            if (items_url := module.get('items_url')) and (items := self._get_api(items_url)):
                for item in items:
                    if 'syllabus' in item.get('title', '').lower() and item.get('type') == 'File':
                        if m := re.search(r'files/(\d+)', item.get('url', '')): self._download_file(m.group(1), "M2 (Modules)")

    def method3_tabs(self):
        logger.info(f"{self.log_prefix} Starting Method 3 (Tabs)")
        if not (tabs := self._get_api(f"/courses/{self.course_id}/tabs")): return
        for tab in tabs:
            if tab.get('id') == 'syllabus' and (full_url := tab.get('full_url')):
                if not (response := self._get_request(full_url)): continue
                soup = BeautifulSoup(response.text, 'html.parser')
                if any(self._download_file(m.group(1), "M3 (Tabs File)") for l in soup.find_all('a', href=re.compile(f'files/')) if 'syllabus' in l.text.lower() and (m := re.search(r'files/(\d+)', l.get('href', '')))): return

                content = soup.find('div', id='content') or soup.body
                if content and sum(1 for i in ['office hours', '@psu.edu', 'instructor'] if i in content.text.lower()) >= 2:
                    logger.info(f"{self.log_prefix} Saving embedded syllabus as markdown.")
                    save_path = os.path.join(self.save_dir, 'syllabus_m3_embedded.md')
                    with open(save_path, 'w', encoding='utf-8') as f: f.write(html2text.HTML2Text().handle(str(content)))
                    self.successes.append("M3 (Embedded MD)")

def run_extraction_for_course(course):
    course_id, full_name = course.get('id'), course.get('name', 'Unknown')
    if not course_id: return (None, [])
    simple_name = simplify_course_name(full_name)
    logger.info(f"--- Processing: {simple_name} ({course_id}) ---")
    extractor = SyllabusExtractor(course_id, simple_name)
    try:
        extractor.method1_course_page()
        if not extractor.successes: extractor.method2_modules()
        if not extractor.successes: extractor.method3_tabs()
    except Exception as e: logger.error(f"[{simple_name}] Unexpected error: {e}", exc_info=False)
    return (simple_name, extractor.successes)

if __name__ == '__main__':
    try:
        with open('course.json', 'r', encoding='utf-8') as f: courses = json.load(f)
        logger.info(f"Found {len(courses)} courses to process.")
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = [r for r in executor.map(run_extraction_for_course, courses) if r[0]]
        logger.info("--- All courses processed. ---")

        print("\n--- Syllabus Extraction Summary ---")
        found_count = sum(1 for _, s in results if s)
        for name, successes in sorted(results):
            status = f"[SUCCESS] {name}: Found via {', '.join(sorted(set(successes)))}" if successes else f"[ FAIL  ] {name}: No syllabus found."
            print(status)
        print(f"\nSummary: Found syllabus for {found_count} out of {len(results)} courses.")
    except FileNotFoundError: logger.error("course.json not found. Please run getCourses.py first.")
    except Exception as e: logger.error(f"An unexpected error occurred: {e}", exc_info=True)
