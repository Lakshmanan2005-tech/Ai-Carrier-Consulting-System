import re

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the broken global variable load
text = re.sub(
    r"GEMINI_API_KEY = os\.getenv\('AIzaSy[^']+'\)\nif GEMINI_API_KEY and GEMINI_API_KEY != 'AIzaSy[^']+':\n    try:\n        genai\.configure\(api_key=GEMINI_API_KEY\)",
   genai.configure(api_key=GEMINI_API_KEY)",
    text,
    flags=re.MULTILINE
)

# Strip out lines that throw API key unconfigured explicitly using the user's hardcoded string
text = re.sub(r' +if not GEMINI_API_KEY or GEMINI_API_KEY == "AIzaSy[^"]+":\n +return jsonify\(\{"(error|reply)": "Gemini API key not configured\."\}\)(, 400)?\n', '', text)
text = re.sub(r' +if not questions and GEMINI_API_KEY and GEMINI_API_KEY != "AIzaSy[^"]+":\n', '    if not questions and GEMINI_API_KEY:\n', text)
text = re.sub(r' +if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":\n', '    if GEMINI_API_KEY:\n', text)
text = re.sub(r' +if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":\n +return jsonify\(\{"(error|reply)": "Gemini API key not configured\."\}\)(, 400)?\n', '', text)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Cleared user overrides.")
