import requests, json, os, sys
from lxml import html
from urllib.parse import urljoin, unquote, urlparse
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config

# Configuration
BASE_QUIZ_URL = "https://psu.instructure.com/courses/2405803/quizzes/5363417"
COOKIES_FILE = config.COOKIES_FILE
QUIZ_RES_DIR = config.QUIZ_RES_DIR
GEMINI_API_KEY = config.GEMINI_API_KEY

def start_quiz(base_url, session):
    """Start or resume quiz, return response with questions page"""
    print(f"Starting quiz: {base_url}")
    parsed = urlparse(base_url)
    path_parts = parsed.path.split('/')
    course_id = path_parts[path_parts.index('courses') + 1]
    quiz_id = path_parts[path_parts.index('quizzes') + 1]
    
    # Try accessing base URL first
    response = session.get(base_url, timeout=20)
    doc = html.fromstring(response.content)
    if doc.xpath('//*[@id="questions"]'):
        return response
    
    # Try POST with CSRF token
    csrf_token = next((unquote(c.value) for c in session.cookies if c.name == '_csrf_token'), '')
    user_id = (doc.xpath('//meta[@name="current-user-id"]/@content') or ['7333037'])[0]
    
    response = session.post(
        f"https://psu.instructure.com/courses/{course_id}/quizzes/{quiz_id}/take",
        data={'user_id': user_id, '_method': 'post', 'authenticity_token': csrf_token},
        headers={'User-Agent': 'Mozilla/5.0', 'Referer': base_url},
        timeout=30, allow_redirects=True
    )
    
    if html.fromstring(response.content).xpath('//*[@id="questions"]'):
        print("✓ Quiz started successfully")
        return response
    print("❌ Failed to start quiz")
    return None

def parse_questions(doc):
    """Parse questions and download images in parallel"""
    img_dir = os.path.join(QUIZ_RES_DIR, 'images')
    os.makedirs(img_dir, exist_ok=True)
    download_tasks = []
    
    def download_img(url, path):
        try:
            open(path, 'wb').write(requests.get(url, timeout=10).content)
            return path
        except: return None
    
    questions = []
    for q_div in doc.xpath('//*[@id="questions"]/div[contains(@class, "question")]'):
        q_container = q_div.xpath('.//div[starts-with(@id, "question_")]')[0]
        q_id = q_container.get('id')
        q_text = q_container.xpath('.//div[contains(@class, "question_text")]')[0].text_content().strip()
        
        # Question images
        q_imgs = []
        for img in q_container.xpath('.//div[contains(@class, "question_text")]//img'):
            if img_url := img.get('src'):
                img_path = os.path.join(img_dir, f"q_{q_id}_{len(q_imgs)}.png")
                download_tasks.append((urljoin(BASE_QUIZ_URL, img_url), img_path))
                q_imgs.append(img_path)
        
        # Answers
        answers = []
        for ans_el in q_container.xpath('.//div[@class="answer" or contains(@class, "answer ") or contains(@class, " answer")]'):
            ans_input = ans_el.xpath('.//input[@type="radio"]')
            if not ans_input: continue
            
            ans_id = ans_input[0].get('value')
            ans_label = ans_el.xpath(f'.//label[@for="{ans_input[0].get("id")}"]')
            ans_text = (ans_label[0] if ans_label else ans_el.xpath('.//label')[0]).text_content().strip()
            
            # Answer images
            ans_imgs = []
            for img in ans_el.xpath('.//img'):
                if img_url := img.get('src'):
                    img_path = os.path.join(img_dir, f"a_{ans_id}_{len(ans_imgs)}.png")
                    download_tasks.append((urljoin(BASE_QUIZ_URL, img_url), img_path))
                    ans_imgs.append(img_path)
            
            answers.append({'id': ans_id, 'content': ans_text, 'images': ans_imgs if ans_imgs else None})
        
        questions.append({'id': q_id, 'content': q_text, 'images': q_imgs if q_imgs else None, 'answers': answers})
    
    # Download all images in parallel
    if download_tasks:
        print(f"⬇️  Downloading {len(download_tasks)} images...")
        with ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(lambda x: download_img(x[0], x[1]), download_tasks))
        print(f"✓ Downloaded {len(download_tasks)} images")
    
    return questions

def get_gemini_answers(questions):
    """Upload images and get answers from Gemini"""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    # Upload all images
    all_files = []
    img_map = {}
    print("\n📤 Uploading images to Gemini...")
    for q in questions:
        for img_path in (q.get('images') or []):
            if img_path not in img_map:
                try:
                    uploaded = genai.upload_file(path=str(img_path), display_name=os.path.basename(img_path))
                    img_map[img_path] = uploaded
                    all_files.append(uploaded)
                    print(f"  ↑ {os.path.basename(img_path)}")
                except: pass
        
        for ans in q['answers']:
            for img_path in (ans.get('images') or []):
                if img_path not in img_map:
                    try:
                        uploaded = genai.upload_file(path=str(img_path), display_name=os.path.basename(img_path))
                        img_map[img_path] = uploaded
                        all_files.append(uploaded)
                        print(f"  ↑ {os.path.basename(img_path)}")
                    except: pass
    
    print(f"✓ Uploaded {len(all_files)} images\n")
    
    # Build prompt
    q_data = {}
    for q in questions:
        opts = {}
        for ans in q['answers']:
            text = ans['content'] if ans['content'] else "[IMAGE]"
            if ans.get('images'):
                text += f" [Images: {', '.join([os.path.basename(i) for i in ans['images']])}]"
            opts[ans['id']] = text
        
        q_entry = {'question': q['content'], 'options': opts}
        if q.get('images'):
            q_entry['question_images'] = [os.path.basename(i) for i in q['images']]
        q_data[q['id']] = q_entry
    
    prompt = f"""Based on quiz questions and uploaded images, select best answer for each.
Return JSON: {{"question_id": "answer_id", ...}}

Questions:
{json.dumps(q_data, indent=2)}

Example: {{"question_97585716": "7574", "question_97585717": "5127"}}
"""
    
    print("Asking Gemini...")
    response = model.generate_content([prompt] + all_files)
    return json.loads(response.text.strip().replace('```json', '').replace('```', ''))

