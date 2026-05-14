import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import io

# PDF Generation
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Charts
import plotly.express as px
import plotly.graph_objects as go

# =========================================================
# CONFIG & INITIALIZATION
# =========================================================
st.set_page_config(page_title="AIMecha Study OS", layout="wide")

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"

# Database Connection with high-reliability settings
@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;") 
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

conn = get_conn()

def init_db():
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, course_name TEXT, completed INTEGER DEFAULT 0)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER, note TEXT, created_at TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, entry TEXT, created_at TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER, course_name TEXT, 
                file_name TEXT, file_blob BLOB, created_at TEXT)""")
    conn.commit()

init_db()

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_courses():
    return pd.read_sql_query("SELECT * FROM courses", conn)

def add_course(category, name):
    conn.execute("INSERT INTO courses (category, course_name) VALUES (?, ?)", (category, name))
    conn.commit()

def update_course(course_id, completed):
    conn.execute("UPDATE courses SET completed=? WHERE id=?", (completed, course_id))
    conn.commit()

def save_exercise(course_id, course_name, uploaded_file):
    blob_data = uploaded_file.read()
    conn.execute("""INSERT INTO exercises (course_id, course_name, file_name, file_blob, created_at)
                    VALUES (?, ?, ?, ?, ?)""", 
                 (course_id, course_name, uploaded_file.name, blob_data, datetime.now().isoformat()))
    conn.commit()

def restore_database(uploaded_db):
    conn.close()
    with open(DB_NAME, "wb") as f:
        f.write(uploaded_db.getbuffer())
    st.cache_resource.clear()
    st.rerun()

# =========================================================
# SIDEBAR / NAVIGATION
# =========================================================
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, width=250)

menu = st.sidebar.radio("Navigation", 
    ["Dashboard", "Courses", "Add Course", "Journal", "Exercises", "Competency Matrix", "System Recovery"])

# =========================================================
# DASHBOARD
# =========================================================
if menu == "Dashboard":
    st.title("⚙️ AIMecha Engineering Dashboard")
    courses_df = get_courses()
    
    total_courses = len(courses_df)
    completed_courses = courses_df["completed"].sum() if not courses_df.empty else 0
    progress = (completed_courses / total_courses * 100) if total_courses > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("📚 Total Courses", total_courses)
    col2.metric("✅ Completed", completed_courses)
    col3.metric("📈 Progress", f"{progress:.1f}%")
    st.progress(progress / 100)

# =========================================================
# COURSES & NOTES
# =========================================================
elif menu == "Courses":
    st.subheader("📚 Course Modules")
    df = get_courses()
    if df.empty:
        st.info("No courses found. Go to 'Add Course' to start.")
    else:
        for _, row in df.iterrows():
            with st.expander(f"{row['course_name']} ({row['category']})"):
                is_done = st.checkbox("Mark as Complete", value=bool(row["completed"]), key=f"check_{row['id']}")
                update_course(row["id"], int(is_done))
                
                note_input = st.text_area("Session Notes", key=f"note_{row['id']}")
                if st.button("Save Note", key=f"btn_{row['id']}"):
                    conn.execute("INSERT INTO notes (course_id, note, created_at) VALUES (?, ?, ?)",
                                 (row['id'], note_input, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("Note added!")

# =========================================================
# EXERCISES (BLOB STORAGE)
# =========================================================
elif menu == "Exercises":
    st.subheader("📤 Exercise Vault")
    courses = get_courses()
    
    if not courses.empty:
        selected_course = st.selectbox("Link to Course", courses["course_name"])
        c_id = courses[courses["course_name"] == selected_course]["id"].values[0]
        
        up_file = st.file_uploader("Upload Engineering File", type=None) # All types allowed
        if up_file and st.button("Commit to Database"):
            save_exercise(c_id, selected_course, up_file)
            st.success(f"File '{up_file.name}' saved inside database.")
    
    st.divider()
    ex_df = pd.read_sql_query("SELECT id, course_name, file_name, file_blob FROM exercises", conn)
    for _, ex in ex_df.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.write(f"📁 {ex['file_name']} ({ex['course_name']})")
        c2.download_button("Download", data=ex['file_blob'], file_name=ex['file_name'], key=f"dl_{ex['id']}")

# =========================================================
# COMPETENCY MATRIX
# =========================================================
elif menu == "Competency Matrix":
    st.subheader("🧠 Skills Radar")
    # Example hardcoded data - you can later link this to course counts
    skills = {"Domain": ["Python", "ML", "CAD", "Robotics", "Control"], "Level": [85, 60, 75, 50, 70]}
    fig = go.Figure(data=go.Scatterpolar(r=skills['Level'], theta=skills['Domain'], fill='toself'))
    st.plotly_chart(fig)

# =========================================================
# SYSTEM RECOVERY (BACKUP & RESTORE)
# =========================================================
elif menu == "System Recovery":
    st.subheader("💾 System Maintenance")
    
    # Backup
    with open(DB_NAME, "rb") as f:
        st.download_button(
            label="📥 Download Full OS Backup (.db)",
            data=f,
            file_name=f"AIMecha_Backup_{datetime.now().strftime('%Y%m%d')}.db",
            mime="application/x-sqlite3",
            use_container_width=True
        )
    
    st.divider()
    
    # Restore
    st.warning("Overwriting the system will delete all current data.")
    restore_file = st.file_uploader("Upload Backup File (.db)", type=["db"])
    if restore_file and st.button("⚠️ Confirm System Restore"):
        restore_database(restore_file)

# =========================================================
# ADD COURSE
# =========================================================
elif menu == "Add Course":
    st.subheader("➕ Create New Module")
    cat = st.selectbox("Category", ["AI", "Robotics", "Control", "Electronics", "Math"])
    name = st.text_input("Course Name")
    if st.button("Add Course") and name:
        add_course(cat, name)
        st.success("Module added!")
        st.rerun()

elif menu == "Journal":
    st.subheader("📓 Engineering Journal")
    title = st.text_input("Title")
    entry = st.text_area("Reflection")
    if st.button("Save Entry") and entry:
        conn.execute("INSERT INTO journal (title, entry, created_at) VALUES (?, ?, ?)",
                     (title or "Untitled", entry, datetime.now().isoformat()))
        conn.commit()
        st.rerun()
