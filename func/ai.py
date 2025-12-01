"""AI Utilities - Model listing and API calls for Gemini/Claude"""
import os, sys, re, time, base64
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# Fallback models
FALLBACK_GEMINI = ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash']
FALLBACK_CLAUDE = ['claude-opus-4-5-20251101', 'claude-sonnet-4-5-20250929', 'claude-haiku-4-5-20251001']


# === Model Listing ===

def _sort_gemini(name):
    """Sort: pro > flash, higher version first"""
    ver = re.search(r'gemini-(\d+)(?:\.(\d+))?', name)
    major = int(ver.group(1)) if ver else 0
    minor = int(ver.group(2)) if ver and ver.group(2) else 0
    model_type = 2 if '-pro' in name else (1 if '-flash' in name else 0)
    penalty = sum([1 if x in name else 0 for x in ['preview', 'exp', 'lite']]) + (1 if re.search(r'-\d{2}-\d{2,4}$', name) else 0)
    return (major, minor, model_type, -penalty)


def _sort_claude(name):
    """Sort: opus > sonnet > haiku, newer date first"""
    model_type = {'opus': 3, 'sonnet': 2, 'haiku': 1}.get(next((x for x in ['opus', 'sonnet', 'haiku'] if x in name), ''), 0)
    name_no_date = re.sub(r'-\d{8}$', '', name)
    ver = re.search(r'-(\d+)(?:-(\d+))?$', name_no_date) or re.search(r'claude-(\d+)(?:-(\d+))?-', name)
    major = int(ver.group(1)) if ver else 0
    minor = int(ver.group(2)) if ver and ver.group(2) else 0
    date = int(re.search(r'(\d{8})$', name).group(1)) if re.search(r'(\d{8})$', name) else 0
    return (model_type, major, minor, date)


def get_gemini_models(api_key=None):
    """Get sorted Gemini model list"""
    api_key = api_key or getattr(config, 'GEMINI_API_KEY', None)
    if not api_key:
        return FALLBACK_GEMINI
    try:
        r = requests.get(f'https://generativelanguage.googleapis.com/v1beta/models?key={api_key}', timeout=10)
        if r.status_code != 200:
            return FALLBACK_GEMINI
        models = [m['name'].replace('models/', '') for m in r.json().get('models', [])
                  if 'generateContent' in m.get('supportedGenerationMethods', [])
                  and m['name'].startswith('models/gemini-')
                  and not any(x in m['name'] for x in ['image', 'tts', 'thinking', 'computer-use', 'robotics'])]
        return sorted(models, key=_sort_gemini, reverse=True) if models else FALLBACK_GEMINI
    except Exception as e:
        print(f"[ai] Gemini models error: {e}")
        return FALLBACK_GEMINI


