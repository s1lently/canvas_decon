import requests, json, re

def get_html(path):
    with open('cookies.json') as f:
        cookies = {c['name']: c['value'] for c in json.load(f)}
    
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }
    
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update(headers)

    url = f"https://psu.instructure.com{path if path.startswith('/') else '/'+path}"
    
    print(f"Initial request to: {url}")
    r = session.get(url)
    
    if r.history:
        print("Server-side redirect detected:")
        for resp in r.history:
            print(f"  {resp.status_code} {resp.url}")
        print(f"Final URL: {r.url}")

    if "endpoint does not support" in r.text:
        print("Initial response indicates an endpoint issue. Searching for client-side redirect...")
        
        # Search for JavaScript redirect: window.location.href = '...'
        js_redirect_match = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", r.text)
        
        redirect_url = None
        if js_redirect_match:
            redirect_url = js_redirect_match.group(1)
            print(f"Found JavaScript redirect to: {redirect_url}")

        if redirect_url:
            # If the URL is relative, make it absolute
            if redirect_url.startswith('/'):
                redirect_url = f"https://psu.instructure.com{redirect_url}"
            
            print(f"Following client-side redirect to: {redirect_url}")
            r = session.get(redirect_url)
        else:
            print("Could not find a client-side redirect URL in the page.")

    open('test.html', 'w', encoding='utf-8').write(r.text)
    print("\nContent for final URL saved to test.html")

if __name__ == '__main__':
    # This is the URL that was failing due to a client-side redirect.
    get_html("/courses/2419722/assignments")
