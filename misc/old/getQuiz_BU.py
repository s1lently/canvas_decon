import requests
import json
from lxml import html
import os
import sys
import google.generativeai as genai
from urllib.parse import urljoin, unquote, urlparse

# Add parent directory to path for config import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# --- Configuration ---
# --- 配置 ---
# Use the base URL of the quiz, without '/take'
# 使用测验的基础URL，不要带'/take'
BASE_QUIZ_URL = "https://psu.instructure.com/courses/2405803/quizzes/5363417"
COOKIES_FILE = config.COOKIES_FILE
QUESTIONS_HTML_FILE = os.path.join(config.QUIZ_RES_DIR, 'questions.html')
QUESTIONS_MD_FILE = os.path.join(config.QUIZ_RES_DIR, 'questions.md')
QUESTIONS_WITH_ANSWERS_FILE = os.path.join(config.QUIZ_RES_DIR, 'QesWA.md')
ERROR_PAGE_FILE = os.path.join(config.QUIZ_RES_DIR, 'quiz_submit_error_page.html')
QUIZ_RESPONSE_FILE = os.path.join(config.QUIZ_RES_DIR, 'quiz_response.html')
QUIZ_DEBUG_FILE = os.path.join(config.QUIZ_RES_DIR, 'quiz_debug.html')
QUIZ_LANDING_DEBUG_FILE = os.path.join(config.QUIZ_RES_DIR, 'quiz_landing_debug.html')
GEMINI_API_KEY = config.GEMINI_API_KEY
# --- End of Configuration ---


