import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import io

# =========================================================
# CONFIG & INITIALIZATION
# =========================================================
st.set_page_config(page_title="AIMecha Study OS", layout="wide")

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"

@st.cache_resource
def get_conn():
    # WAL mode and Synchronous Normal ensure the database doesn't corrupt 
    # when the app goes to sleep or restarts.
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
# CORE FUNCTIONS
# =========================================================

def save_exercise(course_id, course_name, uploaded_file):
    blob_data = uploaded_file.read()
    conn.execute("""INSERT INTO exercises (course_id, course_name, file_name, file_blob, created_at)
                    VALUES (?, ?, ?, ?, ?)""", 
                 (course_id, course_name, uploaded_file.name, blob_data, datetime.now().isoformat()))
    conn.commit()

def restore_system(uploaded_db):
    conn.close()
    with open(DB_NAME, "wb") as f:
        f.write(uploaded_db.getbuffer())
    st.cache_resource.clear()
    st.rerun()

# =========================================================
# SIDEBAR NAVIGATION
# =========================================================
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, width=250)

menu = st.sidebar.radio("Navigation", 
    ["Dashboard", "Courses", "Add Course", "Journal", "Exercises", "Professional CV", "System Recovery"])

# =========================================================
# DASHBOARD
# =========================================================
if menu == "Dashboard":
    st.title("⚙️ AIMecha Engineering Dashboard")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    
    total = len(df)
    done = df["completed"].sum() if total > 0 else 0
    prog = (done / total) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Modules", total)
    c2.metric("Completed", done)
    c3.metric("Progress", f"{prog*100:.1f}%")
    st.progress(prog)

# =========================================================
# COURSES & NOTES
# =========================================================
elif menu == "Courses":
    st.subheader("📚 Learning Modules")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    
    if df.empty:
        st.info("No courses found. Add your first module to begin.")
    else:
        for _, row in df.iterrows():
            with st.expander(f"{row['course_name']} ({row['category']})"):
                completed = st.checkbox("Mark as Complete", value=bool(row["completed"]), key=f"c_{row['id']}")
                conn.execute("UPDATE courses SET completed=? WHERE id=?", (int(completed), row['id']))
                conn.commit()
                
                note = st.text_area("Live Notes", key=f"n_{row['id']}")
                if st.button("Save Note", key=f"b_{row['id']}"):
                    conn.execute("INSERT INTO notes (course_id, note, created_at) VALUES (?, ?, ?)",
                                 (row['id'], note, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("Note saved.")

# =========================================================
# EXERCISES (BLOB ENGINE)
# =========================================================
elif menu == "Exercises":
    st.subheader("📤 Exercise Vault")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    
    if not courses.empty:
        sel = st.selectbox("Assign to Course", courses["course_name"])
        c_id = courses[courses["course_name"] == sel]["id"].values[0]
        
        up = st.file_uploader("Upload Engineering Artifact (No Limit)", type=None)
        if up and st.button("Save to Database"):
            save_exercise(int(c_id), sel, up)
            st.success("File stored safely in database.")
            st.rerun()
    
    st.divider()
    exs = pd.read_sql_query("SELECT id, course_name, file_name, file_blob FROM exercises", conn)
    for _, ex in exs.iterrows():
        col1, col2 = st.columns([5,1])
        col1.write(f"📁 **{ex['file_name']}** ({ex['course_name']})")
        col2.download_button("Download", data=ex['file_blob'], file_name=ex['file_name'], key=f"dl_{ex['id']}")

# =========================================================
# PROFESSIONAL CV
# =========================================================
elif menu == "Professional CV":
    st.title("📄 Engineering Portfolio")
    
    st.markdown("""
        <style>
        .cv-card {
            background: rgba(255, 255, 255, 0.05);
            border-left: 5px solid #00d4ff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header-box {
            background: #111;
            padding: 30px;
            border-radius: 15px;
            border: 1px solid #333;
            margin-bottom: 25px;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="header-box"><h1>MECHATRONICS AI PORTFOLIO</h1><p>Verified Technical Progress & Project Documentation</p></div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🛠 Technical Mastery")
        st.write("- Python Development\n- Data Science & Modeling\n- AI Architectures\n- Mechatronics Systems")

    with col2:
        st.subheader("🎓 Completed Certifications")
        comp = pd.read_sql_query("SELECT * FROM courses WHERE completed = 1", conn)
        if comp.empty:
            st.warning("Mark courses as complete to show certifications here.")
        else:
            for _, row in comp.iterrows():
                st.markdown(f'<div class="cv-card"><b>{row["course_name"]}</b><br><small>Verified Category: {row["category"]}</small></div>', unsafe_allow_html=True)

# =========================================================
# SYSTEM RECOVERY
# =========================================================
elif menu == "System Recovery":
    st.subheader("💾 System Maintenance")
    
    with open(DB_NAME, "rb") as f:
        st.download_button("📥 Download Database Backup", f, file_name="aimecha_os_backup.db", use_container_width=True)
    
    st.divider()
    up_db = st.file_uploader("📤 Restore from Backup", type=["db"])
    if up_db and st.button("⚠️ Confirm System Restore"):
        restore_system(up_db)

# =========================================================
# ADD COURSE
# =========================================================
elif menu == "Add Course":
    st.subheader("➕ Create New Module")
    with st.form("course_form"):
        cat = st.selectbox("Category", ["AI", "Programming", "Robotics", "Control", "Electronics"])
        name = st.text_input("Course Name")
        if st.form_submit_button("Add Course") and name:
            conn.execute("INSERT INTO courses (category, course_name) VALUES (?, ?)", (cat, name))
            conn.commit()
            st.success("Course Added!")
            st.rerun()

# =========================================================
# JOURNAL
# =========================================================
elif menu == "Journal":
    st.subheader("📓 Engineering Journal")
    title = st.text_input("Title")
    entry = st.text_area("Entry")
    if st.button("Save Entry") and entry:
        conn.execute("INSERT INTO journal (title, entry, created_at) VALUES (?, ?, ?)",
                     (title or "Daily Log", entry, datetime.now().isoformat()))
        conn.commit()
        st.success("Saved.")
        st.rerun()
