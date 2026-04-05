import os
import sqlite3
import json
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============ CONFIGURATION ============
DB_NAME = "studybuddy.db"

# ============ DATABASE SETUP ============
def init_db():
    """Initialize SQLite database with role-based schema"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Users table (role-based access)
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT CHECK(role IN ('teacher', 'student')) NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Themes table (quiz categories)
    cursor.execute("""CREATE TABLE IF NOT EXISTS themes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    )""")
    
    # Questions table (pre-defined quiz items)
    cursor.execute("""CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        theme_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_answer TEXT CHECK(correct_answer IN ('A','B','C','D')) NOT NULL,
        explanation TEXT,
        created_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (theme_id) REFERENCES themes(id),
        FOREIGN KEY (created_by) REFERENCES users(id)
    )""")
    
    # Quiz attempts table (student progress)
    cursor.execute("""CREATE TABLE IF NOT EXISTS quiz_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        theme_id INTEGER NOT NULL,
        question_ids TEXT NOT NULL,
        answers TEXT,
        score INTEGER,
        total_questions INTEGER DEFAULT 5,
        completed_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (theme_id) REFERENCES themes(id)
    )""")
    
    # ============ INSERT DEMO DATA (ONLY IF NOT EXISTS) ============
    
    # Insert demo users (if not exist)
    demo_users = [
        ('teacher1', 'demo123', 'teacher'),
        ('student1', 'demo123', 'student'),
        ('student2', 'demo123', 'student')
    ]
    for username, password, role in demo_users:
        cursor.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password, role)
        )
    
    # Insert demo themes (if not exist)
    demo_themes = [
        ('Chemistry Basics', 'Fundamental chemistry concepts', 1),
        ('World Capitals', 'Geography: country capitals', 1),
        ('Computer Science', 'Basic CS concepts', 1),
        ('Biology 101', 'Introduction to biology', 1)
    ]
    for name, desc, creator in demo_themes:
        cursor.execute(
            "INSERT OR IGNORE INTO themes (name, description, created_by) VALUES (?, ?, ?)",
            (name, desc, creator)
        )
    
    # ============ KEY FIX: Check if questions already exist ============
    cursor.execute("SELECT COUNT(*) FROM questions")
    question_count = cursor.fetchone()[0]
    
    # Only insert demo questions if table is empty (prevents duplicates on restart)
    if question_count == 0:
        demo_questions = [
            # Chemistry (theme_id=1)
            (1, 'What is the chemical formula for water?', 'H2O', 'CO2', 'NaCl', 'O2', 'A', 'Water consists of two hydrogen atoms bonded to one oxygen atom.'),
            (1, 'What is the pH of pure water?', '5', '7', '9', '14', 'B', 'Pure water has a neutral pH of 7 at 25°C.'),
            (1, 'Which element has the symbol O?', 'Gold', 'Oxygen', 'Osmium', 'Oganesson', 'B', 'O is the chemical symbol for Oxygen, atomic number 8.'),
            (1, 'What is the smallest unit of an element?', 'Atom', 'Molecule', 'Cell', 'Proton', 'A', 'An atom is the smallest unit that retains the properties of an element.'),
            (1, 'What type of bond holds water molecules together?', 'Ionic', 'Covalent', 'Hydrogen', 'Metallic', 'C', 'Hydrogen bonds form between water molecules, giving water unique properties.'),
            (1, 'What is the atomic number of Carbon?', '6', '12', '8', '14', 'A', 'Carbon has 6 protons, giving it atomic number 6.'),
            (1, 'Which gas is most abundant in Earth atmosphere?', 'Oxygen', 'Nitrogen', 'Carbon Dioxide', 'Argon', 'B', 'Nitrogen makes up about 78% of Earth atmosphere.'),
            
            # World Capitals (theme_id=2)
            (2, 'What is the capital of France?', 'London', 'Paris', 'Berlin', 'Madrid', 'B', 'Paris is the capital and largest city of France.'),
            (2, 'What is the capital of Japan?', 'Seoul', 'Beijing', 'Tokyo', 'Bangkok', 'C', 'Tokyo is the capital of Japan.'),
            (2, 'What is the capital of Germany?', 'Munich', 'Hamburg', 'Berlin', 'Frankfurt', 'C', 'Berlin is the capital of Germany.'),
            (2, 'What is the capital of Italy?', 'Venice', 'Rome', 'Milan', 'Naples', 'B', 'Rome is the capital of Italy.'),
            (2, 'What is the capital of Spain?', 'Barcelona', 'Madrid', 'Seville', 'Valencia', 'B', 'Madrid is the capital of Spain.'),
            
            # Computer Science (theme_id=3)
            (3, 'What does CPU stand for?', 'Central Process Unit', 'Computer Personal Unit', 'Central Processing Unit', 'Central Processor Utility', 'C', 'CPU is the primary component that executes program instructions.'),
            (3, 'What is the binary number system base?', '2', '8', '10', '16', 'A', 'Binary uses base-2 with digits 0 and 1.'),
            (3, 'Which language is used for web pages?', 'Python', 'Java', 'HTML', 'C++', 'C', 'HTML (HyperText Markup Language) structures web pages.'),
            (3, 'What does RAM stand for?', 'Read Access Memory', 'Random Access Memory', 'Run All Memory', 'Rapid Application Memory', 'B', 'RAM allows data to be read and written in any order.'),
            (3, 'What is 1 byte equal to?', '4 bits', '8 bits', '16 bits', '32 bits', 'B', '1 byte = 8 bits, the basic unit of digital information.'),
            
            # Biology 101 (theme_id=4) - EXACTLY 4 questions for demo
            (4, 'What is the powerhouse of the cell?', 'Nucleus', 'Mitochondria', 'Ribosome', 'Cytoplasm', 'B', 'Mitochondria produce ATP, the energy currency of the cell, through cellular respiration.'),
            (4, 'What is the basic unit of life?', 'Cell', 'Tissue', 'Organ', 'Organism', 'A', 'The cell is the smallest structural and functional unit of living organisms.'),
            (4, 'What process do plants use to make food?', 'Respiration', 'Photosynthesis', 'Fermentation', 'Digestion', 'B', 'Photosynthesis converts light energy into chemical energy (glucose) using CO2 and water.'),
            (4, 'What molecule carries genetic information?', 'Protein', 'DNA', 'RNA', 'Lipid', 'B', 'DNA (deoxyribonucleic acid) stores and transmits genetic information in all living organisms.'),
        ]
        
        for q in demo_questions:
            cursor.execute("""INSERT INTO questions 
                (theme_id, question_text, option_a, option_b, option_c, option_d, correct_answer, explanation, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""", q)
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DB_NAME} ({question_count} existing questions)")

# Initialize database on startup
init_db()

# ============ FASTAPI APP ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    print("🚀 Starting StudyBuddy Quiz Manager...")
    print(f"   Web: http://localhost:8000")
    print(f"   Database: {DB_NAME}")
    print(f"   Demo accounts: teacher1/demo123, student1/demo123")
    yield
    print("🛑 StudyBuddy stopped")

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ AUTH ENDPOINTS ============
@app.post("/api/login")
async def login(req: Request):
    """Simple login (demo: plaintext password)"""
    data = await req.json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    conn = sqlite3.connect(DB_NAME)
    user = conn.execute(
        "SELECT id, username, role FROM users WHERE username = ? AND password_hash = ?",
        (username, password)
    ).fetchone()
    conn.close()
    
    if user:
        return {
            "status": "success",
            "user": {
                "id": user[0],
                "username": user[1],
                "role": user[2]
            }
        }
    raise HTTPException(status_code=401, detail="Invalid username or password")

@app.get("/api/themes")
async def get_themes():
    """Get all available themes (public)"""
    conn = sqlite3.connect(DB_NAME)
    themes = conn.execute(
        "SELECT id, name, description FROM themes ORDER BY name"
    ).fetchall()
    conn.close()
    return [{"id": t[0], "name": t[1], "description": t[2]} for t in themes]

# ============ TEACHER ENDPOINTS ============
@app.get("/api/teacher/questions")
async def teacher_get_questions(theme_id: Optional[int] = None):
    """Teacher: Get all questions (optionally filtered by theme)"""
    conn = sqlite3.connect(DB_NAME)
    if theme_id:
        questions = conn.execute("""
            SELECT q.id, q.question_text, q.option_a, q.option_b, q.option_c, q.option_d, 
                   q.correct_answer, q.explanation, t.name as theme_name
            FROM questions q
            JOIN themes t ON q.theme_id = t.id
            WHERE q.theme_id = ?
            ORDER BY q.id DESC
        """, (theme_id,)).fetchall()
    else:
        questions = conn.execute("""
            SELECT q.id, q.question_text, q.option_a, q.option_b, q.option_c, q.option_d, 
                   q.correct_answer, q.explanation, t.name as theme_name
            FROM questions q
            JOIN themes t ON q.theme_id = t.id
            ORDER BY q.id DESC
        """).fetchall()
    conn.close()
    
    return [{
        "id": q[0],
        "question": q[1],
        "options": [q[2], q[3], q[4], q[5]],
        "correct_answer": q[6],
        "explanation": q[7],
        "theme_name": q[8]
    } for q in questions]

@app.post("/api/teacher/questions")
async def teacher_add_question(req: Request):
    """Teacher: Add a new question to a theme"""
    data = await req.json()
    
    required = ["theme_id", "question", "options", "answer", "explanation"]
    if not all(k in data for k in required):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    if len(data["options"]) != 4:
        raise HTTPException(status_code=400, detail="Must provide exactly 4 options")
    
    if data["answer"] not in ["A", "B", "C", "D"]:
        raise HTTPException(status_code=400, detail="Answer must be A, B, C, or D")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO questions 
        (theme_id, question_text, option_a, option_b, option_c, option_d, correct_answer, explanation, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data["theme_id"], data["question"], data["options"][0], data["options"][1],
         data["options"][2], data["options"][3], data["answer"], data["explanation"], data.get("created_by", 1)))
    conn.commit()
    question_id = cursor.lastrowid
    conn.close()
    
    return {"status": "created", "question_id": question_id}

@app.delete("/api/teacher/questions/{question_id}")
async def teacher_delete_question(question_id: int):
    """Teacher: Delete a question"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@app.post("/api/teacher/themes")
async def teacher_add_theme(req: Request):
    """Teacher: Add a new theme"""
    data = await req.json()
    
    if not data.get("name") or not data.get("description"):
        raise HTTPException(status_code=400, detail="Name and description required")
    
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO themes (name, description, created_by) VALUES (?, ?, ?)",
            (data["name"], data["description"], data.get("created_by", 1))
        )
        conn.commit()
        theme_id = cursor.lastrowid
        conn.close()
        return {"status": "created", "theme_id": theme_id}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Theme name already exists")