def start_or_resume_quiz(base_url, session):
    """
    Navigates to the quiz, starting or resuming it if necessary,
    and returns the response object of the page containing the questions.
    """
    print("--- Step 1: Starting or Resuming Quiz ---")
    print(f"Accessing quiz landing page: {base_url}")

    # Parse quiz IDs from URL
    parsed = urlparse(base_url)
    path_parts = parsed.path.split('/')
    try:
        course_id = path_parts[path_parts.index('courses') + 1]
        quiz_id = path_parts[path_parts.index('quizzes') + 1]
    except (ValueError, IndexError):
        print("Error: Could not parse course_id and quiz_id from URL")
        return None

    try:
        response = session.get(base_url, timeout=20)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to load quiz page: {e}")
        return None

    doc = html.fromstring(response.content)

    # Scenario 1: Quiz already in progress (we are on the '/take' page)
    # 场景1：测验已在进行中 (我们就在'/take'页面上)
    if doc.xpath('//*[@id="questions"]'):
        print("Quiz is already in progress. Proceeding directly to questions.")
        return response

    # Scenario 2: Use POST method with CSRF token (like stQz.py)
    # 场景2：使用 POST 方法和 CSRF token 启动测验 (参考 stQz.py)
    print("Attempting to start quiz using POST method with CSRF token...")

    # Get CSRF token from cookies
    csrf_token = None
    for cookie in session.cookies:
        if cookie.name == '_csrf_token':
            csrf_token = unquote(cookie.value)
            break

    if not csrf_token:
        print("Warning: _csrf_token not found in cookies")

    # Extract user_id from page content
    user_id = None
    user_id_match = doc.xpath('//meta[@name="current-user-id"]/@content')
    if user_id_match:
        user_id = user_id_match[0]
    else:
        # Try to find from Take Quiz link
        take_link = doc.xpath('//a[@id="take_quiz_link"]/@href')
        if take_link:
            import re
            match = re.search(r'user_id=(\d+)', take_link[0])
            if match:
                user_id = match.group(1)

    if not user_id:
        print("Warning: Could not find user_id")
        user_id = "7333037"  # fallback to known user_id

    # Construct POST URL and payload
    post_url = f"https://psu.instructure.com/courses/{course_id}/quizzes/{quiz_id}/take"

    payload = {
        'user_id': user_id,
        '_method': 'post',
        'authenticity_token': csrf_token if csrf_token else ''
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': base_url,
        'Origin': 'https://psu.instructure.com'
    }

    print(f"POST URL: {post_url}")
    print(f"Payload: {payload}")

    try:
        response = session.post(post_url, data=payload, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()

        # Check if questions are now visible
        final_doc = html.fromstring(response.content)
        if final_doc.xpath('//*[@id="questions"]'):
            print("✓ Quiz started successfully using POST method!")
            return response
        else:
            print("POST succeeded but questions not found. Saving debug file...")
            with open(QUIZ_DEBUG_FILE, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"Saved to '{QUIZ_DEBUG_FILE}'")
            return None

    except requests.RequestException as e:
        print(f"POST request failed: {e}")
        return None

    # Scenario 3: Find "Resume Quiz" link/button
    # 场景3：找到 "Resume Quiz" 链接/按钮
    resume_quiz_link = doc.xpath('//a[contains(@class, "btn") and contains(., "Resume Quiz")]')
    if resume_quiz_link:
        href = resume_quiz_link[0].get('href')
        if not href:
            print("Found 'Resume Quiz' button but it has no href. Cannot proceed.")
            return None

        resume_url = urljoin(base_url, href)
        print(f"'Resume Quiz' link found. Navigating to: {resume_url}")
        try:
            # The resume action might be a simple GET that leads to the quiz
            # 继续测验的动作可能就是一个简单的GET请求
            return session.get(resume_url, timeout=20)
        except requests.RequestException as e:
            print(f"Failed to follow 'Resume Quiz' link: {e}")
            return None

    print("Could not find a 'Take Quiz' or 'Resume Quiz' button, nor any questions.")
    print("The quiz may be over, or the page structure is unexpected.")
    with open(QUIZ_LANDING_DEBUG_FILE, 'w', encoding='utf-8') as f:
        f.write(response.text)
    print(f"Saved the landing page HTML to '{QUIZ_LANDING_DEBUG_FILE}' for inspection.")
    return None


def parse_questions(doc):
    """Parses the HTML document to extract quiz questions and answers."""
    import os
    import requests
    from urllib.parse import urljoin
    from concurrent.futures import ThreadPoolExecutor
    
    img_dir = os.path.join(config.QUIZ_RES_DIR, 'images')
    os.makedirs(img_dir, exist_ok=True)
    
    # Collect all image download tasks
    download_tasks = []
    
    def download_image(url, path):
        try:
            requests.get(url, timeout=10).content and open(path, 'wb').write(requests.get(url).content)
            return path
        except:
            return None
    
    questions_list = []
    question_elements = doc.xpath('//*[@id="questions"]/div[contains(@class, "question")]')

    for question_div in question_elements:
        question_data = {}
        
        nav_anchor = question_div.xpath('./a')
        if nav_anchor:
            question_data['nav_id'] = nav_anchor[0].get('id')

        question_container = question_div.xpath('.//div[starts-with(@id, "question_")]')
        if not question_container:
            continue
        
        question_container = question_container[0]
        question_id_full = question_container.get('id')
        
        question_text_element = question_container.xpath('.//div[contains(@class, "question_text")]')
        if question_text_element:
            question_data['id'] = question_id_full
            img_elements = question_text_element[0].xpath('.//img')
            if img_elements:
                img_paths = []
                for img in img_elements:
                    if img_url := img.get('src'):
                        img_url = urljoin(BASE_QUIZ_URL, img_url)
                        img_path = os.path.join(img_dir, f"q_{question_id_full}_{len(img_paths)}.png")
                        download_tasks.append((img_url, img_path))
                        img_paths.append(img_path)
                question_data['images'] = img_paths
            question_data['content'] = question_text_element[0].text_content().strip()

        answers = []
        # Use exact class match to avoid matching "answer_label", "answer_input" etc.
        answer_elements = question_container.xpath('.//div[@class="answer" or contains(@class, "answer ") or contains(@class, " answer")]')
        for answer_el in answer_elements:
            answer_input = answer_el.xpath('.//input[@type="radio"]')
            answer_label = answer_el.xpath('.//label')
            
            if answer_input and answer_label:
                input_id = answer_input[0].get('id')
                correct_label = answer_el.xpath(f'.//label[@for="{input_id}"]')
                label_text = correct_label[0].text_content().strip() if correct_label else answer_label[0].text_content().strip()
                
                answer_data = {'id': answer_input[0].get('value'), 'content': label_text}
                
                img_elements = answer_el.xpath('.//img')
                if img_elements:
                    img_paths = []
                    for img in img_elements:
                        if img_url := img.get('src'):
                            img_url = urljoin(BASE_QUIZ_URL, img_url)
                            img_path = os.path.join(img_dir, f"a_{answer_data['id']}_{len(img_paths)}.png")
                            download_tasks.append((img_url, img_path))
                            img_paths.append(img_path)
                    answer_data['images'] = img_paths
                
                answers.append(answer_data)
        
        question_data['answers'] = answers
        if 'id' in question_data and 'content' in question_data:
            questions_list.append(question_data)
    
    # Download all images in parallel
    if download_tasks:
        print(f"⬇️  Downloading {len(download_tasks)} images with 20 threads...")
        with ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(lambda x: download_image(x[0], x[1]), download_tasks))
        print(f"✓ Downloaded {len(download_tasks)} images")

    return questions_list

