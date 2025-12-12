import re
import docx2txt
import spacy
from spacy.matcher import PhraseMatcher
from collections import Counter
import pandas as pd
from pdfminer.high_level import extract_text

# Load NLP model once
nlp = spacy.load("en_core_web_sm")

def load_skills(csv_path="skills.csv"):
    """Loads skills from CSV and creates a Spacy matcher."""
    try:
        skills_df = pd.read_csv(csv_path)
        # Ensure 'skill' column exists and filter valid skills
        skills_list = [str(skill).strip().lower() for skill in skills_df['skill'] if pd.notna(skill)]
        
        matcher = PhraseMatcher(nlp.vocab, attr='LOWER')
        patterns = [nlp.make_doc(skill) for skill in skills_list]
        matcher.add("SKILLS", patterns)
        return matcher
    except Exception as e:
        print(f"Error loading skills: {e}")
        return None

def clean_text(text):
    """
    Cleans text while preserving important characters for technical skills
    (e.g., C++, C#, .NET, Node.js).
    """
    # Replace newlines/tabs with space
    text = text.replace('\n', ' ').replace('\t', ' ')
    
    # Keep alphanumeric, space, and specific chars: +, #, ., -
    # The original regex [^a-zA-Z\s] was too aggressive.
    # We allow: a-z, A-Z, 0-9, space, +, #, ., -
    text = re.sub(r'[^a-zA-Z0-9\s\+\#\.\-]', '', text)
    
    # Normalize multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text.lower()

import io

def extract_text_from_pdf(file_stream):
    """Extracts text from a PDF file stream using pdfminer.six."""
    try:
        # Create a BytesIO object from the file stream content
        # This ensures pdfminer treats it as a binary file object and not a path or problematic stream
        if hasattr(file_stream, 'read'):
            # It's a stream, read it into bytes
            file_content = file_stream.read()
            # If we need to reuse the stream later in app, we might need to seek(0) but here we just consume it.
            # However, flask FileStorage might need to be seeked if it was read before.
            # Safe bet: create fresh BytesIO
            stream = io.BytesIO(file_content)
        else:
            # Assume it's bytes already? Or just pass it
            stream = file_stream

        text = extract_text(stream)
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def extract_text_from_docx(file_stream):
    """Extracts text from a DOCX file stream."""
    try:
        return docx2txt.process(file_stream)
    except Exception as e:
        print(f"Error reading DOCX: {e}")
        return ""

def extract_skills(text, matcher):
    """Extracts skills using the Spacy PhraseMatcher."""
    # We don't clean text BEFORE passing to nlp if we want to rely on Spacy's tokenization 
    # but for matching our specific keyword list which is lowercased, cleaning is helpful.
    # However, 'clean_text' might merge words if we aren't careful.
    # Let's clean it but ensure spacing is preserved.
    cleaned_txt = clean_text(text)
    doc = nlp(cleaned_txt)
    matches = matcher(doc)
    
    found_skills = []
    for match_id, start, end in matches:
        span = doc[start:end]
        found_skills.append(span.text.lower())
    
    return Counter(found_skills)

def highlight_skills(text, skills, css_class):
    """Highlights found skills in the text with a given CSS class."""
    # We need a robust replacement that doesn't break HTML or re-replace replaced terms.
    # But since we are just displaying simple text, a regex replace is okay for now.
    # Note: text here should be the ORIGINAL text (or close to it) for display, 
    # but highlighting on raw resume text can be messy.
    # For simplicity, we'll highlight on the cleaned version or just best-effort on raw.
    
    # Let's clean the text for display to make highlighting easier and consistent
    # with what was matched.
    display_text = clean_text(text) 
    
    highlighted = display_text
    # Sort skills by length (descending) to avoid partial replacement issues (e.g. replacing 'C' in 'C++')
    sorted_skills = sorted(list(skills), key=len, reverse=True)
    
    for skill in sorted_skills:
        # Escape special chars in skill for regex (like + or .)
        pattern = re.compile(rf"\b{re.escape(skill)}\b", re.IGNORECASE)
        replacement = f'<span class="{css_class}">{skill}</span>'
        highlighted = pattern.sub(replacement, highlighted)
        
    return highlighted
