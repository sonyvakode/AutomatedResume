
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil, os
from src.pipeline import evaluate_resume_from_files, save_jd
from fastapi.responses import JSONResponse

app = FastAPI(title="Resume Relevance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

os.makedirs('uploads', exist_ok=True)

@app.post("/upload_jd/")
async def upload_jd(title: str = Form(...), jd_file: UploadFile = File(...)):
    content = (await jd_file.read()).decode(errors='ignore')
    jd_id = save_jd(title, content)
    return JSONResponse({'status':'ok','jd_id': jd_id})

@app.post("/evaluate/")
async def evaluate(resume_file: UploadFile = File(...), jd_id: int = Form(...)):
    tmp_path = os.path.join('uploads', resume_file.filename)
    with open(tmp_path, 'wb') as f:
        f.write(await resume_file.read())
    result = evaluate_resume_from_files(tmp_path, jd_id)
    return JSONResponse(result)
