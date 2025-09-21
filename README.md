
# Automated Resume Relevance Check System (MVP)

## Overview
This project provides an end-to-end MVP for automated resume evaluation:
- FastAPI backend for processing JDs and resumes.
- Streamlit frontend as a realistic dashboard for placement teams and students.
- Hybrid scoring: hard keyword matches + semantic similarity.
- SQLite storage for results.

**Note:** This repository uses local ML libraries (sentence-transformers) for embeddings.
If you cannot download models, the pipeline falls back to TF-IDF based semantic matching.

## What's included
- backend/ (FastAPI)
- frontend/ (Streamlit app)
- src/ (parsing, matching, scoring, db)
- data/sample/ (sample JD and resume text)
- requirements.txt

## Quick start (local)
1. Create a virtualenv:
   ```bash
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   ```
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Start backend (API):
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```
4. Start Streamlit frontend (in a new terminal):
   ```bash
   streamlit run frontend/app.py
   ```
5. Open the Streamlit URL shown in the terminal (works on desktop and mobile).

## Files to check
- `frontend/app.py` — Streamlit UI and dashboard.
- `backend/main.py` — FastAPI endpoints for upload + evaluate.
- `src/` — core logic (parsers, matching, scorer, db).

## Notes & Tips
- If sentence-transformers model download fails due to offline environment, the evaluation will continue using TF-IDF semantic fallback.
- For production, replace local vector store with Pinecone/Chroma and secure your API keys.

Good luck with your submission — this is a complete, runnable MVP.
