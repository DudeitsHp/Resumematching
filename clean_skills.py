import pandas as pd
import re
import shutil
import os

def clean_skills():
    input_file = 'skills.csv'
    backup_file = 'skills.csv.bak'
    
    # Create backup
    if os.path.exists(input_file):
        shutil.copy(input_file, backup_file)
        print(f"Backup created at {backup_file}")
    else:
        print(f"Error: {input_file} not found.")
        return

    try:
        # Load the skills file
        # Trying to read with default settings first, similar to notebook
        try:
            skills_df = pd.read_csv(input_file)
        except pd.errors.ParserError:
             # Fallback if simple read fails (as seen in notebook logic, though notebook used header=None fallback)
             # The notebook showed:
             # df = pd.read_csv('skills.csv', header=None, encoding='utf-8')
             # But let's stick to the simpler logic first if the file has a header 'skill' as implied by later code
             # "for skill in skills_df['skill']:" implies there is a 'skill' column.
             # However, the notebook also had a block handling header=None.
             # Let's try to be robust.
             skills_df = pd.read_csv(input_file, header=None, names=['skill'])

        # Ensure 'skill' column exists
        if 'skill' not in skills_df.columns:
             # If no 'skill' column, maybe it was read without header and assigned default int columns
             if 0 in skills_df.columns:
                 skills_df.rename(columns={0: 'skill'}, inplace=True)
             else:
                 print("Error: Could not identify 'skill' column.")
                 return

        print(f"Original row count: {len(skills_df)}")

        skills_list = []
        stop_words = ["is", "be", "as", "do", "or", "and", "of", "to", "in", "for", "with", "by", "an", "on"]
        ignore_keywords = ["degree", "bachelors", "communication", "good", "strong", "preferred", "knowledge", "fresher", "excellent", "internal", "relations", "methods"]

        for skill in skills_df['skill']:
            if pd.isna(skill):
                continue
            
            # Ensure string
            skill = str(skill)
            skill = skill.strip().lower()
            
            # Skip short or non-informative words
            if len(skill) < 3:
                continue
            
            if skill in stop_words:
                continue
            
            if re.match(r"^[a-z]{1,2}$", skill):  # single/double letters like 'pf', 'll'
                continue
            
            if any(word in skill for word in ignore_keywords):
                continue

            # Keep only meaningful entries
            skills_list.append(skill)

        # Create new DataFrame
        cleaned_df = pd.DataFrame(skills_list, columns=['skill'])
        
        # Remove duplicates
        cleaned_df.drop_duplicates(inplace=True)
        
        print(f"Cleaned row count: {len(cleaned_df)}")
        
        # Save back to csv
        cleaned_df.to_csv(input_file, index=False)
        print(f"Successfully updated {input_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    clean_skills()
