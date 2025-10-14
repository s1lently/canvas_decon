import google.generativeai as genai
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config

# 配置API
genai.configure(api_key=config.GEMINI_API_KEY)

# 上传PDF
pdf_file = genai.upload_file(path="bisc_pdfs/Lecture _1 BISC4 (1).pdf", display_name="pdf1")

# 调用模型
model = genai.GenerativeModel('gemini-2.5-pro')
response = model.generate_content(["请问这是什么", pdf_file])

print(response.text)
