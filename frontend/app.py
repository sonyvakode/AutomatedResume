
import streamlit as st
import requests, os, io, pandas as pd, json
from pathlib import Path

API_BASE = st.secrets.get('API_BASE', 'http://localhost:8000')

st.set_page_config(page_title="Resume Relevance Dashboard", layout="wide")

def local_text(path):
    try:
        return open(path,'r',encoding='utf-8').read()
    except:
        return ''

st.title("📄 Automated Resume Relevance Check — Dashboard")
menu = st.sidebar.selectbox("Menu", ["Upload Job Description", "Evaluate Resume", "Shortlist Dashboard", "Help / Samples"])

if menu == "Upload Job Description":
    st.header("Upload Job Description")
    with st.form("jd_form"):
        title = st.text_input("Job title / Role", value="Data Scientist - NLP")
        jd_txt = st.text_area("Paste JD text (or upload below)", height=200)
        jd_file = st.file_uploader("Or upload a .txt/.md JD file", type=['txt','md'])
        submitted = st.form_submit_button("Upload JD")
        if submitted:
            if jd_file is not None:
                jd_txt = jd_file.getvalue().decode('utf-8', errors='ignore')
            if not jd_txt.strip():
                st.error("Provide JD text or file.")
            else:
                files = {'jd_file': ('jd.txt', jd_txt)}
                data = {'title': title}
                resp = requests.post(f"{API_BASE}/upload_jd/", data=data, files=files)
                st.success("Uploaded JD: " + str(resp.json()))

if menu == "Evaluate Resume":
    st.header("Evaluate Resume")
    jd_id = st.number_input("JD id (from upload response)", min_value=1, value=1)
    uploaded = st.file_uploader("Upload resume (PDF/DOCX/TXT)", type=['pdf','docx','txt'])
    if st.button("Evaluate"):
        if uploaded is None:
            st.error("Upload a resume first.")
        else:
            files = {'resume_file': (uploaded.name, uploaded.getvalue())}
            data = {'jd_id': str(jd_id)}
            with st.spinner("Evaluating..."):
                resp = requests.post(f"{API_BASE}/evaluate/", data=data, files=files)
            res = resp.json()
            st.subheader("Result")
            st.metric("Relevance Score", res.get('score', 0))
            st.write("Verdict:", res.get('verdict'))
            st.write("Missing items:", res.get('missing', []))
            st.write("Raw details:")
            st.json(res)

if menu == "Shortlist Dashboard":
    st.header("Shortlist Dashboard")
    st.info("This demo stores results in a local SQLite DB. Use backend/src/db.py to explore.")
    # For demo, show sample data from data/sample
    sample_jd = local_text('data/sample/job_description.txt')
    st.subheader("Sample JD")
    st.code(sample_jd)
    st.subheader("Sample Resume")
    st.code(local_text('data/sample/sample_resume.txt'))

if menu == "Help / Samples":
    st.header("Help & Samples")
    st.write("Sample data included in `data/sample/`. README has run steps.")
