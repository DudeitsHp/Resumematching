from flask import Flask, render_template, request
import docx2txt
import re
import spacy
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
from collections import Counter
import os
import fitz  # PyMuPDF


app = Flask(__name__)

# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# Define technical keywords list
TECH_KEYWORDS = {
     'api', 'aws lambda', 'aws', 'angular', 'apache maven', 'azure blob storage',
     'azure functions', 'azure virtual machines', 'boost', 'c++', 'css', 'decision trees',
     'django', 'docker', 'ec2', 'express.js', 'flask', 'google cloud functions',
     'google cloud platform', 'google cloud storage', 'google compute engine', 'google kubernetes engine',
     'html', 'hibernate', 'iaas', 'junit', 'java', 'javafx', 'javascript', 'kubernetes', 'linear regression',
     'logistic regression', 'mean', 'mern', 'machine learning', 'matplotlib', 'microsoft azure',
     'microsoft sql server', 'mongodb', 'mysql', 'neural networks', 'nosql', 'node.js', 'numpy',
     'opencv', 'oracle database', 'php', 'poco', 'paas', 'pandas', 'postgresql', 'power bi', 'python',
     'qt', 'r', 'restful apis', 'react', 'responsive design', 'ruby', 's3', 'sdl', 'sql', 'sqlite', 'saas',
     'scikit-learn', 'spring', 'supervised learning', 'support vector machines', 'tableau', 'tensorflow',
     'unsupervised learning', 'vue.js', 'ab initio', 'agile', 'airflow', 'analysts', 'azure', 'bash', 'big data',
     'ci/cd', 'data integration', 'data lake', 'data modeling', 'data pipeline', 'data processing',
     'data scientists', 'data warehouse', 'data', 'database administrators', 'etl', 'express', 'gcp', 'git',
     'graphql', 'jquery', 'jenkins', 'jira', 'keras', 'linux', 'node', 'pipelines', 'quality assurance',
     'rest', 'scrum', 'spark','snow'
}

# Custom stopwords (can expand this list)
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

    # Dictionary-based match (exact)
    dict_matches = [word for word in words if word in TECH_KEYWORDS]

    # NLP parsing
    doc = nlp(text)
    raw_terms = [chunk.text.lower() for chunk in doc.noun_chunks] + \
                [ent.text.lower() for ent in doc.ents]

    # Clean and normalize
    filtered_terms = set()
    trailing_stopwords = {'and', 'or', 'with', 'of', 'for', 'to', 'in'}

    for phrase in raw_terms:
        phrase = clean_text(phrase.strip())

        # Remove trailing stopwords
        tokens = phrase.split()
        while tokens and tokens[-1] in trailing_stopwords:
            tokens.pop()
        phrase = ' '.join(tokens)

        # Skip overly long or vague phrases
        if len(phrase.split()) > 3:
            continue
        if phrase in CUSTOM_STOPWORDS:
            continue

        # Match dictionary-defined technical terms
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/match', methods=['POST'])
def match_resume():
    resume_file = request.files['resume']
    jd_text = request.form['jd']
    
    # Determine file type
    filename = resume_file.filename
    extension = os.path.splitext(filename)[1].lower()
    
    if extension == '.docx':
        resume_text = docx2txt.process(resume_file)
    elif extension == '.pdf':
        resume_text = extract_text_from_pdf(resume_file)
    else:
        return "Unsupported file type. Please upload a .docx or .pdf", 400
    
    resume_text = docx2txt.process(resume_file)

    # Extract technical keywords from JD
    jd_keywords = extract_technical_keywords(jd_text)
    jd_keywords_str = ' '.join(jd_keywords)

    # Clean resume text and convert to lowercase
    resume_text_clean = clean_text(resume_text)

    # Vectorize and compute cosine similarity
    text = [resume_text_clean, jd_keywords_str]
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(text)
    match_score = round(cosine_similarity(count_matrix)[0][1] * 100, 2)

    # Highlight matches and unmatched keywords in resume
    resume_words = set(resume_text_clean.split())
    matched = [word for word in jd_keywords if word in resume_words]
    unmatched = [word for word in jd_keywords if word not in resume_words]

    # Highlight resume content
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

    return render_template(
        'result.html',
        score=match_score,
        matched=matched,
        unmatched=unmatched,
        resume_highlighted=resume_highlighted,
        jd_keywords=jd_keywords
    )

if __name__ == '__main__':
    app.run(debug=True)