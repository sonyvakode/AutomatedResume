
import sqlite3, os
DB_PATH = 'data/results.db'
def init_db():
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS jds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jd_id INTEGER,
        resume_path TEXT,
        score REAL,
        verdict TEXT,
        missing TEXT
    )
    ''')
    conn.commit()
    conn.close()

def save_jd(title, content):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('INSERT INTO jds (title,content) VALUES (?,?)', (title, content))
    conn.commit()
    id = cur.lastrowid
    conn.close()
    return id

def save_evaluation(jd_id, resume_path, score, verdict, missing):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('INSERT INTO evaluations (jd_id, resume_path, score, verdict, missing) VALUES (?,?,?,?,?)',
                (jd_id, resume_path, score, verdict, json_list(missing)))
    conn.commit()
    conn.close()

def json_list(obj):
    import json
    return json.dumps(obj)
