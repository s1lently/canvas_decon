import requests
import json
from urllib.parse import unquote
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config

def start_quiz():
    # Load cookies from cookies.json
    with open(config.COOKIES_FILE, 'r') as f:
        cookies_data = json.load(f)

    cookies = {cookie['name']: cookie['value'] for cookie in cookies_data}
    
    # Get the authenticity_token from the _csrf_token cookie
    csrf_token = cookies.get('_csrf_token')
    if not csrf_token:
        print("Error: _csrf_token not found in cookies.json")
        return
        
    authenticity_token = unquote(csrf_token)

    # Provided URL from the user
    course_id = "2418560"
    quiz_id = "5399427"
    user_id = "7333037"
    
    url = f"https://psu.instructure.com/courses/{course_id}/quizzes/{quiz_id}/take"
    
    # Payload for the POST request, based on post_exp.txt
    payload = {
        'user_id': user_id,
        '_method': 'post',
        'authenticity_token': authenticity_token
    }
    
    # Headers for the request, inspired by post_exp.txt
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': f'https://psu.instructure.com/courses/{course_id}/quizzes/{quiz_id}',
        'Origin': 'https://psu.instructure.com'
    }

    print(f"Attempting to start quiz at: {url}")
    print(f"Payload: {payload}")

    # Make the POST request
    try:
        response = requests.post(url, headers=headers, data=payload, cookies=cookies, allow_redirects=True)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Save the response content to a file
        with open('quiz_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
            
        print(f"Successfully started the quiz. Response saved to quiz_page.html")
        print(f"Final URL after redirection: {response.url}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            # Save error response for debugging
            with open('quiz_start_error.html', 'w', encoding='utf-8') as f:
                f.write(e.response.text)
            print("Error response saved to quiz_start_error.html")


if __name__ == "__main__":
    start_quiz()
