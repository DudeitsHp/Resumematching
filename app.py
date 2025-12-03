from flask import Flask, render_template, request
import pandas as pd
import docx2txt
import re
import spacy
from spacy.matcher import PhraseMatcher
from fuzzywuzzy import fuzz
from collections import Counter


app = Flask(__name__)
nlp = spacy.load("en_core_web_sm")

# Load the master skill list
skills_df = pd.read_csv("skills.csv")
skills_list = [str(skill).strip().lower() for skill in skills_df['skill'] if pd.notna(skill)]

def clean_text(text):
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    return text.lower()

def extract_skills_spacy(text):
    """Return a Counter of skill occurrences in the given text."""
    doc = nlp(clean_text(text))
    matches = skill_matcher(doc)
    found = [doc[start:end].text.lower() for _, start, end in matches]
    return Counter(found)

# Build a PhraseMatcher that can recognise both single‑ and multi‑word skills
skill_matcher = PhraseMatcher(nlp.vocab, attr='LOWER')
patterns = [nlp.make_doc(skill) for skill in skills_list]
skill_matcher.add("SKILLS", patterns)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/match', methods=['POST'])
def match():
    jd_text = request.form['job_description']
    resume_file = request.files['resume']
    resume_text = docx2txt.process(resume_file)
    jd_counter = extract_skills_spacy(jd_text)
    resume_counter = extract_skills_spacy(resume_text)
    jd_skills_set = set(jd_counter.keys())
    resume_skills_set = set(resume_counter.keys())
    matched = jd_skills_set.intersection(resume_skills_set)
    unmatched = jd_skills_set.difference(resume_skills_set)
    # Highlight matched skills in both texts
    # Highlight matched and unmatched skills in both texts
    def highlight(text, skills, css_class):
        highlighted = text
        for skill in skills:
            pattern = rf"\\b{re.escape(skill)}\\b"
            replacement = f"<span class=\"{css_class}\">{skill}</span>"
            highlighted = re.sub(pattern, replacement, highlighted, flags=re.IGNORECASE)
        return highlighted

    highlighted_jd = highlight(jd_text, matched, "match")
    highlighted_jd = highlight(highlighted_jd, unmatched, "unmatch")
    highlighted_resume = highlight(resume_text, matched, "match")
    highlighted_resume = highlight(highlighted_resume, unmatched, "unmatch")
    # Compute weighted score based on JD skill frequencies
    total_weight = sum(jd_counter.values())
    matched_weight = sum(jd_counter[skill] for skill in matched)
    score = round((matched_weight / total_weight) * 100, 2) if total_weight else 0
    return render_template('result.html', highlighted_jd=highlighted_jd, matched=matched, unmatched=unmatched, highlighted_resume=highlighted_resume, score=score)

if __name__ == '__main__':
    app.run(debug=True)
