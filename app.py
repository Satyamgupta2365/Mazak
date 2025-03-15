import os
import requests
from flask import Flask, render_template, request, jsonify, session
from groq import Groq

app = Flask(__name__)
app.secret_key = "loan_advisor_secret_key"  # For session management

# API Keys
GROQ_API_KEY = "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"
SARVAM_API_KEY = "9e95e478-07bd-4d90-ad75-7cbefa3d8172"

# Groq client
client = Groq(api_key=GROQ_API_KEY)

# Sarvam API endpoint
TRANSLATE_URL = "https://api.sarvam.ai/translate"
TRANSLATE_HEADERS = {
    "api-subscription-key": SARVAM_API_KEY,
    "Content-Type": "application/json"
}

def translate_text(text, source_lang, target_lang):
    """Translates text using Sarvam AI"""
    payload = {
        "source_language_code": source_lang,
        "target_language_code": target_lang,
        "speaker_gender": "Male",
        "mode": "classic-colloquial",
        "model": "mayura:v1",
        "enable_preprocessing": False,
        "input": text
    }
    response = requests.post(TRANSLATE_URL, json=payload, headers=TRANSLATE_HEADERS)
    if response.status_code == 200:
        return response.json().get("translated_text", "Translation not available")
    return "Translation failed."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    user_lang = data.get('language', 'en-IN')
    
    # Initialize or get session messages
    if 'messages' not in session:
        session['messages'] = [{"role": "system", "content": "You are a helpful loan advisor and i want you to give short answers."}]
    
    # Translate user message to English
    translated_question = translate_text(user_message, user_lang, "en-IN")
    
    # Add to message history
    session['messages'].append({"role": "user", "content": translated_question})
    
    # Get response from Groq
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=session['messages'],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1
        )
        
        if completion.choices and completion.choices[0].message:
            answer = completion.choices[0].message.content
        else:
            answer = "I didn't understand that question."
    except Exception as e:
        answer = f"Error: {str(e)}"
    
    # Translate answer back to user language
    translated_answer = translate_text(answer, "en-IN", user_lang)
    
    # Add to message history
    session['messages'].append({"role": "assistant", "content": answer})
    session.modified = True
    
    return jsonify({
        'original_response': answer,
        'translated_response': translated_answer
    })

@app.route('/reset', methods=['POST'])
def reset_conversation():
    if 'messages' in session:
        session.pop('messages')
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)