def get_claude_models(api_key=None):
    """Get sorted Claude model list"""
    api_key = api_key or getattr(config, 'CLAUDE_API_KEY', None)
    if not api_key:
        return FALLBACK_CLAUDE
    try:
        r = requests.get('https://api.anthropic.com/v1/models',
                        headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01'}, timeout=10)
        if r.status_code != 200:
            return FALLBACK_CLAUDE
        models = [m['id'] for m in r.json().get('data', []) if m['id'].startswith('claude-')]
        return sorted(models, key=_sort_claude, reverse=True) if models else FALLBACK_CLAUDE
    except Exception as e:
        print(f"[ai] Claude models error: {e}")
        return FALLBACK_CLAUDE


def get_all_models():
    """Get all models (for GUI)"""
    return {'Gemini': get_gemini_models(), 'Claude': get_claude_models()}


def get_best_model(product):
    """Get best model for product"""
    if product == 'Gemini':
        return get_gemini_models()[0] if get_gemini_models() else "gemini-2.5-pro"
    return get_claude_models()[0] if get_claude_models() else "claude-opus-4-5-20251101"


# === File Upload ===

def upload_files(files, product):
    """Pre-upload files for API calls"""
    if product == 'Gemini':
        return _upload_gemini(files)
    elif product == 'Claude':
        return _upload_claude(files)
    raise ValueError(f"Unknown product: {product}")


def _upload_gemini(files):
    """Gemini file upload"""
    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    uploaded = []
    for f in files:
        if os.path.exists(f):
            obj = client.files.upload(file=str(f))
            uploaded.append({'filename': os.path.basename(f), 'uri': obj.name, 'uploaded_obj': obj})
    return uploaded


def _upload_claude(files):
    """Claude file preprocessing (base64)"""
    uploaded = []
    mime_map = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}
    for f in files:
        if not os.path.exists(f):
            continue
        ext = os.path.splitext(f)[1].lower()[1:]
        data = base64.standard_b64encode(open(f, 'rb').read()).decode()
        if ext in mime_map:
            uploaded.append({'filename': os.path.basename(f), 'size': os.path.getsize(f),
                           'mime': mime_map[ext], 'type': 'image', 'data': data})
        elif ext == 'pdf':
            uploaded.append({'filename': os.path.basename(f), 'size': os.path.getsize(f),
                           'mime': 'application/pdf', 'type': 'document', 'data': data})
    return uploaded


# === AI Calls ===

def call_ai(prompt, product, model, files=[], uploaded_info=None, thinking=False, status_callback=None):
    """Unified AI call interface"""
    if product == 'Gemini':
        return _call_gemini(prompt, model, uploaded_info, status_callback)
    elif product == 'Claude':
        return _call_claude(prompt, model, uploaded_info, thinking)
    raise ValueError(f"Unknown product: {product}")


def _call_gemini(prompt, model, uploaded_info=None, status_callback=None):
    """Gemini API call with retry"""
    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    contents = [prompt] + ([i['uploaded_obj'] for i in uploaded_info] if uploaded_info else [])

    for attempt in range(3):
        try:
            return client.models.generate_content(model=model, contents=contents).text
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                if attempt < 2:
                    wait = 60 * (attempt + 1)
                    msg = f"[WARN] Rate limit. Waiting {wait}s..."
                    print(msg)
                    if status_callback:
                        status_callback(msg)
                    time.sleep(wait)
                    continue
            raise
    return ""


def _call_claude(prompt, model, uploaded_info=None, thinking=False):
    """Claude API call"""
    import anthropic
    client = anthropic.Anthropic(api_key=config.CLAUDE_API_KEY, base_url="https://api.anthropic.com")

    content = [{"type": "text", "text": prompt}]
    if uploaded_info:
        for i in uploaded_info:
            if i['type'] == 'image':
                content.append({"type": "image", "source": {"type": "base64", "media_type": i['mime'], "data": i['data']}})
            elif i['type'] == 'document':
                content.append({"type": "document", "source": {"type": "base64", "media_type": i['mime'], "data": i['data']}})

    params = {"model": model, "max_tokens": 16384, "messages": [{"role": "user", "content": content}]}
    if thinking:
        params["thinking"] = {"type": "enabled", "budget_tokens": 8000}

    msg = client.messages.create(**params)
    return next((b.text for b in msg.content if hasattr(b, 'text')), "")


# === Compatibility exports ===
get_best_gemini_model = lambda api_key=None: get_gemini_models(api_key)[0] if get_gemini_models(api_key) else "gemini-2.5-pro"
get_best_claude_model = lambda api_key=None: get_claude_models(api_key)[0] if get_claude_models(api_key) else "claude-opus-4-5-20251101"


if __name__ == "__main__":
    print("=== Gemini Models ===")
    for i, m in enumerate(get_gemini_models()): print(f"{i+1:2}. {m}")
    print("\n=== Claude Models ===")
    for i, m in enumerate(get_claude_models()): print(f"{i+1:2}. {m}")
