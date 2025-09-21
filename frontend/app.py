import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import io, json, sqlite3
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# -------------------- Directories --------------------
os.makedirs('data/resumes', exist_ok=True)

# -------------------- Page Config --------------------
st.set_page_config(page_title="Automated Resume Relevance Dashboard", layout="wide")

# -------------------- CSS Styling --------------------
st.markdown("""
<style>
/* Headings */
h1,h2,h3 {color:#1f2937; font-family: 'Segoe UI', sans-serif;}

/* Buttons */
.stButton>button {
    background-color: #1f77b4; 
    color: white;
    border-radius:8px;
    font-weight: bold;
}
.stButton>button:hover {
    background-color: #145a8a;
    transform: scale(1.02);
    transition: 0.2s;
}

/* File uploader */
.stFileUploader>div {
    border: 2px dashed #1f77b4; 
    border-radius: 10px; 
    padding: 10px;
}

/* Sidebar */
[data-testid="stSidebar"] > div:first-child {
    background-color: #1f77b4;
    color: white;
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label {
    color: white;
}

/* Shortlist dashboard table */
.stDataFrame th {
    background-color: #2c3e50 !important;
    color: white !important;
}
.stDataFrame tbody tr:nth-child(even) {background-color: #f9f9f9 !important;}
.stDataFrame tbody tr:hover {background-color: #e6f7ff !important;}
</style>
""", unsafe_allow_html=True)

st.title("📄 Automated Resume Relevance Dashboard")

# -------------------- Sidebar Menu --------------------
menu = st.sidebar.selectbox(
    "Menu",
    ["Placement Team: Upload JD", "Students: Upload Resume", "Shortlist Dashboard", "Help / Samples"]
)

DB_PATH = "results.db"

# -------------------- Utilities --------------------
def extract_docx_text(file_path):
    doc = Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def normalize_text(text):
    return text.lower().replace('\n',' ').strip()

def parse_jd(jd_text):
    lines = jd_text.splitlines()
    title = lines[0] if lines else "Role"
    must_have_skills = [line.strip() for line in lines[1:] if line.strip()]
    return {"role_title": title, "must_have_skills": must_have_skills, "good_to_have_skills": [], "qualifications": []}

def hard_match(resume_text, jd_parsed):
    missing = []
    for skill in jd_parsed.get('must_have_skills', []):
        if skill.lower() not in resume_text:
            missing.append(skill)
    score = max(0, 100 - len(missing)*10)
    return score, missing

def semantic_score(resume_text, jd_text):
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([resume_text, jd_text])
    sim = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    return int(sim*100)

def compute_final_score(hard_score, sem_score):
    final = round(0.6*hard_score + 0.4*sem_score, 2)
    verdict = "High" if final>=75 else "Medium" if final>=50 else "Low"
    return {"score": final, "verdict": verdict}

# -------------------- Student Resume Upload & Evaluation --------------------
if menu == "Students: Upload Resume":
    st.header("Resume Evaluation")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS evaluations (id INTEGER PRIMARY KEY AUTOINCREMENT, jd_id INTEGER, resume_name TEXT, score REAL, verdict TEXT, missing TEXT)")
    cur.execute("SELECT id, title, content FROM jds")
    jds = cur.fetchall()
    conn.close()

    resume_file = st.file_uploader("Upload Resume (DOCX/TXT)", type=['docx','txt'])
    jd_available = len(jds) > 0
    jd_dict = {f"{row[1]} (ID:{row[0]})": (row[0], row[2]) for row in jds} if jd_available else {}

    # -------- JD Filters --------
    if jd_available:
        col1, col2, col3 = st.columns(3)
        with col1:
            locs = sorted({title.split("|")[-1].strip() for _, title, _ in jds})
            location_filter = st.selectbox("Filter by Location", ["All"] + locs)
        with col2:
            job_id_search = st.text_input("Search by Job ID")
        with col3:
            jd_sel = st.selectbox("Select Job to Apply", list(jd_dict.keys()))
    else:
        st.info("No JD posted yet.")
        jd_sel = None

    if st.button("Evaluate Resume") and resume_file:
        resume_path = os.path.join("data/resumes", resume_file.name)
        with open(resume_path,'wb') as f:
            f.write(resume_file.getvalue())

        if resume_file.name.endswith(".docx"):
            resume_text = extract_docx_text(resume_path)
        else:
            resume_text = open(resume_path,'r',encoding='utf-8').read()
        resume_text = normalize_text(resume_text)

        missing = []
        sem_score = 0
        hard_score = 0
        final_score = 0
        verdict = "No JD"
        suggestions = []

        if jd_available and jd_sel:
            jd_id, jd_content = jd_dict[jd_sel]
            jd_parsed = parse_jd(jd_content)
            jd_text = normalize_text(jd_content)

            hard_score, missing = hard_match(resume_text, jd_parsed)
            sem_score = semantic_score(resume_text, jd_text)
            scored = compute_final_score(hard_score, sem_score)

            final_score = scored['score']
            verdict = scored['verdict']

            if verdict != 'High':
                if missing:
                    suggestions.append(f"Missing: {', '.join(missing)}")
                suggestions.append("Add relevant certifications, projects, and measurable achievements.")

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("INSERT INTO evaluations (jd_id, resume_name, score, verdict, missing) VALUES (?, ?, ?, ?, ?)",
                        (jd_id, resume_file.name, final_score, verdict, json.dumps(missing)))
            conn.commit()
            conn.close()

        # -------- Results Layout --------
        col1, col2 = st.columns([2,2])

        with col1:
            st.subheader("Score Breakdown")
            fig, ax = plt.subplots(figsize=(6,3))
            ax.barh(["Semantic Match (Context)", "Hard Match (Keywords)"], [sem_score, hard_score], color=["skyblue","steelblue"])
            ax.set_xlabel("Score (%)")
            st.pyplot(fig)

            st.markdown(f"**Verdict:** {verdict} | **Relevance Score:** {final_score}/100")

        with col2:
            st.subheader("Feedback & Missing Elements")
            if missing:
                for item in missing:
                    st.write(f"- {item}")
            if suggestions:
                st.markdown("**Suggestions:** " + " ".join(suggestions))
