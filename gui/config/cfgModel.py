"""GUI Model Config"""
import os, json, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config
from func.ai import get_gemini_models, get_claude_models, get_all_models as _get_all_models

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

def get_all_models():
    """Get models for all products (调用统一模块)"""
    return _get_all_models()
