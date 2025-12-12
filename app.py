from flask import Flask, render_template, request
import os
from utils import load_skills, extract_skills, extract_text_from_pdf, extract_text_from_docx, highlight_skills

app = Flask(__name__)

# Load matcher once at startup
skill_matcher = load_skills("skills.csv")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/match', methods=['POST'])
def match():
    if 'job_description' not in request.form or 'resume' not in request.files:
        return "Missing data", 400

    jd_text = request.form['job_description']
    resume_file = request.files['resume']
    
    filename = resume_file.filename.lower()
    resume_text = ""

    if filename.endswith('.pdf'):
        resume_text = extract_text_from_pdf(resume_file)
    elif filename.endswith('.docx'):
        resume_text = extract_text_from_docx(resume_file)
    else:
        return "Invalid file format. Please upload PDF or DOCX.", 400

    if not resume_text:
        return "Could not extract text from resume.", 400

    if not skill_matcher:
         return "Skill database not loaded.", 500

    jd_counter = extract_skills(jd_text, skill_matcher)
    resume_counter = extract_skills(resume_text, skill_matcher)

    jd_skills_set = set(jd_counter.keys())
    resume_skills_set = set(resume_counter.keys())

    matched = jd_skills_set.intersection(resume_skills_set)
    unmatched = jd_skills_set.difference(resume_skills_set)
    
    # Calculate score
    # Weighted score: (sum of weights of matched skills / sum of weights of all JD skills) * 100
    # Weight = frequency in JD
    total_weight = sum(jd_counter.values())
    matched_weight = sum(jd_counter[skill] for skill in matched)
    score = round((matched_weight / total_weight) * 100, 2) if total_weight else 0

    # Highlight skills
    highlighted_jd = highlight_skills(jd_text, matched, "match")
    highlighted_jd = highlight_skills(highlighted_jd, unmatched, "unmatch")
    
    highlighted_resume = highlight_skills(resume_text, matched, "match")
    highlighted_resume = highlight_skills(highlighted_resume, unmatched, "unmatch")

    return render_template(
        'result.html', 
        highlighted_jd=highlighted_jd, 
        matched=matched, 
        unmatched=unmatched, 
        highlighted_resume=highlighted_resume, 
        score=score
    )

if __name__ == '__main__':
    app.run(debug=True)
