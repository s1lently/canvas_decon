import json, os, re, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from markdownify import markdownify as md
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

def simplify_name(name):
    return ' '.join(name.split()[:2]) if len(name.split()) >= 2 else name.split()[0]

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', '_', name)

def remove_scripts(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for script in soup.find_all('script'):
        script.decompose()
    return str(soup)

def fetch_html(course_name, tab_name, url, html_file, cookies_list):
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=options)
    try:
        for cookie in cookies_list:
            driver.execute_cdp_cmd('Network.setCookie', {
                'name': cookie['name'], 'value': cookie['value'], 'domain': cookie['domain'],
                'path': cookie.get('path', '/'), 'httpOnly': cookie.get('httpOnly', False),
                'secure': cookie.get('secure', False), 'sameSite': cookie.get('sameSite', 'Lax'),
                'expires': cookie.get('expiry', int(time.time()) + 86400)
            })
        driver.get(url)
        html_content = remove_scripts(driver.page_source)
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return f"✓ HTML: {course_name}/{tab_name}"
    except Exception as e:
        return f"✗ HTML: {course_name}/{tab_name}: {str(e)[:30]}"
    finally:
        driver.quit()

def convert_to_md(course_name, course_full_name, tab_name, url, html_file, md_file):
    try:
        with open(html_file, encoding='utf-8') as f:
            html_content = f.read()
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {tab_name}\n\n**Course**: {course_full_name}\n**URL**: {url}\n\n---\n\n{md(html_content)}")
        return f"✓ MD: {course_name}/{tab_name}"
    except Exception as e:
        return f"✗ MD: {course_name}/{tab_name}: {str(e)[:30]}"

def main():
    with open('cookies.json') as f:
        cookies_list = json.load(f)
    with open('course.json', encoding='utf-8') as f:
        data = json.load(f)
    
    base_url = data['base_url']
    html_tasks, md_tasks = [], []
    
    for c in data['courses']:
        course_name = simplify_name(c['name'])
        course_dir = os.path.join(sanitize_filename(course_name), 'tabs')
        html_dir, md_dir = os.path.join(course_dir, 'html'), os.path.join(course_dir, 'md')
        os.makedirs(html_dir, exist_ok=True)
        os.makedirs(md_dir, exist_ok=True)
        
        for tab_name, tab_path in c['tabs'].items():
            safe_name = sanitize_filename(tab_name)
            html_file = os.path.join(html_dir, f"{safe_name}.html")
            md_file = os.path.join(md_dir, f"{safe_name}.md")
            url = f"{base_url}{tab_path}"
            html_tasks.append((course_name, tab_name, url, html_file, cookies_list))
            md_tasks.append((course_name, c['name'], tab_name, url, html_file, md_file))
    
    print("Phase 1: Fetching HTML (10 threads)...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        for future in as_completed([executor.submit(fetch_html, *t) for t in html_tasks]):
            print(future.result())
    
    print("\nPhase 2: Converting to MD (10 threads)...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        for future in as_completed([executor.submit(convert_to_md, *t) for t in md_tasks]):
            print(future.result())

if __name__ == '__main__':
    main()

