from flask import Flask, request, jsonify, render_template, session
import json
from openai import OpenAI
from preprocessing import split_sentences_and_filter_sentiment

MAX_SESSION_SIZE = 4000
app = Flask(__name__)
app.secret_key = "TrietChatBot"

# Initialize OpenAI client
client = OpenAI(
    api_key="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",  # Thay thế bằng API Key của bạn
    organization="org-6OKJYIXzvTJPG0ykg9uQkWEX",
    project="proj_Y6a6fJdGqPDSlGgA8znbvL7D"
)

async def fetch_ai_response(payload, max_retries=5):
    """ Gọi API ChatGPT với tối đa 5 lần thử nếu phản hồi không hợp lệ """
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=payload["model"],
                messages=payload["messages"],
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Làm sạch JSON (loại bỏ markdown nếu có)
            clean_json_str = ai_response.strip("```json").strip("```")
            ai_response_json = json.loads(clean_json_str)

            if "aspectTerms" in ai_response_json and isinstance(ai_response_json["aspectTerms"], list) and ai_response_json["aspectTerms"]:
                return ai_response_json
            
            print(f"⚠️ API attempt {attempt+1} failed: No valid aspects. Retrying...")
        
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️ API attempt {attempt+1} failed: Invalid JSON format. Retrying...")
        except Exception as e:
            print(f"⚠️ API attempt {attempt+1} failed: {e}. Retrying...")

    return None  

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
async def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    chat_history = session.get("chat_history", [])
    session_size = len(json.dumps(chat_history).encode('utf-8'))
    
    if session_size > MAX_SESSION_SIZE:
        print(f"⚠️ Session size {session_size} bytes exceeds limit. Clearing session.")
        session.clear()

    if 'chat_history' not in session:
        session['chat_history'] = []
    
    prompt = f"""Extract the key aspects mentioned in the following review and return them in JSON format.
                 Ensure the response follows this format: 
                 "aspectTerms": [
                            {{"term": "term1", 'opinion': 'adj', "polarity": "positive/neutral/negative"}},
                            {{"term": "term2", 'opinion': 'adj', "polarity": "positive/neutral/negative"}}
                ]
                 Review: "{user_message}"."""
    
    session['chat_history'].append({"role": "user", "content": prompt})

    payload = {
        "model": "gpt-4o-mini",
        "messages": session['chat_history']
    }

    ai_response = await fetch_ai_response(payload)

    if ai_response:
        session['chat_history'].append({"role": "assistant", "content": json.dumps(ai_response)})
        session.modified = True
        return jsonify(ai_response)
    
    return jsonify({"error": "AI failed to generate valid aspects after 5 attempts"}), 500

@app.route('/api/reset', methods=['POST'])
def reset_chat():
    session.pop('chat_history', None)
    return jsonify({"message": "Chat history cleared"})

@app.route('/run-preprocessing', methods=['POST'])
def run_preprocessing():
    data = request.json
    review_text = data.get("text", "").strip()

    if not review_text:
        return jsonify({"error": "No text provided"}), 400

    try:
        sentences = split_sentences_and_filter_sentiment(review_text)
        return jsonify({"sentences": sentences})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=9099, debug=True)
