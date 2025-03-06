from flask import Flask, request, jsonify, render_template
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# API configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"

# --------------------------- Helper Functions ----------------------------

def is_islamic_question(question):
    """Check if the question is related to Islam based on keywords."""
    keywords = ["islam", "quran", "hadith", "fiqh", "fatwa", "prayer", "fasting", "zakat", "hajj"]
    return any(keyword in question.lower() for keyword in keywords)

def get_gemini_response(prompt):
    """Fetch a response from the Gemini API."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    params = {"key": GOOGLE_API_KEY}

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Safely extract the response text
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Error: No response text received")
    except requests.RequestException as e:
        return f"Error fetching response: {str(e)}"

def format_references(response):
    """Format references in the response for readability."""
    response = response.replace("Quran", "<strong>Quran</strong>")
    response = response.replace("Hadith", "<strong>Hadith</strong>")
    return response

# --------------------------- Routes --------------------------------------

@app.route('/')
def home():
    """Render the home page with the chatbot interface."""
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_fatwa():
    """Handle the user's question and return a response from the Gemini API."""
    data = request.json
    question = data.get('question', '')
    fiqh = data.get('fiqh', '')

    # Validate input
    if not question or not fiqh:
        return jsonify({"response": "Please provide both a question and a Fiqh selection."}), 400

    if not is_islamic_question(question):
        return jsonify({"response": "I can only assist with Islamic questions."}), 400

    # Construct the prompt
    prompt = (
        f"You are an Islamic scholar specializing in {fiqh} Fiqh. Answer this question: '{question}' "
        f"based on the Quran, Hadith, and {fiqh}-specific books. Provide references with narrators, "
        f"authors, and dates where possible."
    )
    response = get_gemini_response(prompt)
    formatted_response = format_references(response)

    return jsonify({"response": formatted_response})

# --------------------------- Application Entry Point ---------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)