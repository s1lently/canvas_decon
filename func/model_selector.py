"""Smart model selection for Gemini and Claude"""
import google.generativeai as genai
import json
import re
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


def get_best_gemini_model(api_key=None):
    """Get the best available Gemini model for PDF processing

    Returns:
        str: Model name (e.g., 'models/gemini-2.0-flash-exp')
    """
    if not api_key:
        # Try to load from config
        try:
            with open(config.ACCOUNT_CONFIG_FILE) as f:
                api_key = json.load(f).get('gemini_api_key')
        except:
            pass

    if not api_key:
        raise ValueError("Gemini API key not found")

    genai.configure(api_key=api_key)

    # List all models that support generateContent
    models = [
        m.name for m in genai.list_models()
        if 'generateContent' in m.supported_generation_methods
        and re.search(r'gemini-\d+\.\d+-(pro|flash)', m.name)
    ]

    if not models:
        # Fallback to known model
        return 'models/gemini-2.0-flash-exp'

    # Sort by: version (descending), pro > flash, stable > preview
    # Example: gemini-2.0-pro > gemini-2.0-flash > gemini-1.5-pro
    best_model = sorted(
        models,
        key=lambda x: (
            tuple(map(float, re.findall(r'\d+\.\d+', x)[0].split('.'))),  # Version number
            'flash' not in x,  # Pro models before Flash
            'preview' not in x  # Stable before preview
        ),
        reverse=True
    )[0]

    return best_model


def get_best_anthropic_model(api_key=None):
    """Get the best available Claude model for text processing

    Returns:
        str: Model name (e.g., 'claude-sonnet-4-20250514')
    """
    if not api_key:
        # Try to load from config
        try:
            with open(config.ACCOUNT_CONFIG_FILE) as f:
                api_key = json.load(f).get('claude_api_key')
        except:
            pass

    if not api_key:
        raise ValueError("Claude API key not found")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        # List available models
        models = client.models.list()

        # Filter for Claude models and sort by date (newest first)
        claude_models = [
            m.id for m in models.data
            if m.id.startswith('claude-')
        ]

        if not claude_models:
            # Fallback to known best model
            return 'claude-sonnet-4-20250514'

        # Sort by version - prefer sonnet-4 > opus-3 > sonnet-3.5
        best_model = sorted(
            claude_models,
            key=lambda x: (
                'sonnet-4' in x,
                'opus-3' in x,
                'sonnet-3.5' in x
            ),
            reverse=True
        )[0]

        return best_model

    except:
        # Fallback to known best model
        return 'claude-sonnet-4-20250514'


def get_model_display_name(full_name):
    """Convert full model name to display name

    Args:
        full_name: e.g., 'models/gemini-2.0-flash-exp' or 'claude-sonnet-4-20250514'

    Returns:
        str: e.g., 'gemini-2.0-flash-exp' or 'claude-sonnet-4-20250514'
    """
    return full_name.replace('models/', '')


if __name__ == "__main__":
    # Test
    try:
        best = get_best_gemini_model()
        print(f"Best Gemini model: {get_model_display_name(best)}")
    except Exception as e:
        print(f"Error: {e}")
