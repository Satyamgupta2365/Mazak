import streamlit as st
import os
import time
import requests
import base64
import tempfile
from groq import Groq
import speech_recognition as sr
from io import BytesIO

# Set page configuration
st.set_page_config(page_title="Multilingual Loan Advisor", layout="wide")

# Initialize session state variables if they don't exist
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "You are a helpful loan advisor and I want you to give short answers."}]
if 'language' not in st.session_state:
    st.session_state.language = "en-IN"
if 'recording' not in st.session_state:
    st.session_state.recording = False

# API Keys - Securely store these in streamlit secrets in production
if 'GROQ_API_KEY' not in st.session_state:
    st.session_state.GROQ_API_KEY = "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"
if 'SARVAM_API_KEY' not in st.session_state:
    st.session_state.SARVAM_API_KEY = "9e95e478-07bd-4d90-ad75-7cbefa3d8172"

# Translation API setup
TRANSLATE_URL = "https://api.sarvam.ai/translate"
TRANSLATE_HEADERS = {
    "api-subscription-key": st.session_state.SARVAM_API_KEY,
    "Content-Type": "application/json"
}

# Function to translate text
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
    
    with st.spinner("Translating..."):
        try:
            response = requests.post(TRANSLATE_URL, json=payload, headers=TRANSLATE_HEADERS)
            if response.status_code == 200:
                return response.json().get("translated_text", "Translation not available")
            else:
                st.error(f"Translation API error: {response.status_code}")
                return "Translation failed."
        except Exception as e:
            st.error(f"Translation error: {e}")
            return "Translation failed."

# Function to create speech from text
def text_to_speech(text, lang):
    """Convert text to speech and return the audio data"""
    try:
        tts = gTTS(text=text, lang=lang.split('-')[0], slow=False)
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp.read()
    except Exception as e:
        st.error(f"Text-to-speech error: {e}")
        return None

# Function to create an audio player for the provided audio data
def get_audio_player(audio_data):
    """Generate HTML for an audio player with the audio data"""
    if audio_data is None:
        return ""
    b64 = base64.b64encode(audio_data).decode()
    audio_html = f"""
        <audio autoplay="true" controls>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            Your browser does not support the audio element.
        </audio>
    """
    return audio_html

# Function to record audio from the microphone
def record_audio():
    """Record audio from the microphone and convert to text"""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Listening... Speak now")
        try:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source, timeout=5)
            st.write("Processing speech...")
            text = recognizer.recognize_google(audio, language=st.session_state.language)
            return text
        except sr.UnknownValueError:
            st.error("Could not understand audio")
            return None
        except sr.RequestError as e:
            st.error(f"Could not request results; {e}")
            return None
        except Exception as e:
            st.error(f"Error in speech recognition: {e}")
            return None

# Function to get completion from LLM
def get_llm_response(messages):
    """Get response from LLM"""
    try:
        client = Groq(api_key=st.session_state.GROQ_API_KEY)
        with st.spinner("Thinking..."):
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=1,
                max_completion_tokens=1024,
                top_p=1
            )
            
            if completion.choices and completion.choices[0].message:
                return completion.choices[0].message.content
            else:
                return "I couldn't generate a response."
    except Exception as e:
        st.error(f"Error getting LLM response: {e}")
        return "Sorry, I encountered an error while processing your question."

# Main UI
st.title("Multilingual Loan Advisor Chatbot")

# Language selection
col1, col2 = st.columns([3, 1])
with col1:
    language_options = {
        "English (India)": "en-IN",
        "Hindi": "hi-IN",
        "Kannada": "kn-IN",
        "Tamil": "ta-IN",
        "Telugu": "te-IN",
        "Bengali": "bn-IN",
        "Marathi": "mr-IN",
        "Gujarati": "gu-IN"
    }
    selected_language = st.selectbox(
        "Select your language:",
        options=list(language_options.keys()),
        index=0
    )
    st.session_state.language = language_options[selected_language]

# Display conversation history
st.subheader("Conversation")
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if message["role"] != "system":
            role = "User" if message["role"] == "user" else "Advisor"
            with st.chat_message(message["role"]):
                st.write(f"{message['content']}")

# Input methods
input_col1, input_col2 = st.columns([3, 1])
with input_col1:
    user_input = st.text_input("Type your message here:", key="text_input")

with input_col2:
    speak_button = st.button("🎤 Speak", key="speak")
    if speak_button:
        with st.spinner("Listening..."):
            spoken_text = record_audio()
            if spoken_text:
                st.session_state.text_input = spoken_text
                user_input = spoken_text

# Process input
if user_input:
    # Add user message to conversation
    with chat_container:
        with st.chat_message("user"):
            st.write(user_input)
    
    # Translate user input to English if not already in English
    if st.session_state.language != "en-IN":
        translated_input = translate_text(user_input, st.session_state.language, "en-IN")
    else:
        translated_input = user_input
    
    # Add to message history
    st.session_state.messages.append({"role": "user", "content": translated_input})
    
    # Get response from LLM
    response = get_llm_response(st.session_state.messages)
    
    # Translate response back to user language if needed
    if st.session_state.language != "en-IN":
        translated_response = translate_text(response, "en-IN", st.session_state.language)
    else:
        translated_response = response
    
    # Display assistant response
    with chat_container:
        with st.chat_message("assistant"):
            st.write(translated_response)
            
            # Convert response to speech and play it
            audio_data = text_to_speech(translated_response, st.session_state.language)
            if audio_data:
                st.markdown(get_audio_player(audio_data), unsafe_allow_html=True)
    
    # Add assistant response to message history
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Clear the input
    st.session_state.text_input = ""

# Instructions
with st.expander("How to use this chatbot"):
    st.markdown("""
    1. **Select your language** from the dropdown menu
    2. **Type your question** in the text box or use the **Speak** button to speak your question
    3. The chatbot will respond in text and with voice
    4. Ask any loan-related questions, and the advisor will provide helpful information
    """)

# Footer
st.markdown("---")
st.caption("Multilingual Loan Advisor powered by Groq LLM and Sarvam AI Translation")
