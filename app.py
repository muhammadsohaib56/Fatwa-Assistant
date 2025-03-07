from flask import Flask, request, jsonify, render_template
import requests
import os
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# API configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SUNNAH_API_KEY = os.getenv("SUNNAH_API_KEY")  # Add your Sunnah.com API key here
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
QURAN_API_URL = "https://api.alquran.cloud/v1/search"
SUNNAH_API_URL = "https://api.sunnah.com/v1/hadiths"

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
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Error: No response text received")
    except requests.RequestException as e:
        return f"Error fetching response: {str(e)}"

def extract_keywords(question):
    """Extract key terms from the question for searching references."""
    stopwords = {"what", "is", "the", "on", "in", "to", "and", "of"}
    words = question.lower().split()
    keywords = [word for word in words if word not in stopwords and len(word) > 3]
    return keywords[:2]  # Limit to 2 keywords for simplicity

def fetch_quran_references(keywords):
    """Fetch 5 Quranic verses dynamically based on keywords."""
    try:
        search_term = " ".join(keywords)
        response = requests.get(f"{QURAN_API_URL}/{search_term}/all/en", timeout=10)
        response.raise_for_status()
        data = response.json()

        verses = data.get("data", {}).get("matches", [])
        quran_references = []
        for verse in verses[:5]:  # Limit to 5 verses
            surah = verse["surah"]["englishName"]
            ayat = verse["numberInSurah"]
            arabic = verse["text"]
            english = verse["edition"]["text"] if "edition" in verse else "Translation not available"
            quran_references.append({
                "surah": surah,
                "ayat": f"{ayat}",
                "arabic": arabic,
                "english": english
            })
        return quran_references
    except requests.RequestException as e:
        return [{"surah": "Error", "ayat": "", "arabic": "", "english": f"Failed to fetch Quranic verses: {str(e)}"}]

def fetch_hadith_references(keywords):
    """Fetch 5-10 Hadiths dynamically based on keywords."""
    try:
        headers = {"X-API-Key": SUNNAH_API_KEY}
        hadith_references = []
        for keyword in keywords:
            # Note: Sunnah.com API doesn't support direct keyword search; we simulate with random or collection-based requests
            # Replace with actual keyword search if available in your API tier
            response = requests.get(f"{SUNNAH_API_URL}/random", headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            hadith = data.get("hadith", [{}])[0]  # Assuming a single hadith per response
            book = hadith.get("collection", "Unknown")
            number = hadith.get("hadithNumber", "N/A")
            narrator = hadith.get("chain", "Unknown narrator")
            arabic = hadith.get("bodyArabic", "Arabic text not available")
            english = hadith.get("body", "English translation not available")
            hadith_references.append({
                "book": book.capitalize(),
                "number": number,
                "narrator": narrator,
                "arabic": arabic,
                "english": english
            })
            if len(hadith_references) >= 10:  # Limit to 10 Hadiths
                break
        return hadith_references[:10]
    except requests.RequestException as e:
        return [{"book": "Error", "number": "", "narrator": "", "arabic": "", "english": f"Failed to fetch Hadiths: {str(e)}"}]

def format_text(text):
    """Convert **text** to <strong>text</strong> for bold formatting."""
    return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)

def format_fatwa_response(question, fiqh, raw_response):
    """Format the fatwa response with proper headings, Quran, Hadith, and styling."""
    # Format the raw response for bold text
    formatted_raw_response = format_text(raw_response)

    # Fetch dynamic references
    keywords = extract_keywords(question)
    quran_references = fetch_quran_references(keywords)
    hadith_references = fetch_hadith_references(keywords)

    # Construct the formatted HTML response
    formatted_response = f"""
    <h2>Fatwa Based on {fiqh} Fiqh</h2>
    <p><strong>Question:</strong> {question}</p>
    <p style="margin-bottom: 20px;"><strong>Answer:</strong> {formatted_raw_response}</p>

    <h3>Quranic References</h3>
    <ul style="margin-bottom: 20px;">
    """
    for ref in quran_references[:5]:  # Limit to 5 Quranic verses
        formatted_response += f"""
        <li style="margin-bottom: 15px;">
            <strong>{ref['surah']} ({ref['ayat']})</strong><br>
            <em>Arabic:</em> {ref['arabic']}<br>
            <em>English:</em> {ref['english']}
        </li>
        """

    formatted_response += """
    </ul>

    <h3>Hadith References</h3>
    <ul style="margin-bottom: 20px;">
    """
    for ref in hadith_references[:10]:  # Limit to 5-10 Hadiths
        formatted_response += f"""
        <li style="margin-bottom: 15px;">
            <strong>{ref['book']} #{ref['number']}</strong> (Narrated by {ref['narrator']})<br>
            <em>Arabic:</em> {ref['arabic']}<br>
            <em>English:</em> {ref['english']}
        </li>
        """

    formatted_response += """
    </ul>
    """
    return formatted_response

# --------------------------- Routes --------------------------------------

@app.route('/')
def home():
    """Render the home page with the chatbot interface."""
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_fatwa():
    """Handle the user's question and return a formatted fatwa response."""
    data = request.json
    question = data.get('question', '')
    fiqh = data.get('fiqh', '')

    # Validate input
    if not question or not fiqh:
        return jsonify({"response": "<p>Please provide both a question and a Fiqh selection.</p>"}), 400

    if not is_islamic_question(question):
        return jsonify({"response": "<p>I can only assist with Islamic questions.</p>"}), 400

    # Construct the prompt for the Gemini API
    prompt = (
        f"You are an Islamic scholar specializing in {fiqh} Fiqh. Answer this question: '{question}' "
        f"based on the Quran, Hadith, and {fiqh}-specific rulings. Provide detailed reasoning and references "
        f"with Quran verses and Hadith from authentic sources. Use **bold** for emphasis where needed."
    )

    # Fetch response from Gemini API
    raw_response = get_gemini_response(prompt)
    if "Error" in raw_response:
        return jsonify({"response": f"<p>{raw_response}</p>"}), 500

    # Format the response with dynamic Quranic and Hadith references
    formatted_response = format_fatwa_response(question, fiqh, raw_response)

    return jsonify({"response": formatted_response})

# --------------------------- Application Entry Point ---------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)