from flask import Flask, render_template, request
import docx2txt
import re
import spacy
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
from collections import Counter
import os
import fitz  # PyMuPDF

app = Flask(__name__)

# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# Load skills list
skills_df = pd.read_csv('skills.csv')
skills_list = skills_df.iloc[:, 0].str.lower().tolist()
TECH_KEYWORDS = skills_list

CUSTOM_STOPWORDS = set(stopwords.words('english')).union({
    'utilize', 'new', 'growing', 'best', 'your', 'you', 'they', 'our', 'the', 'a', 'an',
    'and', 'too', 'required', 'preferred', 'others', 'bachelor', 'master',
    'degree', 'education', 'skills', 'experience', 'responsibilities'
})

def clean_text(text):
    text = re.sub(r'[.,;:()\[\]{}]', '', text)
    return text.lower()

def extract_technical_keywords(text):
    cleaned = clean_text(text)
    words = set(cleaned.split()) - CUSTOM_STOPWORDS

    dict_matches = [word for word in words if word in TECH_KEYWORDS]

    doc = nlp(text)
    raw_terms = [chunk.text.lower() for chunk in doc.noun_chunks] + \
                [ent.text.lower() for ent in doc.ents]

    filtered_terms = set()
    trailing_stopwords = {'and', 'or', 'with', 'of', 'for', 'to', 'in'}

    for phrase in raw_terms:
        phrase = clean_text(phrase.strip())
        tokens = phrase.split()
        while tokens and tokens[-1] in trailing_stopwords:
            tokens.pop()
        phrase = ' '.join(tokens)
        if len(phrase.split()) > 3:
            continue
        if phrase in CUSTOM_STOPWORDS:
            continue
        for tech_term in TECH_KEYWORDS:
            if tech_term in phrase:
                filtered_terms.add(tech_term)

    combined_keywords = set(dict_matches) | filtered_terms
    return sorted(combined_keywords)

def extract_text_from_pdf(file):
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def highlight_jd_text(text, matched, unmatched):
    # Sort longer phrases first
    matched = sorted(matched, key=lambda x: -len(x))
    unmatched = sorted(unmatched, key=lambda x: -len(x))

    for phrase in matched:
        phrase_re = re.compile(r'\b' + re.escape(phrase) + r'\b', flags=re.IGNORECASE)
        text = phrase_re.sub(lambda m: f'<span class="match">{m.group(0)}</span>', text)

    for phrase in unmatched:
        phrase_re = re.compile(r'\b' + re.escape(phrase) + r'\b', flags=re.IGNORECASE)
        text = phrase_re.sub(lambda m: f'<span class="unmatch">{m.group(0)}</span>', text)

    return text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/match', methods=['POST'])
def match_resume():
    resume_file = request.files['resume']
    jd_text = request.form['jd']
    
    filename = resume_file.filename
    extension = os.path.splitext(filename)[1].lower()
    
    if extension == '.docx':
        resume_text = docx2txt.process(resume_file)
    elif extension == '.pdf':
        resume_text = extract_text_from_pdf(resume_file)
    else:
        return "Unsupported file type. Please upload a .docx or .pdf", 400

    jd_keywords = extract_technical_keywords(jd_text)
    jd_keywords_str = ' '.join(jd_keywords)

    resume_text_clean = clean_text(resume_text)

    text = [resume_text_clean, jd_keywords_str]
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(text)
    match_score = round(cosine_similarity(count_matrix)[0][1] * 100, 2)

    resume_words = set(resume_text_clean.split())
    matched = [word for word in jd_keywords if word in resume_words]
    unmatched = [word for word in jd_keywords if word not in resume_words]

    matched = list(matched)
    unmatched = list(unmatched)

    highlighted_resume = []
    for word in resume_text.split():
        cleaned_word = re.sub(r'[.,;:()\[\]{}]', '', word.lower())
        if cleaned_word in matched:
            highlighted_resume.append(f'<span class="match">{word}</span>')
        elif cleaned_word in unmatched:
            highlighted_resume.append(f'<span class="unmatch">{word}</span>')
        else:
            highlighted_resume.append(word)
    resume_highlighted = ' '.join(highlighted_resume)

    highlighted_jd_text = highlight_jd_text(jd_text, matched, unmatched)

    top_keywords = get_top_keywords_from_jd(jd_text)

    return render_template(
        'result.html',
        score=match_score,
        matched=matched,
        unmatched=unmatched,
        resume_highlighted=resume_highlighted,
        jd_highlighted=highlighted_jd_text,
        jd_keywords=jd_keywords,
        top_keywords=top_keywords 
    )

def get_top_keywords_from_jd(jd_text, top_n=10):
    cleaned_text = clean_text(jd_text)
    tokens = cleaned_text.split()
    filtered_tokens = [token for token in tokens if token not in CUSTOM_STOPWORDS and len(token) > 2]
    freq = Counter(filtered_tokens)
    top_keywords = [word for word, count in freq.most_common(top_n)]
    return top_keywords

if __name__ == '__main__':
    app.run(debug=True)
