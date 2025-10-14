import requests, json, os, sys
from lxml import html
from urllib.parse import urljoin, unquote, urlparse
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config

# Config
BASE_QUIZ_URL = "https://psu.instructure.com/courses/2405803/quizzes/5363417"
OUT = config.QUIZ_RES_DIR

def get_quiz_via_api(s, url):
    """Get quiz questions via Canvas API (more reliable)"""
    p = urlparse(url).path.split('/')
    cid, qid = p[p.index('courses')+1], p[p.index('quizzes')+1]

    # Get quiz questions via API
    api_url = f"https://psu.instructure.com/api/v1/courses/{cid}/quizzes/{qid}/questions"
    print(f"Fetching via API: {api_url}")

    r = s.get(api_url, timeout=20)
    if r.status_code != 200:
        print(f"❌ API failed: {r.status_code}")
        return None

    questions = r.json()
    print(f"✓ Got {len(questions)} questions from API")

    # Download images in parallel
    idir = os.path.join(OUT, 'images')
    os.makedirs(idir, exist_ok=True)
    tasks = []

    def dl(u, p):
        try: open(p, 'wb').write(requests.get(u, timeout=10).content); return p
        except: return None

    # Parse questions and collect image URLs
    qs = []
    for i, q_api in enumerate(questions):
        qid = f"question_{q_api['id']}"
        qt = html.fromstring(q_api.get('question_text', '')).text_content().strip() if q_api.get('question_text') else ''

        # Extract question images from HTML
        qimgs = []
        if q_api.get('question_text'):
            q_doc = html.fromstring(q_api['question_text'])
            for img in q_doc.xpath('.//img'):
                if u := img.get('src'):
                    ip = os.path.join(idir, f"q_{qid}_{len(qimgs)}.png")
                    tasks.append((urljoin(BASE_QUIZ_URL, u), ip))
                    qimgs.append(ip)

        # Parse answers
        ans = []
        for a_api in q_api.get('answers', []):
            aid = str(a_api['id'])
            atxt = html.fromstring(a_api.get('text', '')).text_content().strip() if a_api.get('text') else ''

            # Extract answer images
            aimgs = []
            if a_api.get('text'):
                a_doc = html.fromstring(a_api['text'])
                for img in a_doc.xpath('.//img'):
                    if u := img.get('src'):
                        ip = os.path.join(idir, f"a_{aid}_{len(aimgs)}.png")
                        tasks.append((urljoin(BASE_QUIZ_URL, u), ip))
                        aimgs.append(ip)

            ans.append({'id': aid, 'txt': atxt, 'imgs': aimgs or None})

        qs.append({'id': qid, 'txt': qt, 'imgs': qimgs or None, 'ans': ans})

    # Download all images
    if tasks:
        print(f"⬇️  {len(tasks)} images...")
        with ThreadPoolExecutor(max_workers=20) as ex:
            list(ex.map(lambda x: dl(x[0], x[1]), tasks))

    return qs

def get_answers(qs):
    """Get Gemini answers"""
    genai.configure(api_key=config.GEMINI_API_KEY)
    m = genai.GenerativeModel('gemini-2.5-pro')
    files, imap = [], {}
    print("\n📤 Uploading...")
    for q in qs:
        for ip in (q.get('imgs') or []) + sum([a.get('imgs') or [] for a in q['ans']], []):
            if ip not in imap:
                try: f = genai.upload_file(path=str(ip), display_name=os.path.basename(ip)); imap[ip] = f; files.append(f)
                except: pass
    print(f"✓ Uploaded {len(files)} images\n")
    qd = {}
    for q in qs:
        opts = {}
        for a in q['ans']:
            t = a['txt'] or "[IMAGE]"
            if a.get('imgs'): t += f" [See images: {', '.join([os.path.basename(i) for i in a['imgs']])}]"
            opts[a['id']] = t
        qe = {'question': q['txt'], 'options': opts}
        if q.get('imgs'): qe['question_images'] = [os.path.basename(i) for i in q['imgs']]
        qd[q['id']] = qe
    prompt = f"Analyze the quiz questions and uploaded images carefully. Select the best answer for each question.\nReturn ONLY valid JSON: {{\"question_id\": \"answer_id\", ...}}\n\nQuestions:\n{json.dumps(qd, indent=2)}\n\nExample: {{\"question_97585716\": \"7574\"}}"
    print("Asking Gemini...")
    r = m.generate_content([prompt] + files)
    return json.loads(r.text.strip().replace('```json', '').replace('```', ''))