def get_answers_from_gemini(questions):
    """Formats questions and calls Gemini API to get answers."""
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is not set.")
        return None
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    # Collect all images and upload them
    all_uploaded_files = []
    image_map = {}  # Map local path to uploaded file reference
    
    print("\n📤 Uploading images to Gemini...")
    for q in questions:
        # Upload question images
        if 'images' in q and q['images']:
            for img_path in q['images']:
                if img_path not in image_map:
                    try:
                        print(f"  Uploading: {os.path.basename(img_path)}")
                        uploaded = genai.upload_file(path=str(img_path), display_name=os.path.basename(img_path))
                        image_map[img_path] = uploaded
                        all_uploaded_files.append(uploaded)
                    except Exception as e:
                        print(f"  Failed: {e}")
        
        # Upload answer images
        for ans in q['answers']:
            if 'images' in ans and ans['images']:
                for img_path in ans['images']:
                    if img_path not in image_map:
                        try:
                            print(f"  Uploading: {os.path.basename(img_path)}")
                            uploaded = genai.upload_file(path=str(img_path), display_name=os.path.basename(img_path))
                            image_map[img_path] = uploaded
                            all_uploaded_files.append(uploaded)
                        except Exception as e:
                            print(f"  Failed: {e}")
    
    print(f"✓ Uploaded {len(all_uploaded_files)} images\n")
    
    # Build questions for prompt with image references
    questions_for_prompt = {}
    for i, q in enumerate(questions):
        q_data = {
            "question": q['content'],
            "options": {}
        }
        
        # Add question image references
        if 'images' in q and q['images']:
            q_data['question_images'] = [os.path.basename(img) for img in q['images'] if img in image_map]
        
        # Add answer options and their image references
        for ans in q['answers']:
            ans_text = ans['content'] if ans['content'] else "[IMAGE]"
            if 'images' in ans and ans['images']:
                img_refs = [os.path.basename(img) for img in ans['images'] if img in image_map]
                ans_text += f" [Images: {', '.join(img_refs)}]"
            q_data['options'][ans['id']] = ans_text
        
        questions_for_prompt[q['id']] = q_data

    prompt = f"""
Based on the following quiz questions and options, please select the best answer for each.
I have uploaded images that are referenced in the questions and options. Please analyze both the text and images carefully.

Return your answers as a single JSON object where the keys are the question IDs and the values are the IDs of the chosen answers.

Questions:
{json.dumps(questions_for_prompt, indent=2)}

Example response format:
{{
  "question_97585716": "7574",
  "question_97585717": "5127"
}}
"""

    print("Sending request to Gemini API...")
    try:
        # Send prompt with all uploaded images
        response = model.generate_content([prompt] + all_uploaded_files)
        cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '')
        gemini_answers = json.loads(cleaned_response_text)
        print("Successfully received answers from Gemini.")
        return gemini_answers
    except Exception as e:
        print(f"An error occurred with the Gemini API: {e}")
        print("Response text:", getattr(response, 'text', 'N/A'))
        return None

