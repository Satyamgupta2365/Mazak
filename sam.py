import os
import time
import requests
from groq import Groq
from PyPDF2 import PdfReader

# API Keys
GROQ_API_KEY = "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"
SARVAM_API_KEY = "9e95e478-07bd-4d90-ad75-7cbefa3d8172"

if not SARVAM_API_KEY:
    raise ValueError("Sarvam API key is missing!")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# Translation API details
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

def process_chunk(chunk_text, user_lang):
    """Processes a text chunk with Groq AI and translates the response."""
    messages = [
        {"role": "user", "content": "Here is the document and the attached text:\n"},
        {"role": "user", "content": "Display my name, you have all my details, and you are the loan advisor: " + chunk_text}
    ]
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=True,
        stop=None,
    )
    response_text = "".join(chunk.choices[0].delta.content or "" for chunk in completion)
    translated_response = translate_text(response_text, "en-IN", user_lang)
    print(translated_response)

def process_pdf(file_path, user_lang):
    """Reads a PDF file and processes it with Groq"""
    reader = PdfReader(file_path)
    for page_num in range(len(reader.pages)):
        page_text = reader.pages[page_num].extract_text()
        chunk_size = 1000
        text_chunks = [page_text[i:i + chunk_size] for i in range(0, len(page_text), chunk_size)]
        for chunk_text in text_chunks:
            process_chunk(chunk_text, user_lang)

def conversation(user_lang):
    """Loan Advisor Chatbot Interaction"""
    print("Welcome to the Loan Advisor Chatbot. Type 'quit' to exit.")
    messages = [{"role": "system", "content": "You are a helpful loan advisor and should give short answers."}]
    
    print(translate_text("Good day Rahul Sharma. I'm your loan advisor, here to assist you in navigating the loan options and eligibility criteria at the State Bank of India. I have reviewed your information and would like to proceed with a discussion on your loan requirements.\n\nMay I confirm, Rahul, what type of loan are you looking to apply for? You have a savings account with a robust balance, which suggests a good basis for securing a loan with a competitive interest rate. Considering your financial documents, we can work on identifying loan options that suit your income profile and financial goals.", "en-IN", user_lang))
    
    while True:
        question = input("You: ")
        if question.lower() in ["quit", "exit", "stop"]:
            print("Goodbye!")
            break
        
        translated_question = translate_text(question, user_lang, "en-IN")
        messages.append({"role": "user", "content": translated_question})
        
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
        
        translated_answer = translate_text(answer, "en-IN", user_lang)
        print("Loan Advisor:", translated_answer)
        
        messages.append({"role": "assistant", "content": answer})
        time.sleep(0.5)

if __name__ == "__main__":
    user_lang = input("Enter your language code (e.g., en-IN, hi-IN, kn-IN): ")
    file_path = "loan.pdf"  # Update with the correct PDF path
    process_pdf(file_path, user_lang)
    conversation(user_lang)
