from flask import Flask, render_template, request
import pandas as pd
import docx2txt
import re
import spacy
from spacy.matcher import PhraseMatcher
from fuzzywuzzy import fuzz


app = Flask(__name__)
nlp = spacy.load("en_core_web_sm")

# Load the master skill list
skills_df = pd.read_csv("skills.csv")
skills_list = [str(skill).strip().lower() for skill in skills_df['skill'] if pd.notna(skill)]

def clean_text(text):
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    return text.lower()

def extract_skills_spacy(text):
    doc = nlp(clean_text(text))
    matcher = PhraseMatcher(nlp.vocab, attr='LOWER')
    patterns = [nlp.make_doc(skill) for skill in skills_list]
    matcher.add("SKILLS", patterns)
    matches = matcher(doc)
    found_skills = set([doc[start:end].text.lower() for _, start, end in matches])
    return found_skills

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/match', methods=['POST'])
def match():
    jd_text = request.form['job_description']
    resume_file = request.files['resume']

    # Extract text from resume
    resume_text = docx2txt.process(resume_file)

    jd_skills = set(extract_skills_spacy(jd_text))
    resume_skills = set(extract_skills_spacy(resume_text))


    # Find matches and misses
    matched = jd_skills.intersection(resume_skills)
    unmatched = jd_skills.difference(resume_skills)

    #Highlight Resume
    highlighted_resume = resume_text
    for skill in matched:
        highlighted_resume = re.sub(rf'\b{re.escape(skill)}\b',
                                f'<span class="match">{skill}</span>',
                                highlighted_resume,
                                flags=re.IGNORECASE)
    for skill in unmatched:
        highlighted_resume = re.sub(rf'\b{re.escape(skill)}\b',
                                f'<span class="unmatch">{skill}</span>',
                                highlighted_resume,
                                flags=re.IGNORECASE)

    # Highlight JD
    highlighted_jd = jd_text
    for skill in matched:
        highlighted_jd = re.sub(rf'\b{re.escape(skill)}\b', f'<span class="match">{skill}</span>', highlighted_jd, flags=re.IGNORECASE)
    for skill in unmatched:
        highlighted_jd = re.sub(rf'\b{re.escape(skill)}\b', f'<span class="unmatch">{skill}</span>', highlighted_jd, flags=re.IGNORECASE)

    score = round((len(matched) / len(jd_skills)) * 100, 2) if jd_skills else 0

    return render_template('result.html',
                           highlighted_jd=highlighted_jd,
                           matched=matched,
                           unmatched=unmatched,
                           highlighted_resume=highlighted_resume,
                           score=score)

if __name__ == '__main__':
    app.run(debug=True)