def validate_answers(questions, answers):
    """
    Validate answers and check for unanswered questions.
    Returns (is_valid, empty_questions, total_questions)
    """
    question_ids = {q['id'] for q in questions}
    answered_ids = set(answers.keys())
    empty_questions = question_ids - answered_ids

    return len(empty_questions) == 0, empty_questions, len(questions)


def manual_answer_input(questions, answers):
    """
    Allow user to manually input answers for unanswered questions.
    Returns updated answers dict.
    """
    is_complete, empty_questions, _ = validate_answers(questions, answers)

    if not empty_questions:
        return answers

    print("\n" + "="*60)
    print("手动输入答案 / Manual Answer Input")
    print("="*60)
    print("提示: 这些题目可能包含图片,Gemini无法识别")
    print("Hint: These questions may contain images that Gemini cannot process")
    print("\n你可以:")
    print("1. 输入答案ID (answer ID)")
    print("2. 输入 'skip' 跳过该题")
    print("3. 输入 'quit' 结束手动输入\n")

    updated_answers = answers.copy()

    for q in questions:
        if q['id'] not in empty_questions:
            continue

        print("\n" + "-"*60)
        print(f"题目 ID: {q['id']}")
        print(f"问题: {q['content'][:200]}")
        print("\n可选答案:")

        # Show all answer options
        if not q.get('answers'):
            print("  (无可用选项 / No options available)")
            continue

        for i, ans in enumerate(q['answers'], 1):
            content = ans.get('content', '')
            if not content or content == '[IMAGE]':
                print(f"  {i}. ID: {ans['id']} - [图片选项 / Image option]")
            else:
                print(f"  {i}. ID: {ans['id']} - {content[:80]}")

        # Get user input
        while True:
            user_input = input("\n请输入答案ID或选项编号 (或 skip/quit): ").strip()

            if user_input.lower() == 'quit':
                print("结束手动输入 / Ending manual input")
                return updated_answers
            elif user_input.lower() == 'skip':
                print(f"跳过题目 {q['id']}")
                break
            elif user_input.isdigit():
                # User entered option number
                opt_num = int(user_input)
                if 1 <= opt_num <= len(q['answers']):
                    answer_id = q['answers'][opt_num - 1]['id']
                    updated_answers[q['id']] = answer_id
                    print(f"✓ 已设置答案: {answer_id}")
                    break
                else:
                    print(f"❌ 无效选项编号,请输入 1-{len(q['answers'])}")
            else:
                # User entered answer ID directly
                # Verify it's valid
                valid_ids = [ans['id'] for ans in q['answers']]
                if user_input in valid_ids:
                    updated_answers[q['id']] = user_input
                    print(f"✓ 已设置答案: {user_input}")
                    break
                else:
                    print(f"❌ 无效的答案ID,有效的ID: {valid_ids}")

    return updated_answers


