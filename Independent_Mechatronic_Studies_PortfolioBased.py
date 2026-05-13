import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="AIMecha Study OS", layout="wide")

DB_NAME = "study_tracker.db"
UPLOAD_FOLDER = "uploads"
LOGO_PATH = "AIMECHA.png"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------------
# LOGO (SAFE LOAD)
# -----------------------------
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, width=180)
else:
    st.sidebar.warning("Logo not found: AIMECHA.png")

st.title("⚙️ AIMecha Study OS — Mechatronics AI Tracker")

# -----------------------------
# DB CONNECTION (SAFE)
# -----------------------------
@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

conn = get_conn()

# -----------------------------
# INIT DATABASE
# -----------------------------
def init_db():
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        course_name TEXT,
        completed INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        note TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        entry TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        course_name TEXT,
        file_name TEXT,
        file_path TEXT,
        created_at TEXT
    )
    """)

    conn.commit()

init_db()

# -----------------------------
# COURSES
# -----------------------------
def get_courses():
    return pd.read_sql_query("SELECT * FROM courses", conn)

def add_course(cat, name):
    conn.execute(
        "INSERT INTO courses (category, course_name) VALUES (?,?)",
        (cat, name)
    )
    conn.commit()

def update_course(cid, done):
    conn.execute(
        "UPDATE courses SET completed=? WHERE id=?",
        (done, cid)
    )
    conn.commit()

# -----------------------------
# NOTES
# -----------------------------
def add_note(course_id, note):
    conn.execute(
        "INSERT INTO notes (course_id, note, created_at) VALUES (?,?,?)",
        (course_id, note, datetime.now().isoformat())
    )
    conn.commit()

def get_notes(course_id):
    return pd.read_sql_query(
        "SELECT * FROM notes WHERE course_id=? ORDER BY created_at DESC",
        conn,
        params=(course_id,)
    )

def delete_note(note_id):
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()

# -----------------------------
# JOURNAL
# -----------------------------
def add_journal(title, entry):
    conn.execute(
        "INSERT INTO journal (title, entry, created_at) VALUES (?,?,?)",
        (title, entry, datetime.now().isoformat())
    )
    conn.commit()

def get_journal():
    return pd.read_sql_query(
        "SELECT * FROM journal ORDER BY created_at DESC",
        conn
    )

def delete_journal(jid):
    conn.execute("DELETE FROM journal WHERE id=?", (jid,))
    conn.commit()

# -----------------------------
# EXERCISES
# -----------------------------
def save_exercise(course_id, course_name, file):
    path = os.path.join(UPLOAD_FOLDER, file.name)

    with open(path, "wb") as f:
        f.write(file.getbuffer())

    conn.execute("""
        INSERT INTO exercises (course_id, course_name, file_name, file_path, created_at)
        VALUES (?,?,?,?,?)
    """, (course_id, course_name, file.name, path, datetime.now().isoformat()))

    conn.commit()

def get_exercises():
    return pd.read_sql_query("SELECT * FROM exercises ORDER BY created_at DESC", conn)

def delete_exercise(ex_id, path):
    conn.execute("DELETE FROM exercises WHERE id=?", (ex_id,))
    if os.path.exists(path):
        os.remove(path)
    conn.commit()

# -----------------------------
# PDF EXPORT (LINKEDIN)
# -----------------------------
def generate_pdf():
    file_name = "AIMecha_Portfolio.pdf"
    doc = SimpleDocTemplate(file_name)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("AIMecha Engineering Portfolio", styles["Title"]))
    content.append(Spacer(1, 12))

    courses = get_courses()

    content.append(Paragraph("Courses Progress", styles["Heading2"]))
    for _, c in courses.iterrows():
        content.append(Paragraph(
            f"{c['course_name']} ({c['category']}) - Completed: {c['completed']}",
            styles["Normal"]
        ))

    content.append(Spacer(1, 12))

    notes = pd.read_sql_query("SELECT * FROM notes", conn)

    content.append(Paragraph("Notes Summary", styles["Heading2"]))
    for _, n in notes.iterrows():
        content.append(Paragraph(n["note"][:200], styles["Normal"]))

    doc.build(content)
    return file_name

# -----------------------------
# NAVIGATION
# -----------------------------
menu = st.sidebar.radio(
    "Navigation",
    ["Courses", "Add Course", "Journal", "Exercises", "Analytics", "Export PDF"]
)

# =========================================================
# COURSES
# =========================================================
if menu == "Courses":
    st.subheader("📚 Courses + Notes System")

    df = get_courses()

    for _, row in df.iterrows():

        st.markdown("---")

        st.write(f"## {row['course_name']} ({row['category']})")

        done = st.checkbox(
            "Completed",
            value=bool(row["completed"]),
            key=f"c_{row['id']}"
        )
        update_course(row["id"], int(done))

        note = st.text_area("Add note", key=f"n_{row['id']}")

        if st.button("Save Note", key=f"s_{row['id']}"):
            if note.strip():
                add_note(row["id"], note)
                st.rerun()

        notes = get_notes(row["id"])

        for _, n in notes.iterrows():
            col1, col2 = st.columns([6,1])

            with col1:
                st.write(n["note"])
                st.caption(n["created_at"])

            with col2:
                if st.button("🗑", key=f"dn_{n['id']}"):
                    delete_note(n["id"])
                    st.rerun()

# =========================================================
# ADD COURSE
# =========================================================
elif menu == "Add Course":
    st.subheader("➕ Add Course")

    cat = st.selectbox("Category", ["AI","Robotics","Programming","Math","Control Systems"])
    name = st.text_input("Course Name")

    if st.button("Add"):
        add_course(cat, name)
        st.success("Added")
        st.rerun()

# =========================================================
# JOURNAL
# =========================================================
elif menu == "Journal":
    st.subheader("🧠 Engineering Journal")

    title = st.text_input("Title")
    entry = st.text_area("Write journal entry", height=150)

    if st.button("Save Journal"):
        add_journal(title, entry)
        st.rerun()

    df = get_journal()

    for _, j in df.iterrows():
        col1, col2 = st.columns([6,1])

        with col1:
            st.write(f"### {j['title']}")
            st.write(j["entry"])
            st.caption(j["created_at"])

        with col2:
            if st.button("🗑", key=f"j_{j['id']}"):
                delete_journal(j["id"])
                st.rerun()

# =========================================================
# EXERCISES
# =========================================================
elif menu == "Exercises":
    st.subheader("📤 Upload Exercises / Assignments")

    courses = get_courses()

    if not courses.empty:
        course = st.selectbox("Course", courses["course_name"])
        cid = courses[courses["course_name"] == course]["id"].values[0]

        file = st.file_uploader("Upload file (PDF, image, code)")

        if file and st.button("Save"):
            save_exercise(cid, course, file)
            st.rerun()

    st.divider()

    ex = get_exercises()

    for _, r in ex.iterrows():
        col1, col2 = st.columns([6,1])

        with col1:
            st.write(f"{r['course_name']} - {r['file_name']}")
            with open(r["file_path"], "rb") as f:
                st.download_button("Download", f, file_name=r["file_name"])

        with col2:
            if st.button("🗑", key=f"e_{r['id']}"):
                delete_exercise(r["id"], r["file_path"])
                st.rerun()

# =========================================================
# ANALYTICS
# =========================================================
elif menu == "Analytics":
    st.subheader("📊 Progress Analytics")

    df = get_courses()

    if not df.empty:
        st.bar_chart(df.groupby("category")["completed"].mean() * 100)

# =========================================================
# EXPORT PDF
# =========================================================
elif menu == "Export PDF":
    st.subheader("📄 LinkedIn Portfolio Export")

    if st.button("Generate PDF"):
        file = generate_pdf()
        with open(file, "rb") as f:
            st.download_button("Download Portfolio PDF", f, file_name=file)
