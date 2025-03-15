import os
import requests
from flask import Flask, render_template, request, jsonify, session
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret_key")  # For session management

# API Keys from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

# Check if API keys are available
if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY is not set in environment variables")
if not SARVAM_API_KEY:
    print("Warning: SARVAM_API_KEY is not set in environment variables")

# Groq client
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Sarvam API endpoint
TRANSLATE_URL = "https://api.sarvam.ai/translate"
TRANSLATE_HEADERS = {
    "api-subscription-key": SARVAM_API_KEY,
    "Content-Type": "application/json"
} if SARVAM_API_KEY else {}

def translate_text(text, source_lang, target_lang):
    """Translates text using Sarvam AI"""
    if not SARVAM_API_KEY:
        return f"Translation failed: API key not configured. Original text: {text}"
        
    payload = {
        "source_language_code": source_lang,
        "target_language_code": target_lang,
        "speaker_gender": "Male",
        "mode": "classic-colloquial",
        "model": "mayura:v1",
        "enable_preprocessing": False,
        "input": text
    }
    
    try:
        response = requests.post(TRANSLATE_URL, json=payload, headers=TRANSLATE_HEADERS)
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.json().get("translated_text", "Translation not available")
    except requests.exceptions.RequestException as e:
        print(f"Translation error: {str(e)}")
        return f"Translation failed: {str(e)}. Original text: {text}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        user_lang = data.get('language', 'en-IN')
        
        # Initialize or get session messages
        if 'messages' not in session:
            session['messages'] = [{"role": "system", "content": "You are a helpful loan advisor and i want you to give short answers."}]
        
        # Check if API keys are configured
        if not GROQ_API_KEY or not SARVAM_API_KEY:
            return jsonify({
                'original_response': "API keys not configured. Please check server setup.",
                'translated_response': "API keys not configured. Please check server setup."
            }), 500
        
        # Skip translation if language is English
        if user_lang == "en-IN":
            translated_question = user_message
        else:
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
            print(f"Groq API error: {str(e)}")
            answer = f"Error with LLM service: {str(e)}"
        
        # Skip translation if language is English
        if user_lang == "en-IN":
            translated_answer = answer
        else:
            # Translate answer back to user language
            translated_answer = translate_text(answer, "en-IN", user_lang)
        
        # Add to message history
        session['messages'].append({"role": "assistant", "content": answer})
        session.modified = True
        
        return jsonify({
            'original_response': answer,
            'translated_response': translated_answer
        })
    except Exception as e:
        print(f"General error in /chat: {str(e)}")
        return jsonify({
            'original_response': f"Server error: {str(e)}",
            'translated_response': f"Server error: {str(e)}"
        }), 500

@app.route('/reset', methods=['POST'])
def reset_conversation():
    if 'messages' in session:
        session.pop('messages')
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    # Use PORT environment variable for hosting platforms
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=(os.environ.get("FLASK_ENV") == "development"))
