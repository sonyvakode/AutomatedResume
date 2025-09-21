
import fitz  # pymupdf
import docx
import os, re

def extract_text_from_pdf(path):
    try:
        doc = fitz.open(path)
        text = []
        for page in doc:
            text.append(page.get_text())
        return "\n".join(text)
    except Exception as e:
        return ""

def extract_text_from_docx(path):
    try:
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return ""

def extract_text(path):
    path = path.lower()
    if path.endswith('.pdf'):
        return extract_text_from_pdf(path)
    if path.endswith('.docx'):
        return extract_text_from_docx(path)
    try:
        return open(path,'r',encoding='utf-8').read()
    except:
        return ""

def normalize_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_jd(text):
    # Very light JD parser: tries to extract Role, Must-have, Good-to-have lists
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    role = lines[0] if lines else "Unknown Role"
    must, good = [], []
    current = None
    for l in lines:
        low = l.lower()
        if 'must' in low:
            current = 'must'
            continue
        if 'good' in low or 'nice' in low:
            current = 'good'
            continue
        if l.startswith('-') or l.startswith('*'):
            item = l.lstrip('-* ').strip()
            if current == 'must':
                must.append(item)
            elif current == 'good':
                good.append(item)
    return {'role': role, 'must': must, 'good': good}