def save_preview(qs, api_data):
    """Save API response & MD for quick preview"""
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'questions_api.json'), 'w', encoding='utf-8').write(json.dumps(api_data, indent=2))
    with open(os.path.join(OUT, 'questions.md'), 'w', encoding='utf-8') as f:
        for i, q in enumerate(qs):
            f.write(f"### Q{i+1} ({q['id']})\n{q['txt']}\n\n")
            if q.get('imgs'): f.write("**Q-Imgs:** " + ", ".join([f"`{os.path.basename(i)}`" for i in q['imgs']]) + "\n\n")
            f.write("**Answers:**\n")
            for a in q['ans']:
                f.write(f"- `{a['id']}`: {a['txt'] or '[IMG]'}")
                if a.get('imgs'): f.write(f" (Imgs: {', '.join([os.path.basename(i) for i in a['imgs']])})")
                f.write("\n")
            f.write("\n---\n\n")
    print(f"✓ Preview saved: {OUT}/questions.md & questions_api.json")

def save_answers(qs, ans):
    """Save answers"""
    with open(os.path.join(OUT, 'QesWA.md'), 'w', encoding='utf-8') as f:
        f.write("# Quiz Answers\n\n")
        for i, q in enumerate(qs):
            f.write(f"### Q{i+1} ({q['id']})\n{q['txt']}\n\n")
            sel = ans.get(q['id'])
            for a in q['ans']:
                m = "✅ " if a['id'] == sel else ""
                f.write(f"- {m}`{a['id']}`: {a['txt'] or '[IMG]'}\n")
            f.write("\n")

def submit_via_api(s, url, qs, ans):
    """Submit quiz via Canvas API"""
    p = urlparse(url).path.split('/')
    cid, qid = p[p.index('courses')+1], p[p.index('quizzes')+1]

    un = set(q['id'] for q in qs) - set(ans.keys())
    print(f"\n{'='*60}\nTotal: {len(qs)} | Answered: {len(ans)} | Unanswered: {len(un)}")
    if un:
        if input(f"⚠️  {len(un)} unanswered! Type 'yes confirm': ").strip().lower() != 'yes confirm': return print("❌ Cancelled")
    else:
        if input("✓ All done. Submit? (y/yes/ok): ").strip().lower() not in ['y', 'yes', 'ok']: return print("❌ Cancelled")

    # Submit via API
    submit_url = f"https://psu.instructure.com/api/v1/quiz_submissions/{qid}/questions"
    payload = {'quiz_questions': [{'id': q['id'].replace('question_', ''), 'answer': ans.get(q['id'])} for q in qs if ans.get(q['id'])]}

    print("Submitting via API...")
    r = s.post(submit_url, json=payload, timeout=30)
    open(os.path.join(OUT, 'submit_response.json'), 'w', encoding='utf-8').write(r.text)
    print("✅ Done!" if r.status_code == 200 else f"❌ Error: {r.status_code}")

def main():
    config.ensure_dirs()
    c = {x['name']: x['value'] for x in json.load(open(config.COOKIES_FILE))}
    s = requests.Session()
    s.cookies.update(c)
    s.headers.update({'User-Agent': 'Mozilla/5.0'})

    print("Fetching quiz via API...")
    qs = get_quiz_via_api(s, BASE_QUIZ_URL)
    if not qs: return print("❌ Failed")

    print(f"✓ {len(qs)} questions")
    save_preview(qs, qs)  # Save raw API response

    print("Getting answers...")
    ans = get_answers(qs)
    print(f"✓ {len(ans)} answers")

    save_answers(qs, ans)
    submit_via_api(s, BASE_QUIZ_URL, qs, ans)

if __name__ == '__main__':
    main()
