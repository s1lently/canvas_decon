import os, json, requests, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

DEFAULT_CONFIG_PATH = os.path.join(config.TODO_DIR, 'default.json')

def load_default_config():
    """Load default product/model from default.json"""
    if os.path.exists(DEFAULT_CONFIG_PATH):
        try: return json.load(open(DEFAULT_CONFIG_PATH))
        except: pass
    return {'product': 'Gemini', 'model': 'gemini-2.5-pro'}

def save_default_config(product, model):
    """Save default product/model to default.json"""
    os.makedirs(config.TODO_DIR, exist_ok=True)
    json.dump({'product': product, 'model': model}, open(DEFAULT_CONFIG_PATH, 'w'), indent=2)

def fetch_claude_models(api_key):
    """Fetch Claude models from Anthropic API"""
    try:
        r = requests.get('https://api.anthropic.com/v1/models',
                        headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01'}, timeout=5)
        if r.status_code == 200:
            return [m['id'] for m in r.json().get('data', [])]
    except: pass
    return ['claude-sonnet-4-5-20250929', 'claude-3-5-sonnet-20241022', 'claude-3-opus-20240229']

def fetch_gemini_models(api_key):
    """Fetch Gemini models from Google API"""
    try:
        r = requests.get(f'https://generativelanguage.googleapis.com/v1beta/models?key={api_key}', timeout=5)
        if r.status_code == 200:
            return [m['name'].replace('models/', '') for m in r.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    except: pass
    return ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-1.5-pro']

def get_all_models():
    """Get models for all products"""
    try:
        from google import genai
        gemini_key = config.GEMINI_API_KEY
    except: gemini_key = None

    claude_key = getattr(config, 'CLAUDE_API_KEY', None)

    models = {
        'Gemini': fetch_gemini_models(gemini_key) if gemini_key else [],
        'Claude': fetch_claude_models(claude_key) if claude_key else []
    }
    return models