def confirm_submission(questions, answers):
    """
    Show answer summary and ask for user confirmation before submission.
    Returns True if user confirms, False otherwise.
    """
    print("\n" + "="*60)
    print("答案检查 / Answer Review")
    print("="*60)

    # Validate answers
    is_complete, empty_questions, total = validate_answers(questions, answers)

    print(f"\n总题数 / Total Questions: {total}")
    print(f"已回答 / Answered: {len(answers)}")
    print(f"未回答 / Unanswered: {len(empty_questions)}")

    if empty_questions:
        print("\n⚠️  警告: 以下题目未回答 / WARNING: Unanswered questions:")
        for q in questions:
            if q['id'] in empty_questions:
                print(f"  - {q['id']}: {q['content'][:60]}...")

    # Show answer summary (first 5 questions)
    print("\n答案预览 / Answer Preview (first 5):")
    for i, q in enumerate(questions[:5]):
        answer_id = answers.get(q['id'], 'EMPTY')
        if answer_id != 'EMPTY':
            # Find the answer content
            answer_content = next((a['content'] for a in q.get('answers', []) if a['id'] == answer_id), 'Unknown')
            print(f"  Q{i+1}: {answer_content[:50]}")
        else:
            print(f"  Q{i+1}: [未回答 / EMPTY]")

    if len(questions) > 5:
        print(f"  ... (and {len(questions) - 5} more)")

    # Ask for confirmation
    print("\n" + "="*60)

    if empty_questions:
        print("⚠️  存在未回答的问题！/ There are unanswered questions!")
        print("确定要提交吗? 需要二次确认 / Are you sure? Need double confirmation!")
        print("请输入 'yes confirm' 来继续提交 / Type 'yes confirm' to proceed:")
        user_input = input("> ").strip().lower()
        return user_input == 'yes confirm'
    else:
        print("✓ 所有题目已回答 / All questions answered")
        print("是否提交? / Submit now?")
        print("输入以下任意词语继续 / Enter any of these to proceed:")
        print("  y, yes, 对, 是, ok, 继续, 别停")
        user_input = input("> ").strip().lower()

        # Check for confirmation keywords
        confirm_keywords = ['y', 'yes', '对', '是', 'ok', '继续', '别停']
        return user_input in confirm_keywords


