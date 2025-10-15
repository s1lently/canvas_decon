from google import genai
import json
import re

api_key = json.load(open('account_config.json'))['gemini_api_key']
client = genai.Client(api_key=api_key)
all_models = list(client.models.list())
models = [m.name for m in all_models if 'generateContent' in m.supported_generation_methods and re.search(r'gemini-\d+\.\d+-(pro|flash)', m.name)]
print(sorted(models, key=lambda x: (tuple(map(float, re.findall(r'\d+\.\d+', x)[0].split('.'))), 'flash' not in x, 'preview' not in x), reverse=True)[0])