def save_files(questions, answers, html_content):
    """Save all output files"""
    os.makedirs(QUIZ_RES_DIR, exist_ok=True)
    
    # Original HTML
    open(os.path.join(QUIZ_RES_DIR, 'questions.html'), 'w', encoding='utf-8').write(html_content)
    
    # Questions MD
    with open(os.path.join(QUIZ_RES_DIR, 'questions.md'), 'w', encoding='utf-8') as f:
        for i, q in enumerate(questions):
            f.write(f"### Question {i+1} (ID: {q['id']})\n\n{q['content']}\n\n")
            if q.get('images'):
                f.write("**Images:** " + ", ".join([f"`{os.path.basename(i)}`" for i in q['images']]) + "\n\n")
            f.write("**Answers:**\n")
            for ans in q['answers']:
                f.write(f"- `{ans['id']}`: {ans['content'] or '[IMAGE]'}\n")
                if ans.get('images'):
                    f.write(f"  - Images: {', '.join([f'`{os.path.basename(i)}`' for i in ans['images']])}\n")
            f.write("\n---\n\n")
    
    # Questions with Answers
    with open(os.path.join(QUIZ_RES_DIR, 'QesWA.md'), 'w', encoding='utf-8') as f:
        f.write("# Quiz Questions with Answers\n\n")
        for i, q in enumerate(questions):
            f.write(f"### Question {i+1} (ID: {q['id']})\n\n{q['content']}\n\n")
            if q.get('images'):
                f.write("**Images:** " + ", ".join([f"`{os.path.basename(i)}`" for i in q['images']]) + "\n\n")
            
            selected = answers.get(q['id'])
            f.write("**Answers:**\n")
            for ans in q['answers']:
                mark = "✅ **[SELECTED]** " if ans['id'] == selected else ""
                f.write(f"- {mark}`{ans['id']}`: {ans['content'] or '[IMAGE]'}\n")
                if ans.get('images'):
                    f.write(f"  - Images: {', '.join([f'`{os.path.basename(i)}`' for i in ans['images']])}\n")
            f.write("\n---\n\n")
    
    print(f"✓ Saved files to {QUIZ_RES_DIR}/")

def submit_quiz(session, url, doc, questions, answers):
    """Submit quiz with answers"""
    # Check for unanswered
    unanswered = set(q['id'] for q in questions) - set(answers.keys())
    print(f"\n{'='*60}")
    print(f"Total: {len(questions)} | Answered: {len(answers)} | Unanswered: {len(unanswered)}")
    
    if unanswered:
        print(f"⚠️  Unanswered questions: {list(unanswered)[:3]}...")
        confirm = input("Type 'yes confirm' to submit anyway: ").strip().lower()
        if confirm != 'yes confirm':
            print("❌ Submission cancelled")
            return False
    else:
        print("✓ All answered")
        if input("Submit? (y/yes/ok/继续): ").strip().lower() not in ['y', 'yes', 'ok', '继续']:
            print("❌ Cancelled")
            return False
    
    # Build payload
    form = doc.xpath('//form[@id="submit_quiz_form"]')[0]
    payload = {inp.get('name'): inp.get('value', '') for inp in form.xpath('.//input') if inp.get('name')}
    payload.update(answers)
    
    # Submit
    print(f"{'='*60}")
    print("Submitting...")
    response = session.post(urljoin(url, form.get('action')), data=payload, timeout=30)
    
    open(os.path.join(QUIZ_RES_DIR, 'quiz_response.html'), 'w', encoding='utf-8').write(response.text)
    print("✅ Submitted successfully!")
    return True

def main():
    config.ensure_dirs()
    
    # Setup session
    cookies = {c['name']: c['value'] for c in json.load(open(COOKIES_FILE))}
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    # Start quiz
    response = start_quiz(BASE_QUIZ_URL, session)
    if not response: return
    
    doc = html.fromstring(response.content)
    
    # Parse questions
    print("\n--- Parsing Questions ---")
    questions = parse_questions(doc)
    print(f"✓ Parsed {len(questions)} questions")
    
    # Get answers
    print("\n--- Getting Answers from Gemini ---")
    answers = get_gemini_answers(questions)
    print(f"✓ Got {len(answers)} answers")
    
    # Save files
    save_files(questions, answers, response.text)
    
    # Submit
    submit_quiz(session, response.url, doc, questions, answers)

if __name__ == '__main__':
    main()

