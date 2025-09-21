import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import io, json, sqlite3
from pathlib import Path
import pandas as pd
from src import parsers, matching, scorer

# Create directories if not exist
os.makedirs('data/resumes', exist_ok=True)

# Page config & background styling
st.set_page_config(page_title="Automated Resume Relevance Dashboard", layout="wide")
page_bg = """
<style>
body {background-color: #f0f2f6;}
section.main {background-color: #ffffff; border-radius:15px; padding:20px; box-shadow: 0px 0px 15px rgba(0,0,0,0.1);}
h1,h2,h3{color:#1f77b4;}
</style>
"""
st.markdown(page_bg, unsafe_allow_html=True)
st.title("📄 Automated Resume Relevance Dashboard")

# Sidebar menu
menu = st.sidebar.selectbox(
    "Menu", 
    ["Placement Team: Upload JD", "Students: Upload Resume", "Shortlist Dashboard", "Help / Samples"]
)

DB_PATH = "results.db"

# ------------------- Placement Team JD Upload -------------------
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
                st.error("Provide all details and JD content/file.")
            else:
                jd_full_title = f"{title} | {company} | {location}"
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

# ------------------- Student Resume Upload & Parsing -------------------
if menu == "Students: Upload Resume":
    st.header("Resume Upload (Students)")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS jds (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS evaluations (id INTEGER PRIMARY KEY AUTOINCREMENT, jd_id INTEGER, resume_name TEXT, score INTEGER, verdict TEXT, missing TEXT)")
    cur.execute("SELECT id, title, content FROM jds")
    jds = cur.fetchall()
    conn.close()

    if not jds:
        st.warning("No job requirements available. Please wait for Placement Team to upload JD.")
    else:
        jd_dict = {f"{row[1]} (ID:{row[0]})": (row[0], row[2]) for row in jds}
        jd_sel = st.selectbox("Select Job Requirement", list(jd_dict.keys()))
        resume_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=['pdf','docx','txt'])

        if st.button("Parse & Evaluate") and resume_file:
            resume_path = os.path.join("data/resumes", resume_file.name)
            with open(resume_path,'wb') as f:
                f.write(resume_file.getvalue())
            
            # Resume Parsing
            resume_text = parsers.extract_text(resume_path)
            resume_text = parsers.normalize_text(resume_text)

            # JD Parsing
            jd_id, jd_content = jd_dict[jd_sel]
            jd_parsed = parsers.parse_jd(jd_content)

            st.subheader("Parsed JD Details")
            st.write(f"**Role Title:** {jd_parsed.get('role_title','')}")
            st.write(f"**Must-have Skills:** {', '.join(jd_parsed.get('must_have_skills',[]))}")
            st.write(f"**Good-to-have Skills:** {', '.join(jd_parsed.get('good_to_have_skills',[]))}")
            st.write(f"**Qualifications:** {', '.join(jd_parsed.get('qualifications',[]))}")

            # Hard Match
            hard = matching.hard_match(resume_text, jd_parsed)

            # Semantic Match
            sem = matching.semantic_similarity(resume_text, jd_content)

            # Scoring & Verdict
            scored = scorer.compute_final_score(hard, sem)

            # Suggestions
            suggestions = []
            if scored['verdict'] != 'High':
                if scored['missing']:
                    suggestions.append(f"Missing skills/projects: {', '.join(scored['missing'])}")
                suggestions.append("Add relevant certifications or projects to improve relevance.")

            # Save evaluation
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("INSERT INTO evaluations (jd_id, resume_name, score, verdict, missing) VALUES (?, ?, ?, ?, ?)",
                        (jd_id, resume_file.name, scored['score'], scored['verdict'], json.dumps(scored['missing'])))
            conn.commit()
            conn.close()

            # Display Results
            st.subheader("Evaluation Results")
            st.metric("Relevance Score", scored['score'])
            st.markdown(f"**Verdict:** <span style='color:{'green' if scored['verdict']=='High' else 'orange' if scored['verdict']=='Medium' else 'red'};'>{scored['verdict']}</span>", unsafe_allow_html=True)
            if scored['missing']:
                st.write("Missing Skills/Projects/Certifications:")
                for item in scored['missing']:
                    st.markdown(f"<span style='color:red; font-weight:bold'>● {item}</span>", unsafe_allow_html=True)
            if suggestions:
                st.write("Suggestions for Improvement:")
                for s in suggestions:
                    st.write(f"- {s}")

# ------------------- Shortlist Dashboard -------------------
if menu == "Shortlist Dashboard":
    st.header("Shortlist Dashboard")
    st.info("Filter resumes by Job Title, Company, Location, and Minimum Score")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Ensure tables exist
    cur.execute("CREATE TABLE IF NOT EXISTS jds (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS evaluations (id INTEGER PRIMARY KEY AUTOINCREMENT, jd_id INTEGER, resume_name TEXT, score INTEGER, verdict TEXT, missing TEXT)")
    
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

# ------------------- Help / Samples -------------------
if menu == "Help / Samples":
    st.header("Help & Sample Data")
    st.write("Sample data included in `data/sample/`. Upload JD first, then student resumes to evaluate.")
    sample_jd_path = Path('data/sample/job_description.txt')
    sample_resume_path = Path('data/sample/sample_resume.txt')
    if sample_jd_path.exists():
        st.subheader("Sample JD")
        st.code(sample_jd_path.read_text())
    if sample_resume_path.exists():
        st.subheader("Sample Resume")
        st.code(sample_resume_path.read_text())
