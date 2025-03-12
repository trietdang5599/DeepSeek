
import nltk
import spacy
import re
import contractions
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from flair.data import Sentence
from flair.models import TextClassifier
from transformers import pipeline
from utils.util import read_txt_file_to_list


# Tải các tài nguyên cần thiết từ NLTK một lần duy nhất
# nltk.download('averaged_perceptron_tagger')
# nltk.download('punkt')
# nltk.download('stopwords')
# nltk.download('vader_lexicon')
# nltk.download('punkt_tab')

tagger = TextClassifier.load('en-sentiment')
nlp = spacy.load("en_core_web_sm")
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

# Danh sách các nhãn từ loại cần kiểm tra
word_type = ['JJ', 'JJR', 'JJS', 'RB', 'RBR', 'RBS']
brands = ['dove', 'aveda', 'silver']
keywords = ['overall', 'summary']
output_directory = "dict/"

pos_words = read_txt_file_to_list(output_directory + "positive-words.txt")
neg_words = read_txt_file_to_list(output_directory + "negative-words.txt")
linking_words = read_txt_file_to_list(output_directory + "conjunctions.txt")

def separate_sentences(text):
    text = text if isinstance(text, str) else ''
    text = contractions.fix(text)  # Mở rộng từ viết tắt
    doc = nlp(text)
    sentences = []
    current_sentence = ""

    for token in doc:
        token_text = token.text.strip()  # Loại bỏ khoảng trắng dư thừa

        if token.is_sent_start or token_text == "\n":
            if current_sentence:
                sentences.append(current_sentence.strip())
            # Nếu token không phải là linking word thì mới thêm vào câu, ngược lại bỏ qua
            current_sentence = token_text if token_text.lower() not in linking_words else ""
        elif token_text.lower() in linking_words:
            # Khi gặp linking word: hoàn thiện câu hiện tại và không đưa linking word vào câu mới
            if current_sentence:
                sentences.append(current_sentence.strip())
            current_sentence = ""
        else:
            current_sentence += f" {token_text}"

    if current_sentence:
        sentences.append(current_sentence.strip())

    return sentences

def split_sentences_and_filter_sentiment(text):
    sentences = separate_sentences(text)
    if len(sentences) == 1 and not re.search(r'[.!?]', text):
        sentences = [text]

    filtered_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        words = word_tokenize(sentence)
        words_lower = [word.lower() for word in words]  # Tiền xử lý để không lặp lại chuyển về chữ thường
        
        # Nếu câu có đề cập đến thương hiệu, bỏ qua các phân tích cảm xúc và POS tagging
        if any(word in brands for word in words_lower):
            contains_sentiment = False
            is_a = False
        else:
            # Phân tích cảm xúc theo từng từ
            contains_sentiment = (any(sia.polarity_scores(word)['compound'] != 0 for word in words) or
                                  any(word in pos_words or word in neg_words for word in words_lower))
            
            # Sử dụng Flair để thực hiện POS tagging và kiểm tra các từ có nhãn quan trọng (adjective, adverb)
            sentence_flair = Sentence(sentence)
            tagger.predict(sentence_flair)
            is_a = any(
                label.value in word_type
                for token in sentence_flair.tokens
                for label in token.get_labels('pos')
            )
        
        if contains_sentiment or is_a:
            filtered_sentences.append(sentence)
    
    return filtered_sentences if filtered_sentences else sentences


