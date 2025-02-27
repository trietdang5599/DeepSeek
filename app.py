from flask import Flask, request, jsonify, render_template, session
import asyncio
import json
import httpx 

MAX_SESSION_SIZE = 4000
app = Flask(__name__)
app.secret_key = "TrietChatBot"

async def fetch_ai_response(payload, headers, max_retries=5):
    """ Gọi API AI với tối đa 3 lần thử nếu phản hồi không chứa 'aspects' """
    url = "https://openrouter.ai/api/v1/chat/completions"

    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                try:
                    result = response.json()
                    ai_response = result["choices"][0]["message"]

                    # Làm sạch JSON (loại bỏ markdown nếu có)
                    clean_json_str = ai_response['content'].strip("```json").strip("```").strip()
                    ai_response_json = json.loads(clean_json_str)

                    if "aspects" in ai_response_json and isinstance(ai_response_json["aspects"], list) and ai_response_json["aspects"]:
                        return ai_response_json  

                    print(f"⚠️ API attempt {attempt+1} failed: No valid aspects. Retrying...")

                except (json.JSONDecodeError, KeyError) as e:
                    print(f"⚠️ API attempt {attempt+1} failed: Invalid JSON format. Retrying...")

            else:
                print(f"⚠️ API attempt {attempt+1} failed: {response.status_code}. Retrying...")

        return None  

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
async def chat():
    # Lấy tin nhắn từ request
    data = request.get_json()
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400
    chat_history = session.get("chat_history", [])
    session_size = len(json.dumps(chat_history).encode('utf-8'))  # Chỉ đo kích thước của lịch sử hội thoại
    if session_size > MAX_SESSION_SIZE:
        print(f"⚠️ Session size {session_size} bytes exceeds limit. Clearing session.")
        session.clear()

    if 'chat_history' not in session:
        session['chat_history'] = []

    # Tạo prompt theo định dạng yêu cầu
    prompt = f"""Extract the key aspects mentioned in the following review and return them in JSON format.
                 Ensure the response follows this format: 
                 "aspects": [
                            {{"aspect": "aspect1", "sentiment": "positive/neutral/negative"}},
                            {{"aspect": "aspect2", "sentiment": "positive/neutral/negative"}}
                ]
                 Review: "{user_message}"."""

    session['chat_history'].append({"role": "user", "content": prompt})

    payload = {
        "model": "deepseek/deepseek-chat:free",
        "messages": session['chat_history']
    }

    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json",
        "X-Title": "ChatBot"
    }

    # Gọi API với tối đa 3 lần thử nếu không có 'aspects'
    ai_response = await fetch_ai_response(payload, headers)

    if ai_response:
        # Lưu tin nhắn của AI vào lịch sử hội thoại
        session['chat_history'].append({"role": "assistant", "content": json.dumps(ai_response)})
        session.modified = True  # Cập nhật session
        return jsonify(ai_response)
    
    return jsonify({"error": "AI failed to generate valid aspects after 3 attempts"}), 500

@app.route('/api/reset', methods=['POST'])
def reset_chat():
    session.pop('chat_history', None)
    return jsonify({"message": "Chat history cleared"})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=9099, debug=True)
