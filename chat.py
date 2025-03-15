import os
import time
import requests
from flask import Flask, request, jsonify, render_template
from groq import Groq
import base64
import tempfile

app = Flask(__name__)

# API Keys
GROQ_API_KEY = "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"
SARVAM_API_KEY = "9e95e478-07bd-4d90-ad75-7cbefa3d8172"

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# API endpoints
TRANSLATE_URL = "https://api.sarvam.ai/translate"
TEXT_TO_SPEECH_URL = "https://api.sarvam.ai/v1/text-to-speech"

# System message for the loan advisor
SYSTEM_MESSAGE = {"role": "system", "content": "You are a helpful loan advisor and I want you to give short answers."}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    data = request.json
    text_input = data.get('text', '')
    user_lang = data.get('language', 'en-IN')
    
    # Translate to English if needed
    if user_lang != "en-IN":
        translated_text = translate_text(text_input, user_lang, "en-IN")
    else:
        translated_text = text_input
    
    # Get response from Groq
    try:
        messages = [SYSTEM_MESSAGE, {"role": "user", "content": translated_text}]
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=1,
            max_completion_tokens=1024,
            top_p=1
        )
        
        if completion.choices and completion.choices[0].message:
            answer = completion.choices[0].message.content
        else:
            answer = "I didn't understand that question."
    except Exception as e:
        print(f"Error getting response from Groq: {e}")
        answer = "I'm having trouble connecting to the server. Please try again."
    
    # Translate back to user language if needed
    if user_lang != "en-IN":
        translated_answer = translate_text(answer, "en-IN", user_lang)
    else:
        translated_answer = answer
    
    # Generate audio if requested
    audio_base64 = None
    if data.get('generate_audio', False):
        audio_data = text_to_speech(translated_answer, user_lang)
        if audio_data:
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    return jsonify({
        'text_response': translated_answer,
        'audio_response': audio_base64
    })

@app.route('/process_audio', methods=['POST'])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    user_lang = request.form.get('language', 'en-IN')
    
    # Save audio to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.webm')
    audio_file.save(temp_file.name)
    temp_file.close()
    
    # Convert audio to wav using ffmpeg
    # Note: You'll need to install ffmpeg on your server
    # This is a placeholder - you'd need to implement actual conversion
    # wav_file = convert_webm_to_wav(temp_file.name)
    
    # Process for text (you'd need to integrate with a proper speech-to-text API)
    # This is a placeholder response
    text = "This is a placeholder for speech recognition. You'll need to integrate with a proper API."
    
    # Clean up temporary files
    try:
        os.unlink(temp_file.name)
    except:
        pass
    
    return jsonify({'text': text})

def translate_text(text, source_lang, target_lang):
    """Translates text using Sarvam AI"""
    try:
        payload = {
            "source_language_code": source_lang,
            "target_language_code": target_lang,
            "speaker_gender": "Male",
            "mode": "classic-colloquial",
            "model": "mayura:v1",
            "enable_preprocessing": False,
            "input": text
        }
        
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.post(TRANSLATE_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            return response.json().get("translated_text", "Translation not available")
        else:
            print(f"API Error: {response.status_code}, {response.text}")
            return "Translation failed."
    except Exception as e:
        print(f"Error in translation: {e}")
        return "Translation failed."

def text_to_speech(text, language_code):
    """Convert text to speech using Sarvam AI"""
    try:
        payload = {
            "input": text,
            "language": language_code,
            "gender": "female",
            "voice_type": "standard"
        }
        
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            TEXT_TO_SPEECH_URL, 
            json=payload, 
            headers=headers
        )
        
        if response.status_code == 200:
            return response.content
        else:
            print(f"API Error: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"Error in text to speech: {e}")
        return None

if __name__ == '__main__':
    # Make sure templates directory exists
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True)
