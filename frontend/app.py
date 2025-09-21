import streamlit as st
import os, json, sqlite3
from src import parsers, matching, scorer, db

db.init_db()
st.set_page_config(page_title="Resume Relevance Checker", layout="wide")
st.title("📄 Automated Resume Relevance Checker")

menu = st.sidebar.selectbox("Menu", ["Placement Team: Upload JD", "Students: Upload Resume", "Dashboard"])

# ---------------- Placement Team: JD Upload ----------------
if menu=="Placement Team: Upload JD":
    st.header("Job Requirement Upload - Placement Team")
    with st.form("jd_form"):
        title = st.text_input("Job Title")
        company = st.text_input("Company Name")
        location = st.text_input("Location")
        jd_file = st.file_uploader("Upload Job Description (.txt)", type=['txt'])
        submitted = st.form_submit_button("Save JD")
        if submitted:
            if jd_file is None or not title.strip() or not company.strip() or not location.strip():
                st.error("Please fill all fields and upload JD file")
            else:
                content = jd_file.getvalue().decode('utf-8', errors='ignore')
                jd_id = db.save_jd(f"{title} | {company} | {location}", content)
                st.success(f"JD saved with ID: {jd_id}")

# ---------------- Students: Resume Upload ----------------
if menu=="Students: Upload Resume":
    st.header("Resume Upload - Students")
    jds = db.get_jds()
    jd_dict = {f"{row[1]} (ID:{row[0]})": row[0] for row in jds}
    if not jd_dict:
        st.warning("No Job Requirements found. Please wait for placement team to upload JD.")
    else:
        jd_sel = st.selectbox("Select Job Requirement", list(jd_dict.keys()))
        resume_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=['pdf','docx','txt'])
        if st.button("Evaluate") and resume_file:
            # Save resume temporarily
            os.makedirs("data/resumes", exist_ok=True)
            resume_path = os.path.join("data/resumes", resume_file.name)
            with open(resume_path,'wb') as f:
                f.write(resume_file.getvalue())
            
            # Extract and normalize resume text
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
            
            # Generate suggestions
            suggestions = []
            if scored['verdict'] != 'High':
                if scored['missing']:
                    suggestions.append(f"Consider acquiring or highlighting skills: {', '.join(scored['missing'])}")
                suggestions.append("Enhance resume with projects, certifications, and quantified achievements")
            
            # Save evaluation
            db.save_evaluation(jd_id, resume_file.name, scored['score'], scored['verdict'], scored['missing'])
            
            # Display Results
            st.subheader("Evaluation Results")
            st.metric("Relevance Score", scored['score'])
            st.write("Verdict:", scored['verdict'])
            st.write("Missing Skills/Projects/Certifications:")
            if scored['missing']:
                for item in scored['missing']:
                    st.markdown(f"<span style='color:red; font-weight:bold'>● {item}</span>", unsafe_allow_html=True)
            if suggestions:
                st.write("Suggestions for Improvement:")
                for s in suggestions:
                    st.write(f"- {s}")

# ---------------- Dashboard ----------------
if menu=="Dashboard":
    st.header("Placement Team Dashboard")
    st.info("Search and filter resumes by Job Title, Company, Location, and Minimum Score.")
    evals = db.get_evaluations()
    if not evals:
        st.info("No evaluations yet.")
    else:
        import pandas as pd
        df = pd.DataFrame(evals, columns=["ID","JD Title","Resume","Score","Verdict","Missing"])
        # Split JD Title into components for filtering
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
        
        # Display Data with badges for missing skills
        st.write(f"Total Evaluations: {len(df_filtered)}")
        for idx, row in df_filtered.iterrows():
            st.markdown(f"### Resume: {row['Resume']}")
            st.markdown(f"**Job:** {row['Job Title']} | **Company:** {row['Company']} | **Location:** {row['Location']}")
            st.markdown(f"**Score:** {row['Score']} | **Verdict:** {row['Verdict']}")
            if row['Missing']:
                missing = json.loads(row['Missing'])
                st.markdown("**Missing Skills/Projects/Certifications:**")
                for item in missing:
                    st.markdown(f"<span style='color:red; font-weight:bold'>● {item}</span>", unsafe_allow_html=True)
            st.markdown("---")
