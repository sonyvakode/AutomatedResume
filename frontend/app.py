import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import io, json, sqlite3
from pathlib import Path
import pandas as pd
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import PyPDF2

# -------------------- Directories --------------------
os.makedirs('data/resumes', exist_ok=True)
os.makedirs('data/sample', exist_ok=True)

# -------------------- Page Config --------------------
st.set_page_config(page_title="Automated Resume Relevance Dashboard", layout="wide")
st.title("📄 Automated Resume Relevance Dashboard")

# -------------------- CSS Styling --------------------
st.markdown("""
<style>
h1,h2,h3 {color:#1f2937; font-family: 'Segoe UI', sans-serif;}
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
.stFileUploader>div {border: 2px dashed #1f77b4; border-radius: 10px; padding: 10px;}
[data-testid="stSidebar"] > div:first-child {background-color: #1f77b4; color: white;}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label {color: white;}
.stDataFrame table {border: 1px solid #ddd; border-radius: 6px;}
.stDataFrame th {background-color: #2c3e50 !important; color: white !important; font-weight: 600 !important;}
.stDataFrame tbody tr:nth-child(even) {background-color: #f9f9f9 !important;}
.stDataFrame tbody tr:hover {background-color: #e6f7ff !important;}
</style>
""", unsafe_allow_html=True)

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

def extract_pdf_text(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def normalize_text(text):
    return text.lower().replace('\n',' ').strip()

def parse_jd(jd_text):
    lines = jd_text.splitlines()
    title = lines[0] if lines else "Role"
    must_have_skills = [line.strip() for line in lines[1:] if line.strip()]
    return {"role_title": title, "must_have_skills": must_have_skills}

def hard_match(resume_text, jd_parsed):
    missing = [skill for skill in jd_parsed.get('must_have_skills', []) if skill.lower() not in resume_text]
    score = max(0, 100 - len(missing)*10)
    return score, missing

def semantic_score(resume_text, jd_text):
    vectorizer = TfidfVectorizer(stop_words='english')
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
                st.success(f"✅ JD uploaded successfully with ID: {jd_id}")

# -------------------- Student Resume Upload & Evaluation --------------------
if menu == "Students: Upload Resume":
    st.header("Upload Resume (Students)")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS evaluations (id INTEGER PRIMARY KEY AUTOINCREMENT, jd_id INTEGER, resume_name TEXT, score INTEGER, verdict TEXT, missing TEXT)")
    cur.execute("SELECT id, title, content FROM jds")
    jds = cur.fetchall()
    conn.close()

    resume_file = st.file_uploader("Upload Resume (DOCX/TXT/PDF)", type=['docx','txt','pdf'])
    jd_dict = {f"{row[1]} (ID:{row[0]})": (row[0], row[2]) for row in jds} if jds else {}
    jd_available = bool(jd_dict)

    jd_sel = st.selectbox("Select Job Requirement", list(jd_dict.keys())) if jd_available else None
    if not jd_available:
        st.info("No JD posted yet. You can still upload your resume to get general suggestions.")

    if st.button("Parse & Evaluate") and resume_file:
        with st.spinner("Evaluating resume..."):
            resume_path = os.path.join("data/resumes", resume_file.name)
            with open(resume_path,'wb') as f:
                f.write(resume_file.getvalue())

            file_ext = resume_file.name.split('.')[-1].lower()
            if file_ext == "docx":
                resume_text = extract_docx_text(resume_path)
            elif file_ext == "pdf":
                resume_text = extract_pdf_text(resume_path)
            else:
                resume_text = open(resume_path,'r',encoding='utf-8').read()
            resume_text = normalize_text(resume_text)

            missing, final_score, verdict, suggestions = [], 0, "No JD", []

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

                # Concise suggestions only
                if scored['verdict'] != 'High' and scored['missing']:
                    suggestions = [f"Add: {', '.join(scored['missing'])}"]

                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("INSERT INTO evaluations (jd_id, resume_name, score, verdict, missing) VALUES (?, ?, ?, ?, ?)",
                            (jd_id, resume_file.name, final_score, verdict, json.dumps(scored['missing'])))
                conn.commit()
                conn.close()
            else:
                suggestions = ["Focus on key skills and relevant projects."]

            st.subheader("Evaluation Results")
            if jd_available:
                st.metric("Relevance Score", final_score)
                st.markdown(f"**Verdict:** {verdict}")
            else:
                st.info("JD not available. General suggestions provided.")

            if suggestions:
                st.write("Suggestions:")
                for s in suggestions: st.write(f"- {s}")

# -------------------- Shortlist Dashboard --------------------
if menu == "Shortlist Dashboard":
    st.header("Placement Team Dashboard")
    st.subheader("Resume Shortlisting Table")

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
        df = pd.DataFrame(evals, columns=["ID","JD Title","Resume","Score","Verdict","Missing"])
        df[['Job Title','Company','Location']] = df['JD Title'].str.split('|', expand=True)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        df['Shortlisted'] = df['Verdict'].apply(lambda v: "YES" if v in ["High", "Medium"] else "NO")

        col1, col2, col3 = st.columns(3)
        with col1: role_filter = st.multiselect("Filter by Role", sorted(df['Job Title'].unique()), [])
        with col2: loc_filter = st.multiselect("Filter by Location", sorted(df['Location'].unique()), [])
        with col3: shortlist_filter = st.selectbox("Shortlisted Only?", ["All","YES","NO"])

        if role_filter: df = df[df['Job Title'].isin(role_filter)]
        if loc_filter: df = df[df['Location'].isin(loc_filter)]
        if shortlist_filter != "All": df = df[df['Shortlisted']==shortlist_filter]

        st.dataframe(df[['Resume','Job Title','Company','Location','Score','Verdict','Shortlisted','Missing']], use_container_width=True)

# -------------------- Help / Samples --------------------
if menu == "Help / Samples":
    st.header("Help & Sample Data")
    st.write("Upload JD first, then student resumes to evaluate.")

    sample_jd_path = Path('data/sample/job_description.txt')
    sample_resume_path = Path('data/sample/sample_resume.txt')

    if not sample_jd_path.exists():
        sample_jd_path.write_text("Software Engineer\nPython\nSQL\nMachine Learning\nCommunication Skills")
    if not sample_resume_path.exists():
        sample_resume_path.write_text("John Doe\nExperienced in Python and SQL\nWorked on Machine Learning projects\nExcellent communication skills")

    st.subheader("Sample JD")
    st.code(sample_jd_path.read_text())
    st.subheader("Sample Resume")
    st.code(sample_resume_path.read_text())
