import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import io, json, sqlite3
from pathlib import Path
import pandas as pd
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# -------------------- Directories --------------------
os.makedirs('data/resumes', exist_ok=True)

# -------------------- Page Config --------------------
st.set_page_config(page_title="Automated Resume Relevance Dashboard", layout="wide")

st.markdown("""
<style>
body {background: linear-gradient(120deg, #f0f2f6 0%, #d9e2ef 100%);}
section.main {background-color: #ffffff; border-radius:15px; padding:20px; box-shadow: 0px 4px 25px rgba(0,0,0,0.1);}
h1,h2,h3{color:#1f77b4;}
.stButton>button {background-color: #1f77b4; color: white;}
.stFileUploader>div{border: 2px dashed #1f77b4; border-radius: 10px; padding: 10px;}
</style>
""", unsafe_allow_html=True)

st.title("📄 Automated Resume Relevance Dashboard")

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
    final = int(0.6*hard_score + 0.4*sem_score)
    verdict = "High" if final>=75 else "Medium" if final>=50 else "Low"
    return {"score": final, "verdict": verdict}

# -------------------- Placement Team JD Upload --------------------
if menu == "Placement Team: Upload JD":
    st.header("Upload Job Description (Placement Team)")
    with st.form("jd_form"):
        title = st.text_input("Job Title")
        company = st.text_input("Company Name")
        locations = ["Delhi NCR", "Bangalore", "Hyderabad", "Pune", "Chennai", "Mumbai"]
        location = st.multiselect("Job Location(s)", options=locations, default=["Delhi NCR"])
        jd_txt = st.text_area("Paste JD text here", height=200)
        jd_file = st.file_uploader("Or upload JD file (.txt/.md)", type=['txt','md'])
        submitted = st.form_submit_button("Upload JD")
        if submitted:
            if jd_file is not None:
                jd_txt = jd_file.getvalue().decode('utf-8', errors='ignore')
            if not jd_txt.strip() or not title.strip() or not company.strip() or not location:
                st.error("Provide all details and JD content/file.")
            else:
                jd_full_title = f"{title} | {company} | {', '.join(location)}"
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS jds (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        content TEXT
                    )
                """)
                cur.execute("INSERT INTO jds (title, content) VALUES (?, ?)", (jd_full_title, jd_txt))
                conn.commit()
                jd_id = cur.lastrowid
                conn.close()
                st.success(f"JD uploaded successfully with ID: {jd_id}")

# -------------------- Student Resume Upload & Evaluation --------------------
if menu == "Students: Upload Resume":
    st.header("Upload Resume (Students)")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS evaluations (id INTEGER PRIMARY KEY AUTOINCREMENT, jd_id INTEGER, resume_name TEXT, score INTEGER, verdict TEXT, missing TEXT)")
    cur.execute("SELECT id, title, content FROM jds")
    jds = cur.fetchall()
    conn.close()

    resume_file = st.file_uploader("Upload Resume (DOCX/TXT)", type=['docx','txt'])
    jd_available = len(jds) > 0
    jd_dict = {f"{row[1]} (ID:{row[0]})": (row[0], row[2]) for row in jds} if jd_available else {}

    if jd_available:
        jd_sel = st.selectbox("Select Job Requirement", list(jd_dict.keys()))
    else:
        st.info("No JD posted yet. You can still upload your resume to get general skill improvement suggestions.")
        jd_sel = None

    if st.button("Parse & Evaluate") and resume_file:
        resume_path = os.path.join("data/resumes", resume_file.name)
        with open(resume_path,'wb') as f:
            f.write(resume_file.getvalue())

        if resume_file.name.endswith(".docx"):
            resume_text = extract_docx_text(resume_path)
        else:
            resume_text = open(resume_path,'r',encoding='utf-8').read()
        resume_text = normalize_text(resume_text)

        missing = []
        final_score = 0
        verdict = "No JD"
        suggestions = []

        if jd_available:
            jd_id, jd_content = jd_dict[jd_sel]
            jd_parsed = parse_jd(jd_content)
            jd_text = normalize_text(jd_content)

            hard_score, missing = hard_match(resume_text, jd_parsed)
            sem_score = semantic_score(resume_text, jd_text)
            scored = compute_final_score(hard_score, sem_score)
            scored['missing'] = missing

            final_score = scored['score']
            verdict = scored['verdict']

            if scored['verdict'] != 'High':
                if scored['missing']:
                    suggestions.append(f"Missing skills/projects: {', '.join(scored['missing'])}")
                suggestions.append("Add relevant certifications or projects to improve relevance.")

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("INSERT INTO evaluations (jd_id, resume_name, score, verdict, missing) VALUES (?, ?, ?, ?, ?)",
                        (jd_id, resume_file.name, final_score, verdict, json.dumps(scored['missing'])))
            conn.commit()
            conn.close()
        else:
            suggestions.append("JD not posted yet. Focus on including key skills, projects, and certifications relevant to your field.")

        st.subheader("Evaluation Results")
        if jd_available:
            st.metric("Relevance Score", final_score)
            st.markdown(f"**Verdict:** <span style='color:{'green' if verdict=='High' else 'orange' if verdict=='Medium' else 'red'};'>{verdict}</span>", unsafe_allow_html=True)
        else:
            st.info("JD not available. General suggestions are provided below.")

        if missing:
            st.write("Missing Skills/Projects/Certifications:")
            for item in missing:
                st.markdown(f"<span style='color:red; font-weight:bold'>● {item}</span>", unsafe_allow_html=True)
        if suggestions:
            st.write("Suggestions for Improvement:")
            for s in suggestions:
                st.write(f"- {s}")

# -------------------- Shortlist Dashboard --------------------
if menu == "Shortlist Dashboard":
    st.header("Shortlist Dashboard")
    st.info("Filter resumes by Job Title, Company, Location, and Minimum Score")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT e.id, j.title, e.resume_name, e.score, e.verdict, e.missing 
            FROM evaluations e 
            JOIN jds j ON e.jd_id = j.id
        """)
        evals = cur.fetchall()
    except sqlite3.OperationalError:
        evals = []
    conn.close()

    if not evals:
        st.info("No evaluations yet.")
    else:
        df = pd.DataFrame(evals, columns=["ID","JD Title","Resume","Score","Verd
