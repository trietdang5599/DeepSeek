from flask import Flask, request, jsonify, render_template
import json
from openai import OpenAI
from preprocessing import split_sentences_and_filter_sentiment
from nltk.corpus import wordnet
import nltk

nltk.download('wordnet')
app = Flask(__name__)
app.secret_key = "TrietChatBot"
category_dict = {}

# Initialize OpenAI client
client = OpenAI(

)



def get_synonyms(word):
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().lower())  # Chuyển tất cả về chữ thường
    return synonyms

def match_aspects_to_categories(aspect_terms):
    matched_categories = set()  # Sử dụng set để tránh trùng lặp

    for item in aspect_terms:
        term = item["term"].lower()
        term_synonyms = get_synonyms(term) | {term}  # Lấy cả từ gốc và từ đồng nghĩa

        for category, aspects in category_dict.items():
            aspect_set = set(map(str.lower, aspects))  # Chuyển aspects về chữ thường
            if term_synonyms & aspect_set:  # Kiểm tra giao nhau giữa tập từ đồng nghĩa và aspects
                matched_categories.add(category)

    return list(matched_categories) if matched_categories else ["unknown"]

# def match_aspects_to_categories(aspect_terms):
#     matched_categories = set()  # Sử dụng set để tránh trùng lặp

#     for item in aspect_terms:
#         for category, aspects in category_dict.items():
#             if item["term"].lower() in aspects:
#                 matched_categories.add(category)

#     return list(matched_categories) if matched_categories else ["unknown"]


async def fetch_ai_response(payload, max_retries=2):
    """Gọi API ChatGPT với tối đa 5 lần thử nếu phản hồi không hợp lệ."""
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

            if ("aspectTerms" in ai_response_json and 
                isinstance(ai_response_json["aspectTerms"], list) and 
                ai_response_json["aspectTerms"]):
                ai_response_json["category"]= match_aspects_to_categories(ai_response_json["aspectTerms"])
                return ai_response_json
            
            print(f"⚠️ API attempt {attempt+1} failed: No valid aspects. Retrying...")
        
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️ API attempt {attempt+1} failed: Invalid JSON format. Retrying...")
        except Exception as e:
            print(f"⚠️ API attempt {attempt+1} failed: {e}. Retrying...")

    # Nếu không có phản hồi hợp lệ sau max_retries, trả về giá trị mặc định
    return {
        "category": ["unknown"],
        "aspectTerms": [
            {
                "opinion": "NULL", 
                "polarity": None,
                "term": "noaspectterm"
            }
        ]
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
async def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    prompt = f"""Extract the key aspects mentioned in the following review and return them in JSON format.
                    Ensure that both 'term' and 'opinion' are explicitly mentioned as keywords in the sentences.
                    The response must strictly follow this format: 
                    "aspectTerms": [
                        {{"term": "term1(noun1)", "opinion": "adj1", "polarity": "positive/neutral/negative"}},
                        {{"term": "term2(noun2)", "opinion": "adj2 ", "polarity": "positive/neutral/negative"}}
                    ]
                    Review: "{user_message}"."""

                    
    # Chỉ gửi prompt của lần tương tác hiện tại
    messages = [{"role": "user", "content": prompt}]

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages
    }

    ai_response = await fetch_ai_response(payload)

    if ai_response:
        return jsonify(ai_response)
    
    return jsonify({"error": "AI failed to generate valid aspects after 5 attempts"}), 500

@app.route('/api/save-categories', methods=['POST'])
def save_categories():
    try:
        # Nhận dữ liệu JSON từ request
        data = request.get_json()

        if not isinstance(data, dict):
            return jsonify({"error": "Invalid format. Expected a dictionary."}), 400

        # Cập nhật category_dict với dữ liệu mới
        category_dict.update(data)

        return jsonify({"message": "Categories saved successfully", "data": category_dict}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
