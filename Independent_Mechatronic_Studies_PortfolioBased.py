import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import base64
import io
import os
import numpy as np
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="AIMecha Study OS",
    page_icon="⚙️",
    layout="wide"
)

# =========================================================
# CONSTANTS
# =========================================================
DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"
MIT_LOGO_PATH = "MIT-OCW.png"

# =========================================================
# THEME ENGINE
# =========================================================
st.markdown("""
<style>
.stApp { background-color: #0b1120; color: white; }
[data-testid="stSidebar"] { background: #020617; }
div.stButton > button { border-radius: 12px; border: 1px solid #00d4ff; background: #0f172a; color: white; }
.header-card { background: linear-gradient(135deg,#0f172a,#1e293b); border-radius: 20px; padding: 30px; border: 1px solid #334155; margin-bottom: 25px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE CORE & SCHEMA SELF-HEAL
# =========================================================
@st.cache_resource
def get_conn():
    connection = sqlite3.connect(DB_NAME, check_same_thread=False)
    connection.execute("PRAGMA journal_mode=WAL;")
    return connection

conn = get_conn()

def init_db():
    with conn:
        cursor = conn.cursor()
        # Courses
        cursor.execute("CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, course_name TEXT, completed INTEGER DEFAULT 0)")
        # Notes
        cursor.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, note TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT, updated_at TEXT)")
        # Journal
        cursor.execute("CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, entry TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT, updated_at TEXT)")
        # Assignment Logs (With PDF Support)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            date_completed TEXT, 
            course_name TEXT, 
            assignment_name TEXT, 
            notes TEXT,
            file_blob BLOB,
            file_name TEXT
        )""")
        # Profile
        cursor.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, name TEXT, bio TEXT, title TEXT)")
        
        # Check for 1st-time Profile Seed
        cursor.execute("SELECT COUNT(*) FROM profile WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO profile (id, name, bio, title) VALUES (1, 'Your Name', 'AI & Mechatronics Engineer', 'Systems Developer')")

init_db()

# =========================================================
# UTILS
# =========================================================
def multimodal_input(key):
    text = st.text_area("Notes", key=f"txt_{key}", height=100)
    c1, c2 = st.columns(2)
    with c1:
        canvas = st_canvas(stroke_width=3, stroke_color="#00d4ff", background_color="#0e1117", height=200, width=400, key=f"canv_{key}")
    with c2:
        img = st.file_uploader("Attach Image", type=["png", "jpg"], key=f"img_{key}")
    
    sketch_b64 = None
    if canvas.image_data is not None and np.any(canvas.image_data[:, :, 3] > 0):
        img_p = Image.fromarray(canvas.image_data.astype("uint8"), 'RGBA')
        buf = io.BytesIO()
        img_p.save(buf, format="PNG")
        sketch_b64 = base64.b64encode(buf.getvalue()).decode()
    
    return text, sketch_b64, (img.read() if img else None)

# =========================================================
# SIDEBAR
# =========================================================
menu = st.sidebar.radio("Navigation", ["Dashboard", "Courses", "Journal", "Professional CV", "Add Course"])

# =========================================================
# DASHBOARD (PDF & CSV FIX)
# =========================================================
if menu == "Dashboard":
    st.title("⚙️ AIMecha Engineering Dashboard")
    
    col_upload, col_manual = st.columns([1, 1])
    
    with col_upload:
        st.markdown("### 📥 Batch CSV Import")
        assignment_csv = st.file_uploader("Drop CSV file here", type=["csv"])
        if assignment_csv:
            df_csv = pd.read_csv(assignment_csv)
            if st.button("🚀 Process CSV Batch"):
                with conn:
                    for _, row in df_csv.iterrows():
                        conn.execute("INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes) VALUES (?,?,?,?)",
                                     (row['date_completed'], row['course_name'], row['assignment_name'], row['notes']))
                st.success("Batch Imported!")

    with col_manual:
        st.markdown("### ✍️ Log Single Task")
        with st.popover("➕ New Assignment Entry"):
            as_date = st.date_input("Date", datetime.now())
            as_name = st.text_input("Assignment Name")
            as_notes = st.text_area("Submission Notes")
            as_pdf = st.file_uploader("Attach PDF Document", type=["pdf"])
            
            if st.button("💾 Save to Registry"):
                pdf_bytes = as_pdf.read() if as_pdf else None
                pdf_name = as_pdf.name if as_pdf else None
                with conn:
                    conn.execute("INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes, file_blob, file_name) VALUES (?,?,?,?,?,?)",
                                 (as_date.strftime("%Y-%m-%d"), "General", as_name, as_notes, pdf_bytes, pdf_name))
                st.rerun()

    st.divider()
    st.subheader("📋 Master Submission Registry")
    try:
        logs = pd.read_sql_query("SELECT * FROM assignment_logs ORDER BY date_completed DESC", conn)
        for _, log in logs.iterrows():
            with st.container(border=True):
                meta, action = st.columns([4, 1])
                meta.markdown(f"**{log['assignment_name']}** | {log['date_completed']}")
                if log['notes']: meta.caption(log['notes'])
                
                if log['file_blob']:
                    action.download_button("📄 Download PDF", data=log['file_blob'], file_name=log['file_name'], mime="application/pdf", key=f"dl_{log['id']}")
    except:
        st.info("No logs found.")

# =========================================================
# COURSES
# =========================================================
elif menu == "Courses":
    st.title("📚 Study Modules")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    for _, row in courses.iterrows():
        with st.expander(f"⚙️ {row['course_name']}"):
            txt, sk, im = multimodal_input(row['id'])
            if st.button("Commit Note", key=f"btn_{row['id']}"):
                with conn:
                    conn.execute("INSERT INTO notes (course_id, note, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                                 (row['id'], txt, sk, im, datetime.now().strftime("%Y-%m-%d")))
                st.rerun()

# =========================================================
# JOURNAL
# =========================================================
elif menu == "Journal":
    st.title("📓 System Logs")
    title = st.text_input("Entry Title")
    txt, sk, im = multimodal_input("journal")
    if st.button("Push to Stream"):
        with conn:
            conn.execute("INSERT INTO journal (title, entry, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                         (title, txt, sk, im, datetime.now().strftime("%Y-%m-%d")))
        st.success("Logged!")

# =========================================================
# CV / PROFILE
# =========================================================
elif menu == "Professional CV":
    profile = pd.read_sql_query("SELECT * FROM profile WHERE id = 1", conn).iloc[0]
    st.title(f"🗂️ {profile['name']}")
    st.subheader(profile['title'])
    st.write(profile['bio'])

# =========================================================
# ADD COURSE
# =========================================================
elif menu == "Add Course":
    st.title("➕ Track New Module")
    with st.form("add_c"):
        name = st.text_input("Course Name")
        cat = st.selectbox("Category", ["Mechatronics", "AI", "Programming", "Electronics"])
        if st.form_submit_button("Inject Module"):
            with conn:
                conn.execute("INSERT INTO courses (category, course_name) VALUES (?, ?)", (cat, name))
            st.success("Course Added!")
