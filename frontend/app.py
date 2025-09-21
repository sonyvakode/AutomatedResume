# ---------------------- app.py ----------------------
import sys, os

# Fix import path for src folder (since app.py is in frontend/)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import io, json, sqlite3
from pathlib import Path
import pandas as pd
from src import parsers, matching, scorer  # db functions replaced with direct SQLite

# Ensure data folder exists
os.makedirs('data', exist_ok=True)
os.makedirs('data/resumes', exist_ok=True)

# ------------------ Background Styling ------------------
st.set_page_config(page_title="Resume Relevance Dashboard", layout="wide")
page_bg_img = """
<style>
body {
background-color: #f5f5f5;
}
section.main {
background-color: #ffffff;
border-radius: 15px;
padding: 20px;
box-shadow: 0px 0px 15px rgba(0,0,0,0.1);
}
h1, h2, h3 {
color: #1f77b4;
}
</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)

st.title("📄 Automated Resume Relevance Check — Dashboard")

menu = st.sidebar.selectbox(
    "Menu", 
    ["Placement Team: Upload JD", "Students: Upload Resume", "Shortlist Dashboard", "Help / Samples"]
)

# ------------------ JD Upload ------------------
if menu == "Placement Team: Upload JD":
    st.header("Upload Job Description (Placement Team)")
    with st.form("jd_form"):
        title = st.text_input("Job Title")
        company = st.text_input("Company Name")
        location = st.text_input("Location")
        jd_txt = st.text_area("Paste JD text here", height=200)
        jd_file = st.file_uploader("Or upload JD file (.txt/.md)", type=['txt','md'])
        submitted = st.form_submit_button("Upload JD")
        if submitted:
            if jd_file is not None:
                jd_txt = jd_file.getvalue().decode('utf-8', errors='ignore')
            if not jd_txt.strip() or not title.strip() or not company.strip() or not location.strip():
                st.error("Please provide all details and JD content/file.")
            else:
                jd_full_title = f"{title} | {company} | {location}"
                # Direct SQLite insertion
                conn = sqlite3.connect('data/results.db')
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS jds (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)")
                cur.execute("INSERT INTO jds (title, content) VALUES (?, ?)", (jd_full_title, jd_txt))
                conn.commit()
                jd_id = cur.lastrowid
                conn.close()
                st.success(f"JD uploaded successfully with ID: {jd_id}")

# ------------------ Student Resume Upload ------------------
if menu == "Students: Upload Resume":
    st.header("Resume Upload (Students)")
    # Fetch JDs directly
    conn = sqlite3.connect('data/results.db')
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS jds (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS evaluations (id INTEGER PRIMARY KEY AUTOINCREMENT, jd_id INTEGER, resume_name TEXT, score INTEGER, verdict TEXT, missing TEXT)")
    cur.execute("SELECT id, title FROM jds")
    jds = cur.fetchall()
    conn.close()
    
    jd_dict = {f"{row[1]} (ID:{row[0]})": row[0] for row in jds}
    if not jd_dict:
        st.warning("No job requirements available. Please wait for Placement Team to upload JD.")
    else:
        jd_sel = st.selectbox("Select Job Requirement", list(jd_dict.keys()))
        resume_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=['pdf','docx','txt'])
        if st.button("Evaluate") and resume_file:
            resume_path = os.path.join("data/resumes", resume_file.name)
            with open(resume_path,'wb') as f:
                f.write(resume_file.getvalue())
            
            # Extract text
            resume_text = parsers.extract_text(resume_path)
            resume_text = parsers.normalize_text(resume_text)

            # Get JD content
            jd_id = jd_dict[jd_sel]
            conn = sqlite3.connect('data/results.db')
            cur = conn.cursor()
            cur.execute("SELECT content FROM jds WHERE id=?",(jd_id,))
            jd_content = cur.fetchone()[0]
            conn.close()

            # Parse JD
            jd_parsed = parsers.parse_jd(jd_content)

            # Step 1: Hard Match
            hard = matching.hard_match(resume_text, jd_parsed)

            # Step 2: Semantic Match
            sem = matching.semantic_similarity(resume_text, jd_content)

            # Step 3: Scoring & Verdict
            scored = scorer.compute_final_score(hard, sem)

            # Suggestions
            suggestions = []
            if scored['verdict'] != 'High':
                if scored['missing']:
                    suggestions.append(f"Consider acquiring or highlighting skills: {', '.join(scored['missing'])}")
                suggestions.append("Enhance resume with projects, certifications, and quantified achievements")

            # Save evaluation directly
            conn = sqlite3.connect('data/results.db')
            cur = conn.cursor()
            cur.execute("INSERT INTO evaluations (jd_id, resume_name, score, verdict, missing) VALUES (?, ?, ?, ?, ?)",
                        (jd_id, resume_file.name, scored['score'], scored['verdict'], json.dumps(scored['missing'])))
            conn.commit()
            conn.close()

            # Display results
            st.subheader("Evaluation Results")
            st.metric("Relevance Score", scored['score'])
            st.markdown(f"**Verdict:** <span style='color:{'green' if scored['verdict']=='High' else 'orange' if scored['verdict']=='Medium' else 'red'};'>{scored['verdict']}</span>", unsafe_allow_html=True)
            st.write("Missing Skills/Projects/Certifications:")
            if scored['missing']:
                for item in scored['missing']:
                    st.markdown(f"<span style='color:red; font-weight:bold'>● {item}</span>", unsafe_allow_html=True)
            if suggestions:
                st.write("Suggestions for Improvement:")
                for s in suggestions:
                    st.write(f"- {s}")

# ------------------ Shortlist Dashboard ------------------
if menu == "Shortlist Dashboard":
    st.header("Shortlist Dashboard")
    st.info("Filter resumes by Job Title, Company, Location, and Minimum Score")
    
    conn = sqlite3.connect('data/results.db')
    cur = conn.cursor()
    
    # Ensure tables exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jd_id INTEGER,
            resume_name TEXT,
            score INTEGER,
            verdict TEXT,
            missing TEXT
        )
    """)
    
    # Fetch evaluations
    cur.execute("""
        SELECT e.id, j.title, e.resume_name, e.score, e.verdict, e.missing 
        FROM evaluations e 
        JOIN jds j ON e.jd_id = j.id
    """)
    evals = cur.fetchall()
    conn.close()

    if not evals:
        st.info("No evaluations yet.")
    else:
        df = pd.DataFrame(evals, columns=["ID","JD Title","Resume","Score","Verdict","Missing"])
        df[['Job Title','Company','Location']] = df['JD Title'].str.split('|', expand=True)
        df['Job Title'] = df['Job Title'].str.strip()
        df['Company'] = df['Company'].str.strip()
        df['Location'] = df['Location'].str.strip()
        
        # Filters
        st.sidebar.subheader("Filters")
        job_filter = st.sidebar.multiselect("Job Title", options=df['Job Title'].unique(), default=df['Job Title'].unique())
        company_filter = st.sidebar.multiselect("Company", options=df['Company'].unique(), default=df['Company'].unique())
        location_filter = st.sidebar.multiselect("Location", options=df['Location'].unique(), default=df['Location'].unique())
        score_filter = st.sidebar.slider("Minimum Score", 0, 100, 0)
        
        df_filtered = df[
            (df['Job Title'].isin(job_filter)) &
            (df['Company'].isin(company_filter)) &
            (df['Location'].isin(location_filter)) &
            (df['Score'] >= score_filter)
        ]

        st.write(f"Total Evaluations: {len(df_filtered)}")
        for idx, row in df_filtered.iterrows():
            st.markdown(f"### Resume: {row['Resume']}")
            st.markdown(f"**Job:** {row['Job Title']} | **Company:** {row['Company']} | **Location:** {row['Location']}")
            st.markdown(f"**Score:** {row['Score']} | **Verdict:** "
                        f"<span style='color:{'green' if row['Verdict']=='High' else 'orange' if row['Verdict']=='Medium' else 'red'};'>{row['Verdict']}</span>", 
                        unsafe_allow_html=True)
            if row['Missing']:
                missing = json.loads(row['Missing'])
                st.markdown("**Missing Skills/Projects/Certifications:**")
                for item in missing:
                    st.markdown(f"<span style='color:red; font-weight:bold'>● {item}</span>", unsafe_allow_html=True)
            st.markdown("---")

# ------------------ Help / Samples ------------------
if menu == "Help / Samples":
    st.header("Help & Sample Data")
    st.write("Sample data included in `data/sample/`. Upload JD, then student can upload resumes to evaluate.")
    sample_jd_path = Path('data/sample/job_description.txt')
    sample_resume_path = Path('data/sample/sample_resume.txt')
    if sample_jd_path.exists():
        st.subheader("Sample JD")
        st.code(sample_jd_path.read_text())
    if sample_resume_path.exists():
        st.subheader("Sample Resume")
        st.code(sample_resume_path.read_text())
