import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "attendiq.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            class_name TEXT DEFAULT '',
            email TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present','Absent','Late','Excused')),
            UNIQUE(student_id, attendance_date),
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            score REAL NOT NULL CHECK(score >= 0),
            max_score REAL NOT NULL CHECK(max_score > 0),
            assessment_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        """)
def add_student(code, name, class_name="", email=""):
    with get_connection() as conn:
        conn.execute("INSERT INTO students(student_code,full_name,class_name,email) VALUES(?,?,?,?)",
                     (code,name,class_name,email))
def delete_student(student_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM students WHERE id=?", (student_id,))
def get_students():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM students ORDER BY full_name").fetchall()]
def save_attendance(attendance_date, entries):
    with get_connection() as conn:
        for student_id, status in entries.items():
            conn.execute("""INSERT INTO attendance(student_id,attendance_date,status) VALUES(?,?,?)
            ON CONFLICT(student_id,attendance_date) DO UPDATE SET status=excluded.status""",
                         (student_id, attendance_date, status))
def get_attendance(attendance_date=None):
    query = """SELECT a.id,a.student_id,a.attendance_date,a.status,s.student_code,s.full_name,s.class_name
               FROM attendance a JOIN students s ON s.id=a.student_id"""
    params = ()
    if attendance_date:
        query += " WHERE a.attendance_date=?"
        params = (attendance_date,)
    query += " ORDER BY a.attendance_date DESC,s.full_name"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]
def save_assessment(student_id, title, score, max_score, assessment_date, notes=""):
    with get_connection() as conn:
        conn.execute("""INSERT INTO assessments(student_id,title,score,max_score,assessment_date,notes)
        VALUES(?,?,?,?,?,?)""", (student_id,title,score,max_score,assessment_date,notes))
def get_assessments():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("""SELECT a.*,s.student_code,s.full_name,s.class_name
        FROM assessments a JOIN students s ON s.id=a.student_id ORDER BY a.assessment_date DESC,a.id DESC""").fetchall()]
def attendance_summary():
    rows = get_attendance()
    if not rows: return pd.DataFrame(columns=["student_code","full_name","class_name","attendance_rate","sessions","present_count","absent_count"])
    df = pd.DataFrame(rows)
    # Excused sessions are omitted from denominator; Present and Late count as attended.
    df["attended"] = df["status"].isin(["Present","Late"])
    df["counted"] = df["status"] != "Excused"
    grouped = df.groupby(["student_code","full_name","class_name"], dropna=False).agg(
        sessions=("counted","sum"), attended=("attended","sum"),
        absent_count=("status",lambda x: int((x=="Absent").sum()))
    ).reset_index()
    grouped["present_count"] = grouped["attended"]
    grouped["attendance_rate"] = grouped.apply(lambda r: round(100*r["attended"]/r["sessions"],1) if r["sessions"] else 0, axis=1)
    return grouped.drop(columns=["attended"])
def performance_summary():
    rows = get_assessments()
    if not rows: return pd.DataFrame(columns=["student_code","average_percent","assessments"])
    df = pd.DataFrame(rows)
    df["percent"] = df["score"] / df["max_score"] * 100
    return df.groupby("student_code").agg(average_percent=("percent","mean"),assessments=("id","count")).reset_index().assign(average_percent=lambda x: x["average_percent"].round(1))