@app.get("/api/teacher/history")
async def teacher_get_all_history():
    """Teacher: View all student quiz attempts"""
    conn = sqlite3.connect(DB_NAME)
    rows = conn.execute("""
        SELECT qa.id, u.username, t.name as theme, qa.score, qa.total_questions, qa.completed_at 
        FROM quiz_attempts qa
        JOIN users u ON qa.user_id = u.id
        JOIN themes t ON qa.theme_id = t.id
        WHERE u.role = 'student'
        ORDER BY qa.completed_at DESC
        LIMIT 50
    """).fetchall()
    conn.close()
    
    return [{
        "id": r[0],
        "student": r[1],
        "theme": r[2],
        "score": f"{r[3]}/{r[4]}",
        "percentage": round((r[3] / r[4]) * 100) if r[4] > 0 else 0,
        "date": r[5]
    } for r in rows]

# ============ STUDENT ENDPOINTS ============
@app.post("/api/student/generate")
async def student_generate_quiz(req: Request):
    """Student: Generate 5 random questions from a theme (without answers)"""
    data = await req.json()
    theme_id = data.get("theme_id")
    
    if not theme_id:
        raise HTTPException(status_code=400, detail="theme_id required")
    
    conn = sqlite3.connect(DB_NAME)
    
    # Check theme exists
    theme = conn.execute("SELECT id, name FROM themes WHERE id = ?", (theme_id,)).fetchone()
    if not theme:
        conn.close()
        raise HTTPException(status_code=404, detail="Theme not found")
    
    # Count questions in theme
    count = conn.execute("SELECT COUNT(*) FROM questions WHERE theme_id = ?", (theme_id,)).fetchone()[0]
    if count < 5:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Theme has only {count} questions (need at least 5)")
    
    # Get 5 random questions, EXCLUDE correct_answer from response
    questions = conn.execute("""
        SELECT id, question_text, option_a, option_b, option_c, option_d, explanation 
        FROM questions WHERE theme_id = ? ORDER BY RANDOM() LIMIT 5
    """, (theme_id,)).fetchall()
    conn.close()
    
    # Format for frontend (no correct_answer exposed)
    quiz = []
    for q in questions:
        quiz.append({
            "id": q[0],
            "question": q[1],
            "options": [q[2], q[3], q[4], q[5]],
            "explanation": q[6] or "Review your notes for more details."
        })
    
    return {
        "questions": quiz,
        "theme_id": theme_id,
        "theme_name": theme[1]
    }

