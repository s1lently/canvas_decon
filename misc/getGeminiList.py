import google.generativeai as genai
import json
import re

genai.configure(api_key=json.load(open('account_config.json'))['gemini_api_key'])
models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and re.search(r'gemini-\d+\.\d+-(pro|flash)', m.name)]
print(sorted(models, key=lambda x: (tuple(map(float, re.findall(r'\d+\.\d+', x)[0].split('.'))), 'flash' not in x, 'preview' not in x), reverse=True)[0])