import requests
import json
from lxml import html
import os
import google.generativeai as genai
from urllib.parse import urljoin

# --- Configuration ---
# --- 配置 ---
# Use the base URL of the quiz, without '/take'
# 使用测验的基础URL，不要带'/take'
BASE_QUIZ_URL = "https://psu.instructure.com/courses/2418560/quizzes/5399431"
COOKIES_FILE = 'cookies.json'
QUESTIONS_HTML_FILE = 'quiz_res/questions.html'
QUESTIONS_MD_FILE = 'quiz_res/questions.md'
ERROR_PAGE_FILE = 'quiz_submit_error_page.html'
QUIZ_RESPONSE_FILE = 'quiz_response.html'

# IMPORTANT: It is not secure to hardcode your API key. Use environment variables instead.
# 重要提示：硬编码API密钥不安全。请改用环境变量。
# For example: os.environ.get("GEMINI_API_KEY")
GEMINI_API_KEY = "AIzaSyBZTx5UDH7pxyYZUgpDzKHRU25FWoPIA8I"
# --- End of Configuration ---


def start_or_resume_quiz(base_url, session):
    """
    Navigates to the quiz, starting or resuming it if necessary, 
    and returns the response object of the page containing the questions.
    """
    print("--- Step 1: Starting or Resuming Quiz ---")
    print(f"Accessing quiz landing page: {base_url}")
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

    # Scenario 2: Find "Take the Quiz" link/button and start with a POST request
    # 场景2：找到 "Take the Quiz" 链接/按钮 并用POST请求开始
    take_quiz_form = doc.xpath('//form[.//button[contains(., "Take the Quiz")] or .//a[@id="take_quiz_link"]]')
    if take_quiz_form:
        form = take_quiz_form[0]
        action_path = form.get('action')
        post_url = urljoin(base_url, action_path)
        
        # Dynamically build payload from all hidden inputs in the form
        # 从表单中所有隐藏的input动态构建payload
        payload = {
            inp.get('name'): inp.get('value', '')
            for inp in form.xpath('.//input[@type="hidden" and @name]')
        }
        
        print(f"'Take the Quiz' form found. Starting quiz by POSTing to: {post_url}")
        print(f"Payload being sent: {payload}")
        
        try:
            # The POST request should redirect to the page with questions
            # POST请求应该会重定向到包含问题的页面
            response = session.post(post_url, data=payload, timeout=20, allow_redirects=True)
            response.raise_for_status()
            
            # Check if we landed on the questions page
            # 检查我们是否到达了问题页面
            final_doc = html.fromstring(response.content)
            if final_doc.xpath('//*[@id="questions"]'):
                print("Quiz started successfully. Questions are visible.")
                return response
            else:
                print("POST was successful, but the page does not contain questions.")
                print("The quiz may have a pre-start page or another step.")
                with open('quiz_after_start_debug.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print("Saved the resulting page to 'quiz_after_start_debug.html'.")
                return None

        except requests.RequestException as e:
            print(f"POST request to start quiz failed: {e}")
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
    with open('quiz_landing_page_debug.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("Saved the landing page HTML to 'quiz_landing_page_debug.html' for inspection.")
    return None


def parse_questions(doc):
    """Parses the HTML document to extract quiz questions and answers."""
    # This function remains unchanged as its logic is sound.
    # 此函数保持不变，因为其逻辑是健全的。
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
            question_data['content'] = question_text_element[0].text_content().strip()

        answers = []
        answer_elements = question_container.xpath('.//div[contains(@class, "answer")]')
        for answer_el in answer_elements:
            answer_input = answer_el.xpath('.//input[@type="radio"]')
            answer_label = answer_el.xpath('.//label')
            
            if answer_input and answer_label:
                # Find label by 'for' attribute, which is more reliable
                # 通过 'for' 属性寻找label，这更可靠
                input_id = answer_input[0].get('id')
                correct_label = answer_el.xpath(f'.//label[@for="{input_id}"]')
                label_text = correct_label[0].text_content().strip() if correct_label else answer_label[0].text_content().strip()
                answers.append({
                    'id': answer_input[0].get('value'),
                    'content': label_text
                })
        
        question_data['answers'] = answers
        if 'id' in question_data and 'content' in question_data:
            questions_list.append(question_data)

    return questions_list

def get_answers_from_gemini(questions):
    """Formats questions and calls Gemini API to get answers."""
    # This function remains unchanged.
    # 此函数保持不变。
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is not set.")
        return None
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro')

    questions_for_prompt = {}
    for i, q in enumerate(questions):
        questions_for_prompt[q['id']] = {
            "question": q['content'],
            "options": {ans['id']: ans['content'] for ans in q['answers']}
        }

    prompt = f"""
    Based on the following quiz questions and options, please select the best answer for each.
    Return your answers as a single JSON object where the keys are the question IDs (e.g., "question_97585716") and the values are the IDs of the chosen answers.

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
        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '')
        gemini_answers = json.loads(cleaned_response_text)
        print("Successfully received answers from Gemini.")
        return gemini_answers
    except Exception as e:
        print(f"An error occurred with the Gemini API: {e}")
        print("Response text:", getattr(response, 'text', 'N/A'))
        return None

def submit_quiz(session, current_url, doc, answers):
    """Constructs and submits the quiz with the provided answers."""
    # This function is modified to use the session and passed doc.
    # 此函数被修改以使用会话和传入的doc。
    form_element = doc.xpath('//form[@id="submit_quiz_form"]')
    if not form_element:
        print("Could not find submission form.")
        return

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
        print("\nQuiz submitted successfully!")
        with open('quiz_submit_result.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("Submission result saved to 'quiz_submit_result.html'.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during submission: {e}")
        with open(ERROR_PAGE_FILE, 'w', encoding='utf-8') as f:
            f.write(e.response.text if hasattr(e, 'response') and e.response else str(e))
        print(f"The error page has been saved to '{ERROR_PAGE_FILE}'.")


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
        
    print("\n--- Step 2: Parsing Questions ---")
    questions = parse_questions(doc)
    if not questions:
        print("Could not parse any questions from the page.")
        return
    print(f"Successfully parsed {len(questions)} questions.")

    with open(QUESTIONS_MD_FILE, 'w', encoding='utf-8') as f:
        for i, q in enumerate(questions):
            f.write(f"### Question {i+1} (ID: {q.get('id')})\n\n{q.get('content')}\n\n")
            for ans in q.get('answers', []):
                f.write(f"- ID: {ans.get('id')}, Content: {ans.get('content')}\n")
            f.write("\n---\n")
    print(f"Formatted questions saved to '{QUESTIONS_MD_FILE}'.")

    # 2. Get Answers from Gemini
    # 2. 从Gemini获取答案
    print("\n--- Step 3: Getting Answers from Gemini ---")
    gemini_answers = get_answers_from_gemini(questions)
    if not gemini_answers:
        print("Could not get answers from Gemini. Aborting submission.")
        return

    # 3. & 4. Construct and POST the answers
    # 3. & 4. 构造并POST答案
    submit_quiz(session, response.url, doc, gemini_answers)


if __name__ == '__main__':
    if not os.path.exists('quiz_res'):
        os.makedirs('quiz_res')
    main()
