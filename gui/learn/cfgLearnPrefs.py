"""Learn Material Preferences Manager - JSON storage for user settings"""
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


# Preferences file location
PREFERENCES_FILE = config.LEARN_PREFERENCES_FILE


# Default preferences (without hardcoded models)
DEFAULT_PREFERENCES = {
    'product': 'Auto',  # Auto, Gemini, Claude
    'model': 'Auto',    # Auto, or specific model name
    'prompts': {
        'text': None,   # None means use default from learn_material.py
        'pdf': None,
        'csv': None
    },
    'available_products': ['Auto', 'Gemini', 'Claude'],
    'available_models': None  # Will be populated dynamically
}


def load_preferences():
    """Load preferences from JSON file

    Returns:
        dict: Preferences dictionary
    """
    if not os.path.exists(PREFERENCES_FILE):
        # Create default preferences
        save_preferences(DEFAULT_PREFERENCES)
        return DEFAULT_PREFERENCES.copy()

    try:
        with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
            prefs = json.load(f)

        # Merge with defaults (in case new fields are added)
        merged = DEFAULT_PREFERENCES.copy()
        merged.update(prefs)

        # Ensure prompts dict exists
        if 'prompts' not in merged:
            merged['prompts'] = DEFAULT_PREFERENCES['prompts'].copy()

        return merged

    except Exception as e:
        print(f"Error loading preferences: {e}")
        return DEFAULT_PREFERENCES.copy()


def save_preferences(prefs):
    """Save preferences to JSON file

    Args:
        prefs: Preferences dictionary
    """
    try:
        with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving preferences: {e}")


def get_product():
    """Get current product preference"""
    return load_preferences().get('product', 'Auto')


def set_product(product):
    """Set product preference"""
    prefs = load_preferences()
    prefs['product'] = product
    save_preferences(prefs)


def get_model():
    """Get current model preference"""
    return load_preferences().get('model', 'Auto')


def set_model(model):
    """Set model preference"""
    prefs = load_preferences()
    prefs['model'] = model
    save_preferences(prefs)


def get_prompt(prompt_type):
    """Get custom prompt for type (text/pdf/csv)

    Args:
        prompt_type: 'text', 'pdf', or 'csv'

    Returns:
        str or None: Custom prompt, or None to use default
    """
    prefs = load_preferences()
    return prefs.get('prompts', {}).get(prompt_type)


def set_prompt(prompt_type, prompt_text):
    """Set custom prompt for type

    Args:
        prompt_type: 'text', 'pdf', or 'csv'
        prompt_text: Custom prompt string, or None to use default
    """
    prefs = load_preferences()
    if 'prompts' not in prefs:
        prefs['prompts'] = {}
    prefs['prompts'][prompt_type] = prompt_text
    save_preferences(prefs)


def get_available_products():
    """Get list of available products"""
    return load_preferences().get('available_products', DEFAULT_PREFERENCES['available_products'])


def refresh_available_models():
    """Refresh model lists from APIs

    Returns:
        dict: Updated available_models dict
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from func.ai import get_gemini_models, get_claude_models

    available_models = {
        'Auto': ['Auto'],
        'Gemini': ['Auto'] + get_gemini_models(),
        'Claude': ['Auto'] + get_claude_models()
    }

    # Save to preferences
    prefs = load_preferences()
    prefs['available_models'] = available_models
    save_preferences(prefs)

    return available_models


def get_available_models(product=None, use_cache=True):
    """Get list of available models for product

    Args:
        product: Product name, or None to use current product
        use_cache: If True, use cached models; if False, refresh from API

    Returns:
        list: Available model names
    """
    if product is None:
        product = get_product()

    prefs = load_preferences()
    available = prefs.get('available_models')

    # If no cached models or refresh requested, fetch from API
    if available is None or not use_cache:
        available = refresh_available_models()

    return available.get(product, ['Auto'])


def add_model_to_product(product, model_name):
    """Add a custom model to product's available list

    Args:
        product: Product name
        model_name: Model name to add
    """
    prefs = load_preferences()
    if 'available_models' not in prefs or prefs['available_models'] is None:
        prefs['available_models'] = refresh_available_models()

    if product not in prefs['available_models']:
        prefs['available_models'][product] = ['Auto']

    if model_name not in prefs['available_models'][product]:
        prefs['available_models'][product].append(model_name)

    save_preferences(prefs)


def reset_to_defaults():
    """Reset all preferences to defaults"""
    save_preferences(DEFAULT_PREFERENCES.copy())


def get_resolved_product_model():
    """Resolve 'Auto' to actual product and model

    Returns:
        tuple: (product, model) - actual values (never 'Auto')
    """
    product = get_product()
    model = get_model()

    # Import here to avoid circular dependency
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from func.ai import get_best_gemini_model, get_best_claude_model

    # Resolve product
    if product == 'Auto':
        # Default to Gemini for PDFs (better vision), Claude for text
        product = 'Gemini'  # We'll decide based on file type later

    # Resolve model
    if model == 'Auto':
        if product == 'Gemini':
            model = get_best_gemini_model().replace('models/', '')
        elif product == 'Claude':
            model = get_best_claude_model()

    return product, model


if __name__ == '__main__':
    # Test
    print("Current preferences:")
    prefs = load_preferences()
    print(json.dumps(prefs, indent=2))

    print("\nResolved product/model:")
    product, model = get_resolved_product_model()
    print(f"Product: {product}, Model: {model}")
