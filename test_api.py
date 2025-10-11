import google.generativeai as genai

genai.configure(api_key="AIzaSyBZTx5UDH7pxyYZUgpDzKHRU25FWoPIA8I")

model = genai.GenerativeModel("gemini-2.5-pro")

response = model.generate_content("Hello", stream=True)

for chunk in response:
    print(chunk.text, end='', flush=True)
