import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import time

# ==================== Page Config ====================
st.set_page_config(
    page_title="ARRCS - AI-Powered Resume Screening",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

DB_PATH = "resume_system.db"

# ==================== Sidebar Menu ====================
menu = st.sidebar.selectbox(
    "Menu",
    ["Placement Team: Upload JD", "Students: Upload Resume", "Shortlist Dashboard", "Help / Samples"]
)

# ==================== Placement Team: Upload JD ====================
if menu == "Placement Team: Upload JD":
    st.header("📌 Placement Team: Upload Job Description")
    st.info("Upload job descriptions with role, company, and location.")

    role = st.text_input("Job Role")
    company = st.text_input("Company")
    location = st.text_input("Location")
    jd_text = st.text_area("Paste Job Description Here")

    if st.button("Save Job Description"):
        if role and company and location and jd_text:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS jds (id INTEGER PRIMARY KEY, title TEXT, description TEXT)")
            jd_title = f"{role} | {company} | {location}"
            cur.execute("INSERT INTO jds (title, description) VALUES (?, ?)", (jd_title, jd_text))
            conn.commit()
            conn.close()
            st.success("✅ Job description saved successfully!")
        else:
            st.error("Please fill in all fields.")

# ==================== Students: Upload Resume ====================
elif menu == "Students: Upload Resume":
    st.header("📂 Students: Upload Your Resume")
    st.info("Upload your resume to be matched with job descriptions.")

    name = st.text_input("Your Name")
    resume_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    if st.button("Submit Resume"):
        if name and resume_file:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS resumes (id INTEGER PRIMARY KEY, name TEXT, file_name TEXT)")
            cur.execute("INSERT INTO resumes (name, file_name) VALUES (?, ?)", (name, resume_file.name))
            conn.commit()
            conn.close()
            st.success("✅ Resume uploaded successfully!")
        else:
            st.error("Please provide your name and upload a resume.")

# ==================== Shortlist Dashboard ====================
elif menu == "Shortlist Dashboard":
    st.header("📊 Placement Team Dashboard")
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

        # Add Shortlisted column
        df['Shortlisted'] = df['Verdict'].apply(lambda v: "YES" if v in ["High", "Medium"] else "NO")

        # ===== Filters (Top Bar) =====
        col1, col2, col3 = st.columns(3)
        with col1:
            role_filter = st.selectbox("Filter by Role", options=["All"] + sorted(df['Job Title'].unique().tolist()))
        with col2:
            loc_filter = st.selectbox("Filter by Location", options=["All"] + sorted(df['Location'].unique().tolist()))
        with col3:
            shortlist_filter = st.selectbox("Shortlisted Only?", options=["All", "YES", "NO"])

        # Apply filters
        if role_filter != "All":
            df = df[df['Job Title'] == role_filter]
        if loc_filter != "All":
            df = df[df['Location'] == loc_filter]
        if shortlist_filter != "All":
            df = df[df['Shortlisted'] == shortlist_filter]

        # ===== Custom CSS Styling for Table =====
        st.markdown("""
        <style>
        .stDataFrame table {
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        .stDataFrame th {
            background-color: #4CAF50 !important;
            color: white !important;
            font-weight: bold !important;
        }
        .stDataFrame td {
            border-bottom: 1px solid #ddd;
        }
        </style>
        """, unsafe_allow_html=True)

        # ===== Display Table =====
        st.dataframe(
            df[['Resume','Job Title','Company','Location','Score','Verdict','Shortlisted','Missing']],
            use_container_width=True
        )

# ==================== Help / Samples ====================
elif menu == "Help / Samples":
    st.header("ℹ️ Help & Sample Data")
    st.write("This tool helps placement teams shortlist resumes against job descriptions using AI.")
    st.write("- Upload JDs first under Placement Team section.")
    st.write("- Students upload resumes under Student section.")
    st.write("- Shortlist Dashboard shows matches with filters.")
