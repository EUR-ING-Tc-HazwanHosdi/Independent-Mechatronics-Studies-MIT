# =========================================================
# AIMecha Study OS - Full Production Build (v2.5)
# =========================================================

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
# FILES & CONSTANTS
# =========================================================

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"
MIT_LOGO_PATH = "MIT-OCW.png"

# =========================================================
# CUSTOM CYBERPUNK THEMING ENGINE
# =========================================================

st.markdown("""
<style>
.stApp { background-color: #0b1120; color: white; }
[data-testid="stSidebar"] { background: #020617; }
div.stButton > button { 
    border-radius: 12px; border: 1px solid #00d4ff; 
    background: #0f172a; color: white; transition: all 0.3s ease; 
}
div.stButton > button:hover { 
    border-color: #00ffcc; box-shadow: 0px 0px 10px rgba(0, 255, 204, 0.4); background: #1e293b; 
}
div[data-testid="stMetric"] { 
    background: rgba(0,212,255,0.05); padding: 15px; border-radius: 15px; border: 1px solid #1e293b; 
}
.header-card { 
    background: linear-gradient(135deg,#0f172a,#1e293b); border-radius: 20px; 
    padding: 30px; border: 1px solid #334155; margin-bottom: 25px; 
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE ENGINE WITH PDF SCHEMA MIGRATION
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
        # Assignment Logs (Structured with PDF storage)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignment_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                date_completed TEXT, 
                course_name TEXT, 
                assignment_name TEXT, 
                notes TEXT,
                file_blob BLOB,
                file_name TEXT
            )
        """)
        # Profile
        cursor.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, name TEXT, bio TEXT, title TEXT)")
        
        # Schema Self-Heal: Add PDF columns if missing
        try:
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN file_blob BLOB")
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN file_name TEXT")
        except sqlite3.OperationalError:
            pass

        # Seed Profile
        cursor.execute("SELECT COUNT(*) FROM profile WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO profile (id, name, bio, title) VALUES (1, 'Your Name', 'AI & Mechatronics Engineer', 'Systems Developer')")

init_db()

# =========================================================
# UTILITIES
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

menu = st.sidebar.radio("Navigation", ["Dashboard", "Courses", "Journal", "Professional CV", "Add Course", "System Recovery"])

# =========================================================
# MODULE 1: DASHBOARD (EXERCISE & ASSIGNMENT HUB)
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ AIMecha Engineering Dashboard")
    
    # Metrics
    df_courses = pd.read_sql_query("SELECT * FROM courses", conn)
    notes_count = pd.read_sql_query("SELECT COUNT(*) FROM notes", conn).iloc[0,0]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Active Modules", len(df_courses))
    c2.metric("Notes Logged", notes_count)
    c3.metric("System Status", "Operational", delta="Optimal")

    st.divider()

    st.subheader("📝 MIT OCW Exercise & Assignment Tracker")
    col_bulk, col_single = st.columns([1, 1])

    with col_bulk:
        st.markdown("**Batch CSV Import**")
        batch_file = st.file_uploader("Upload .CSV for bulk logs", type=["csv"], key="bulk_csv")
        if batch_file:
            try:
                csv_df = pd.read_csv(batch_file)
                if st.button("🚀 Commit CSV to DB"):
                    with conn:
                        for _, row in csv_df.iterrows():
                            conn.execute("INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes) VALUES (?,?,?,?)",
                                         (row['date_completed'], row['course_name'], row['assignment_name'], row['notes']))
                    st.success("Batch Imported!")
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")

    with col_single:
        st.markdown("**Manual Entry & PDF Upload**")
        with st.popover("➕ New Assignment Record"):
            as_date = st.date_input("Completion Date", datetime.now())
            as_course = st.selectbox("Module", df_courses['course_name'].tolist() if not df_courses.empty else ["General"])
            as_name = st.text_input("Assignment Name (e.g. Pset 1)")
            as_notes = st.text_area("Observations")
            
            # THE PDF UPLOADER
            as_pdf = st.file_uploader("Attach Solution PDF", type=["pdf"], key="pdf_single")
            
            if st.button("💾 Save Assignment"):
                p_blob = as_pdf.read() if as_pdf else None
                p_name = as_pdf.name if as_pdf else None
                with conn:
                    conn.execute("""
                        INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes, file_blob, file_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (as_date.strftime("%Y-%m-%d"), as_course, as_name, as_notes, p_blob, p_name))
                st.success("Logged!")
                st.rerun()

    st.markdown("### Master Submission Registry")
    logs = pd.read_sql_query("SELECT * FROM assignment_logs ORDER BY date_completed DESC", conn)
    
    if logs.empty:
        st.info("No assignment history found.")
    else:
        for _, log in logs.iterrows():
            with st.container(border=True):
                m_col, a_col = st.columns([5, 1])
                m_col.markdown(f"**{log['assignment_name']}** | {log['course_name']}")
                m_col.caption(f"Date: {log['date_completed']}")
                if log['notes']: m_col.info(log['notes'])
                
                if log['file_blob']:
                    a_col.download_button(
                        label="📄 PDF",
                        data=log['file_blob'],
                        file_name=log['file_name'] if log['file_name'] else "doc.pdf",
                        mime="application/pdf",
                        key=f"dl_{log['id']}"
                    )
                else:
                    a_col.caption("No Doc")

# =========================================================
# OTHER MODULES (COURSES, JOURNAL, ETC)
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

elif menu == "Journal":
    st.title("📓 System Logs")
    title = st.text_input("Entry Title")
    txt, sk, im = multimodal_input("journal")
    if st.button("Push to Stream"):
        with conn:
            conn.execute("INSERT INTO journal (title, entry, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                         (title, txt, sk, im, datetime.now().strftime("%Y-%m-%d")))
        st.success("Logged!")

elif menu == "Professional CV":
    profile = pd.read_sql_query("SELECT * FROM profile WHERE id = 1", conn).iloc[0]
    st.title(f"🗂️ {profile['name']}")
    st.subheader(profile['title'])
    st.write(profile['bio'])

elif menu == "Add Course":
    st.title("➕ Track New Module")
    with st.form("add_c"):
        name = st.text_input("Course Name")
        cat = st.selectbox("Category", ["Mechatronics", "AI", "Programming", "Electronics"])
        if st.form_submit_button("Inject Module"):
            with conn:
                conn.execute("INSERT INTO courses (category, course_name) VALUES (?, ?)", (cat, name))
            st.success("Course Added!")

elif menu == "System Recovery":
    st.title("🛠️ System Recovery")
    if st.button("📦 Download Database Backup"):
        with open(DB_NAME, "rb") as f:
            st.download_button("Save .db file", f, file_name="backup.db")
    
    restore_file = st.file_uploader("Restore Database", type=["db"])
    if restore_file and st.button("🚨 Overwrite System Core"):
        conn.close()
        with open(DB_NAME, "wb") as f:
            f.write(restore_file.getbuffer())
        st.success("Restored. Reloading...")
        st.rerun()
