"""
统一模型列表获取模块 - 唯一的模型获取入口
"""
import requests
import re
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# 默认fallback模型
FALLBACK_GEMINI = ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash']
FALLBACK_CLAUDE = ['claude-opus-4-5-20251101', 'claude-sonnet-4-5-20250929', 'claude-haiku-4-5-20251001']


def _sort_gemini(name):
    """Gemini排序: pro > flash, 版本高优先, 后缀少优先"""
    ver_match = re.search(r'gemini-(\d+)(?:\.(\d+))?', name)
    major = int(ver_match.group(1)) if ver_match else 0
    minor = int(ver_match.group(2)) if ver_match and ver_match.group(2) else 0

    if '-pro' in name: model_type = 2
    elif '-flash' in name: model_type = 1
    else: model_type = 0

    penalty = 0
    if 'preview' in name: penalty += 1
    if 'exp' in name: penalty += 2
    if 'lite' in name: penalty += 3
    if re.search(r'-\d{2}-\d{2,4}$', name): penalty += 1

    return (major, minor, model_type, -penalty)


def _sort_claude(name):
    """Claude排序: opus > sonnet > haiku, 版本高优先, 日期新优先"""
    if 'opus' in name: model_type = 3
    elif 'sonnet' in name: model_type = 2
    elif 'haiku' in name: model_type = 1
    else: model_type = 0

    name_no_date = re.sub(r'-\d{8}$', '', name)
    ver_match = re.search(r'-(\d+)(?:-(\d+))?$', name_no_date)
    if ver_match:
        major = int(ver_match.group(1))
        minor = int(ver_match.group(2)) if ver_match.group(2) else 0
    else:
        ver_match2 = re.search(r'claude-(\d+)(?:-(\d+))?-', name)
        if ver_match2:
            major = int(ver_match2.group(1))
            minor = int(ver_match2.group(2)) if ver_match2.group(2) else 0
        else:
            major, minor = 0, 0

    date_match = re.search(r'(\d{8})$', name)
    date_val = int(date_match.group(1)) if date_match else 0

    return (model_type, major, minor, date_val)


def get_gemini_models(api_key=None):
    """获取Gemini模型列表 (已排序)"""
    if not api_key:
        api_key = getattr(config, 'GEMINI_API_KEY', None)
    if not api_key:
        return FALLBACK_GEMINI

    try:
        r = requests.get(
            f'https://generativelanguage.googleapis.com/v1beta/models?key={api_key}',
            timeout=10
        )
        if r.status_code != 200:
            return FALLBACK_GEMINI

        models = [
            m['name'].replace('models/', '')
            for m in r.json().get('models', [])
            if 'generateContent' in m.get('supportedGenerationMethods', [])
            and m['name'].startswith('models/gemini-')
            and 'image' not in m['name']
            and 'tts' not in m['name']
            and 'thinking' not in m['name']
            and 'computer-use' not in m['name']
            and 'robotics' not in m['name']
        ]

        return sorted(models, key=_sort_gemini, reverse=True) if models else FALLBACK_GEMINI
    except Exception as e:
        print(f"[utilModels] Gemini error: {e}")
        return FALLBACK_GEMINI


def get_claude_models(api_key=None):
    """获取Claude模型列表 (已排序)"""
    if not api_key:
        api_key = getattr(config, 'CLAUDE_API_KEY', None)
    if not api_key:
        return FALLBACK_CLAUDE

    try:
        r = requests.get(
            'https://api.anthropic.com/v1/models',
            headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01'},
            timeout=10
        )
        if r.status_code != 200:
            return FALLBACK_CLAUDE

        models = [m['id'] for m in r.json().get('data', []) if m['id'].startswith('claude-')]
        return sorted(models, key=_sort_claude, reverse=True) if models else FALLBACK_CLAUDE
    except Exception as e:
        print(f"[utilModels] Claude error: {e}")
        return FALLBACK_CLAUDE


def get_all_models():
    """获取所有模型 (供GUI使用)"""
    return {
        'Gemini': get_gemini_models(),
        'Claude': get_claude_models()
    }


def get_best_gemini_model(api_key=None):
    """获取最佳Gemini模型 (返回display name, 无models/前缀)"""
    models = get_gemini_models(api_key)
    return models[0] if models else "gemini-2.5-pro"


def get_best_claude_model(api_key=None):
    """获取最佳Claude模型"""
    models = get_claude_models(api_key)
    return models[0] if models else "claude-opus-4-5-20251101"


if __name__ == "__main__":
    print("=== Gemini Models ===")
    for i, m in enumerate(get_gemini_models()):
        print(f"{i+1:2}. {m}")

    print("\n=== Claude Models ===")
    for i, m in enumerate(get_claude_models()):
        print(f"{i+1:2}. {m}")

    print(f"\nBest Gemini: {get_best_gemini_model()}")
    print(f"Best Claude: {get_best_claude_model()}")
