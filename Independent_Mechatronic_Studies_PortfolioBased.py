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
MIT_LOGO_PATH = "MIT-OCW.png"  # New logo path

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
# CORE FUNCTIONS
# =========================================================

def delete_course_full(course_id):
    conn.execute("DELETE FROM courses WHERE id=?", (course_id,))
    conn.execute("DELETE FROM notes WHERE course_id=?", (course_id,))
    conn.execute("DELETE FROM exercises WHERE course_id=?", (course_id,))
    conn.commit()

def save_exercise(course_id, course_name, uploaded_file):
    blob_data = uploaded_file.read()
    conn.execute("""INSERT INTO exercises (course_id, course_name, file_name, file_blob, created_at)
                    VALUES (?, ?, ?, ?, ?)""", 
                 (course_id, course_name, uploaded_file.name, blob_data, datetime.now().isoformat()))
    conn.commit()

# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

# Display Main Logo
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)

# Display MIT-OCW Logo at the bottom of navigation
st.sidebar.divider()

menu = st.sidebar.radio("Navigation", 
    ["Dashboard", "Courses", "Add Course", "Manage Courses", "Journal", "Exercises", "Professional CV", "System Recovery"])

st.sidebar.spacer = st.sidebar.container() # Create space

# MIT-OCW Integration in Sidebar
st.sidebar.markdown("---")
if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=150)
else:
    st.sidebar.caption("🎓 MIT OpenCourseWare")

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
# MANAGE COURSES
# =========================================================
elif menu == "Manage Courses":
    st.subheader("🗑️ Course Inventory Management")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    
    if df.empty:
        st.warning("No courses to manage.")
    else:
        for _, row in df.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            col1.write(f"**{row['course_name']}**")
            col2.write(f"_{row['category']}_")
            if col3.button("Delete", key=f"del_{row['id']}", type="primary"):
                delete_course_full(row['id'])
                st.rerun()

# =========================================================
# EXERCISES
# =========================================================
elif menu == "Exercises":
    st.subheader("📤 Exercise Vault")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    if not courses.empty:
        sel = st.selectbox("Assign to Course", courses["course_name"])
        c_id = courses[courses["course_name"] == sel]["id"].values[0]
        up = st.file_uploader("Upload Engineering Artifact", type=None)
        if up and st.button("Save to Database"):
            save_exercise(int(c_id), sel, up)
            st.success("File stored safely.")
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
    st.markdown("""<style>.cv-card { background: rgba(255, 255, 255, 0.05); border-left: 5px solid #00d4ff; padding: 20px; border-radius: 10px; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)
    comp = pd.read_sql_query("SELECT * FROM courses WHERE completed = 1", conn)
    if comp.empty:
        st.warning("Complete modules to populate your CV.")
    else:
        for _, row in comp.iterrows():
            st.markdown(f'<div class="cv-card"><b>{row["course_name"]}</b><br><small>Category: {row["category"]}</small></div>', unsafe_allow_html=True)

# =========================================================
# SYSTEM RECOVERY
# =========================================================
elif menu == "System Recovery":
    st.subheader("💾 Backup & Restore")
    with open(DB_NAME, "rb") as f:
        st.download_button("📥 Download Backup", f, file_name="aimecha_backup.db", use_container_width=True)
    up_db = st.file_uploader("Restore Database", type=["db"])
    if up_db and st.button("⚠️ Confirm Restore"):
        conn.close()
        with open(DB_NAME, "wb") as f: f.write(up_db.getbuffer())
        st.cache_resource.clear()
        st.rerun()

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
        st.rerun()
