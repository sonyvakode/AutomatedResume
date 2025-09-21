
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from fuzzywuzzy import fuzz
import numpy as np
import os

MODEL = None
def get_embedding_model():
    global MODEL
    if MODEL is None:
        try:
            MODEL = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            MODEL = None
    return MODEL

def hard_match(resume_text, jd):
    # exact/fuzzy matching of must-have skills
    resume_lower = resume_text.lower()
    matches = []
    for skill in jd.get('must', []) + jd.get('good', []):
        score = fuzz.partial_ratio(skill.lower(), resume_lower)
        matches.append({'skill': skill, 'score': score})
    return matches

def semantic_similarity(resume_text, jd_text):
    model = get_embedding_model()
    if model is not None:
        try:
            emb = model.encode([resume_text, jd_text], convert_to_numpy=True)
            sim = float(cosine_similarity([emb[0]],[emb[1]])[0][0])
            return sim
        except Exception:
            model = None
    # fallback TF-IDF
    vec = TfidfVectorizer().fit_transform([resume_text, jd_text])
    sim = float(cosine_similarity(vec[0:1], vec[1:2])[0][0])
    return sim
