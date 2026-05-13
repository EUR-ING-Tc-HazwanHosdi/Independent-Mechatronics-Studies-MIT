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
st.set_page_config(page_title="AIMecha OS", layout="wide")

DB_NAME = "study_tracker.db"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.title("⚙️ AIMecha Study OS — AI Mechatronics Tracker")

# -----------------------------
# SAFE DATABASE CONNECTION (FIXED)
# -----------------------------
@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn

conn = get_conn()

# -----------------------------
# INIT DATABASE (SAFE)
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
    c = conn.cursor()
    c.execute("INSERT INTO courses (category, course_name) VALUES (?,?)", (cat, name))
    conn.commit()

def update_course(cid, done):
    c = conn.cursor()
    c.execute("UPDATE courses SET completed=? WHERE id=?", (done, cid))
    conn.commit()

# -----------------------------
# NOTES
# -----------------------------
def add_note(course_id, note):
    c = conn.cursor()
    c.execute(
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
    c = conn.cursor()
    c.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()

# -----------------------------
# JOURNAL
# -----------------------------
def add_journal(title, entry):
    c = conn.cursor()
    c.execute(
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
    c = conn.cursor()
    c.execute("DELETE FROM journal WHERE id=?", (jid,))
    conn.commit()

# -----------------------------
# EXERCISES
# -----------------------------
elif menu == "Exercises":
    st.subheader("📤 Upload Exercises")

    courses = get_courses()

    if not courses.empty:
        course = st.selectbox("Course", courses["course_name"])
        cid = courses[courses["course_name"] == course]["id"].values[0]

        file = st.file_uploader("Upload PDF / file")

        if file and st.button("Save"):
            save_exercise(cid, course, file)
            st.success("Uploaded")
            st.rerun()

    st.divider()

    st.write("## 📁 Uploaded Exercises")

    ex = get_exercises()

    if ex.empty:
        st.info("No exercises uploaded yet.")
    else:
        for _, r in ex.iterrows():

            col1, col2 = st.columns([6,1])

            with col1:
                st.write(f"📘 **{r['course_name']}**")
                st.write(r["file_name"])
                st.caption(r["created_at"])

                with open(r["file_path"], "rb") as f:
                    st.download_button(
                        "⬇ Download",
                        f,
                        file_name=r["file_name"],
                        key=f"dl_{r['id']}"
                    )

            with col2:
                if st.button("🗑 Delete", key=f"del_ex_{r['id']}"):
                    delete_exercise(r["id"], r["file_path"])
                    st.success("Deleted")
                    st.rerun()

# -----------------------------
# PDF GENERATION (LINKEDIN READY)
# -----------------------------
def generate_pdf():
    file_name = "AIMecha_Portfolio_Report.pdf"
    doc = SimpleDocTemplate(file_name)

    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("AIMecha Learning Portfolio Report", styles["Title"]))
    content.append(Spacer(1, 12))

    # Courses
    courses = get_courses()
    content.append(Paragraph("Courses Progress", styles["Heading2"]))

    for _, row in courses.iterrows():
        text = f"{row['course_name']} ({row['category']}) - Completed: {row['completed']}"
        content.append(Paragraph(text, styles["Normal"]))

    content.append(Spacer(1, 12))

    # Notes
    content.append(Paragraph("Notes Summary", styles["Heading2"]))
    notes = pd.read_sql_query("SELECT * FROM notes", conn)

    for _, n in notes.iterrows():
        text = f"{n['note'][:200]}..."
        content.append(Paragraph(text, styles["Normal"]))

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
# COURSES + NOTES
# =========================================================
if menu == "Courses":
    st.subheader("📚 Courses + Notes")

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

        note = st.text_area("Add note", key=f"n_{row['id']}", height=120)

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
                if st.button("🗑", key=f"d_{n['id']}"):
                    delete_note(n["id"])
                    st.rerun()

# =========================================================
# ADD COURSE
# =========================================================
elif menu == "Add Course":
    st.subheader("➕ Add Course")

    cat = st.selectbox("Category", ["AI","Robotics","Math","Physics","Programming"])
    name = st.text_input("Course Name")

    if st.button("Add"):
        add_course(cat, name)
        st.success("Added")
        st.rerun()

# =========================================================
# JOURNAL
# =========================================================
elif menu == "Journal":
    st.subheader("🧠 Journal")

    title = st.text_input("Title")
    entry = st.text_area("Write journal", height=150)

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
    st.subheader("📤 Upload Exercises")

    courses = get_courses()

    if not courses.empty:
        course = st.selectbox("Course", courses["course_name"])
        cid = courses[courses["course_name"] == course]["id"].values[0]

        file = st.file_uploader("Upload PDF / file")

        if file and st.button("Save"):
            save_exercise(cid, course, file)
            st.rerun()

    st.divider()

    ex = get_exercises()

    for _, r in ex.iterrows():
        st.write(f"📘 {r['course_name']} - {r['file_name']}")

        with open(r["file_path"], "rb") as f:
            st.download_button("Download", f, file_name=r["file_name"])

# =========================================================
# ANALYTICS
# =========================================================
elif menu == "Analytics":
    st.subheader("📊 Progress Analytics")

    df = get_courses()

    if not df.empty:
        st.bar_chart(df.groupby("category")["completed"].mean() * 100)

# =========================================================
# EXPORT PDF (LINKEDIN READY)
# =========================================================
elif menu == "Export PDF":
    st.subheader("📄 Generate LinkedIn Portfolio PDF")

    if st.button("Generate PDF Report"):
        file = generate_pdf()
        with open(file, "rb") as f:
            st.download_button("Download Portfolio PDF", f, file_name=file)