@app.post("/api/student/submit")
async def student_submit_quiz(req: Request):
    """Student: Submit answers and get scored"""
    data = await req.json()
    
    required = ["user_id", "theme_id", "question_ids", "answers"]
    if not all(k in data for k in required):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    user_id = data["user_id"]
    theme_id = data["theme_id"]
    question_ids = data["question_ids"]
    answers = data["answers"]
    
    if len(question_ids) != len(answers):
        raise HTTPException(status_code=400, detail="Answers count must match questions count")
    
    # Fetch correct answers from DB
    conn = sqlite3.connect(DB_NAME)
    placeholders = ",".join("?" * len(question_ids))
    correct = conn.execute(
        f"SELECT id, correct_answer FROM questions WHERE id IN ({placeholders})",
        question_ids
    ).fetchall()
    correct_map = {qid: ans for qid, ans in correct}
    
    # Grade
    score = sum(1 for qid, ans in zip(question_ids, answers) if correct_map.get(qid) == ans)
    
    # Save attempt
    conn.execute("""INSERT INTO quiz_attempts 
        (user_id, theme_id, question_ids, answers, score, total_questions, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, theme_id, json.dumps(question_ids), json.dumps(answers),
         score, len(question_ids), datetime.now().isoformat()))
    conn.commit()
    
    # Return results with explanations
    results = []
    for qid, user_ans in zip(question_ids, answers):
        q_data = conn.execute(
            "SELECT question_text, option_a, option_b, option_c, option_d, correct_answer, explanation FROM questions WHERE id = ?",
            (qid,)
        ).fetchone()
        if q_data:
            results.append({
                "question_id": qid,
                "question": q_data[0],
                "options": [q_data[1], q_data[2], q_data[3], q_data[4]],
                "user_answer": user_ans,
                "correct_answer": q_data[5],
                "is_correct": user_ans == q_data[5],
                "explanation": q_data[6] or "Review your notes for more details."
            })
    conn.close()
    
    return {
        "score": score,
        "total": len(question_ids),
        "percentage": round((score / len(question_ids)) * 100),
        "results": results
    }

@app.get("/api/student/history")
async def student_get_history(user_id: Optional[int] = None):
    """Student: Get quiz history (all if no user_id, filtered if provided)"""
    conn = sqlite3.connect(DB_NAME)
    if user_id:
        rows = conn.execute("""
            SELECT qa.id, t.name, qa.score, qa.total_questions, qa.completed_at 
            FROM quiz_attempts qa
            JOIN themes t ON qa.theme_id = t.id
            WHERE qa.user_id = ? ORDER BY qa.completed_at DESC LIMIT 20
        """, (user_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT qa.id, t.name, qa.score, qa.total_questions, qa.completed_at 
            FROM quiz_attempts qa
            JOIN themes t ON qa.theme_id = t.id
            ORDER BY qa.completed_at DESC LIMIT 20
        """).fetchall()
    conn.close()
    
    return [{
        "id": r[0],
        "theme": r[1],
        "score": f"{r[2]}/{r[3]}",
        "percentage": round((r[2] / r[3]) * 100) if r[3] > 0 else 0,
        "date": r[4]
    } for r in rows]

# ============ FRONTEND ============
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the web frontend"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "frontend", "index.html")
    return FileResponse(html_path)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    conn = sqlite3.connect(DB_NAME)
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    themes = conn.execute("SELECT COUNT(*) FROM themes").fetchone()[0]
    questions = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    conn.close()
    
    return {
        "status": "ok",
        "database": "connected",
        "users": users,
        "themes": themes,
        "questions": questions
    }

# ============ RUN COMMAND ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)