def submit_quiz(session, current_url, doc, questions, answers):
    """Constructs and submits the quiz with the provided answers."""
    # This function is modified to use the session and passed doc.
    # 此函数被修改以使用会话和传入的doc。

    # First, ask for user confirmation
    if not confirm_submission(questions, answers):
        print("\n❌ 提交已取消 / Submission cancelled by user")
        return False

    form_element = doc.xpath('//form[@id="submit_quiz_form"]')
    if not form_element:
        print("Could not find submission form.")
        return False

    form_element = form_element[0]
    action = form_element.get('action')
    submission_url = urljoin(current_url, action)

    payload = {}
    for input_el in form_element.xpath('.//input'):
        name = input_el.get('name')
        if name:
            payload[name] = input_el.get('value', '')

    for question_id, answer_id in answers.items():
        payload[question_id] = answer_id

    print("\n--- Submitting Quiz ---")
    print(f"URL: {submission_url}")
    print("Payload being sent (first 3 items):", {k: v for i, (k, v) in enumerate(payload.items()) if i < 3})

    try:
        response = session.post(submission_url, data=payload, timeout=30)
        response.raise_for_status()
        print("\n✅ Quiz submitted successfully!")
        with open(QUIZ_RESPONSE_FILE, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Submission result saved to '{QUIZ_RESPONSE_FILE}'.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred during submission: {e}")
        with open(ERROR_PAGE_FILE, 'w', encoding='utf-8') as f:
            f.write(e.response.text if hasattr(e, 'response') and e.response else str(e))
        print(f"The error page has been saved to '{ERROR_PAGE_FILE}'.")
        return False


def main():
    """Main function to orchestrate the quiz bot."""
    # Setup session with cookies
    # 设置带cookie的会话
    try:
        with open(COOKIES_FILE, 'r') as f:
            cookies_dict = {c['name']: c['value'] for c in json.load(f)}
    except FileNotFoundError:
        print(f"Error: {COOKIES_FILE} not found.")
        return

    session = requests.Session()
    session.cookies.update(cookies_dict)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    # 1. Start or Resume Quiz to get the question page
    # 1. 开始或继续测验以获取题目页面
    response = start_or_resume_quiz(BASE_QUIZ_URL, session)
    if not response:
        return

    doc = html.fromstring(response.content)
    
    if not doc.xpath('//*[@id="questions"]'):
        print("Failed to get to the questions page.")
        return
    
    # Save original HTML
    with open(QUESTIONS_HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(response.text)
    print(f"✓ Original HTML saved to '{QUESTIONS_HTML_FILE}'")
        
    print("\n--- Step 2: Parsing Questions ---")
    questions = parse_questions(doc)
    if not questions:
        print("Could not parse any questions from the page.")
        return
    print(f"Successfully parsed {len(questions)} questions.")

    with open(QUESTIONS_MD_FILE, 'w', encoding='utf-8') as f:
        for i, q in enumerate(questions):
            f.write(f"### Question {i+1} (ID: {q.get('id')})\n\n{q.get('content')}\n\n")
            
            # Add question images if any (using filename references for Gemini)
            if 'images' in q and q['images']:
                f.write("**Question Images (uploaded to Gemini):**\n")
                for img_path in q['images']:
                    f.write(f"- `{os.path.basename(img_path)}`\n")
                f.write("\n")
            
            f.write("**Answers:**\n")
            for ans in q.get('answers', []):
                ans_content = ans.get('content') if ans.get('content') else "[IMAGE]"
                f.write(f"- ID: `{ans.get('id')}`, Content: {ans_content}\n")
                
                # Add answer images if any (using filename references for Gemini)
                if 'images' in ans and ans['images']:
                    f.write("  - Uploaded images: ")
                    img_refs = [f"`{os.path.basename(img)}`" for img in ans['images']]
                    f.write(", ".join(img_refs) + "\n")
            f.write("\n---\n")
    print(f"Formatted questions saved to '{QUESTIONS_MD_FILE}'.")

    # 2. Get Answers from Gemini
    # 2. 从Gemini获取答案
    print("\n--- Step 3: Getting Answers from Gemini ---")
    gemini_answers = get_answers_from_gemini(questions)
    if not gemini_answers:
        print("Could not get answers from Gemini. Aborting submission.")
        return
    
    # Save questions with answers
    with open(QUESTIONS_WITH_ANSWERS_FILE, 'w', encoding='utf-8') as f:
        f.write("# Quiz Questions with Answers\n\n")
        for i, q in enumerate(questions):
            f.write(f"### Question {i+1} (ID: {q.get('id')})\n\n{q.get('content')}\n\n")
            
            if 'images' in q and q['images']:
                f.write("**Question Images:**\n")
                for img_path in q['images']:
                    f.write(f"- `{os.path.basename(img_path)}`\n")
                f.write("\n")
            
            selected_answer_id = gemini_answers.get(q['id'])
            f.write("**Answers:**\n")
            for ans in q.get('answers', []):
                is_selected = ans.get('id') == selected_answer_id
                marker = "✅ **[SELECTED]**" if is_selected else ""
                ans_content = ans.get('content') if ans.get('content') else "[IMAGE]"
                f.write(f"- {marker} ID: `{ans.get('id')}`, Content: {ans_content}\n")
                if 'images' in ans and ans['images']:
                    img_refs = [f"`{os.path.basename(img)}`" for img in ans['images']]
                    f.write(f"  - Images: {', '.join(img_refs)}\n")
            f.write("\n---\n\n")
    print(f"✓ Questions with answers saved to '{QUESTIONS_WITH_ANSWERS_FILE}'")

    # 3. Check for unanswered questions and allow manual input
    # 3. 检查未回答的题目并允许手动输入
    _, empty_questions, _ = validate_answers(questions, gemini_answers)

    if empty_questions:
        print(f"\n⚠️  发现 {len(empty_questions)} 个未回答的题目")
        print(f"Found {len(empty_questions)} unanswered questions")
        print("\n可能原因:")
        print("- 题目或选项包含图片 (Images in question/answers)")
        print("- Gemini API 未能生成答案 (API failed to generate answer)")

        print("\n是否手动输入这些题目的答案? / Manually input answers?")
        print("输入 'y' 或 'yes' 进入手动输入模式")
        user_choice = input("> ").strip().lower()

        if user_choice in ['y', 'yes', '是', '对']:
            gemini_answers = manual_answer_input(questions, gemini_answers)
            print("\n✓ 手动输入完成 / Manual input completed")

    # 4. Submit quiz with confirmation
    # 4. 提交测验(带确认)
    submit_quiz(session, response.url, doc, questions, gemini_answers)


if __name__ == '__main__':
    config.ensure_dirs()
    main()
