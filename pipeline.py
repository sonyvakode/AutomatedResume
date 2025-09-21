
from .parsers import extract_text, parse_jd, normalize_text
from .matching import hard_match, semantic_similarity
from .scorer import compute_final_score
from .db import init_db, save_jd, save_evaluation
import os, json

init_db()

def save_jd(title, content):
    return save_jd(title, content)

def evaluate_resume_from_files(resume_path, jd_id):
    # get jd by id from DB
    import sqlite3
    conn = sqlite3.connect('data/results.db')
    cur = conn.cursor()
    cur.execute('SELECT content FROM jds WHERE id=?', (jd_id,))
    row = cur.fetchone()
    if not row:
        jd_text = open('data/sample/job_description.txt','r',encoding='utf-8').read()
    else:
        jd_text = row[0]
    resume_text = extract_text(resume_path)
    resume_text = normalize_text(resume_text)
    jd_parsed = parse_jd(jd_text)
    hard = hard_match(resume_text, jd_parsed)
    sem = semantic_similarity(resume_text, jd_text)
    scored = compute_final_score(hard, sem)
    save_evaluation(jd_id, resume_path, scored['score'], scored['verdict'], scored['missing'])
    return {**scored, 'jd_parsed': jd_parsed}
