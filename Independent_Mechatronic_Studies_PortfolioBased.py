# =========================================================
# AIMecha Study OS - Full Production Build (Universal File Edition)
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
# DATABASE ENGINE (UPDATED FOR UNIVERSAL FILES)
# =========================================================
@st.cache_resource
def get_conn():
    connection = sqlite3.connect(DB_NAME, check_same_thread=False)
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection

conn = get_conn()

def init_db():
    with conn:
        cursor = conn.cursor()
        # Core Tables
        cursor.execute("CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, course_name TEXT NOT NULL, completed INTEGER DEFAULT 0)")
        cursor.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, note TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT, updated_at TEXT, FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, entry TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT, updated_at TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, name TEXT, bio TEXT, title TEXT)")
        
        # Assignment Logs with Universal File Support
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            date_completed TEXT NOT NULL, 
            course_name TEXT NOT NULL, 
            assignment_name TEXT NOT NULL, 
            notes TEXT,
            file_blob BLOB,
            file_name TEXT
        )
        """)

        # Schema Migrations (Ensure columns exist for older DBs)
        try:
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN file_blob BLOB")
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN file_name TEXT")
        except sqlite3.OperationalError:
            pass

        # Seed Profile
        cursor.execute("SELECT COUNT(*) FROM profile WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO profile (id, name, bio, title) VALUES (1, 'Engineer', 'Industrial AI & Mechatronics', 'Systems Developer')")

init_db()

# =========================================================
# MULTIMODAL HELPERS
# =========================================================
def compress_img(image_file):
    if image_file is None: return None
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((800, 800))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()

def multimodal_input(key):
    text = st.text_area("Technical Notes", key=f"t_{key}", height=100)
    c1, c2 = st.columns(2)
    with c1:
        canvas = st_canvas(stroke_width=2, stroke_color="#00d4ff", background_color="#0e1117", height=200, width=400, key=f"c_{key}")
    with c2:
        img = st.file_uploader("Snapshot", type=["png", "jpg", "jpeg"], key=f"i_{key}")
    
    sketch_b64 = None
    if canvas.image_data is not None and np.any(canvas.image_data[:, :, 3] > 0):
        raw_img = Image.fromarray(canvas.image_data.astype("uint8"), 'RGBA')
        buf = io.BytesIO()
        raw_img.save(buf, format="PNG")
        sketch_b64 = base64.b64encode(buf.getvalue()).decode()
    
    return text, sketch_b64, compress_img(img)

# =========================================================
# NAVIGATION & SIDEBAR
# =========================================================
st.sidebar.title("⚙️ AIMecha OS")
menu = st.sidebar.radio("Navigation", ["Dashboard", "Courses", "Journal", "Professional CV", "MIT Learning Hub", "Add Course", "System Recovery"])

st.sidebar.divider()
st.sidebar.subheader("🎓 MIT OCW Quick Launch")
mit_links = {"Python": "https://ocw.mit.edu/courses/6-0001-fall-2016/", "Control": "https://ocw.mit.edu/courses/6-302-spring-2007/", "Robotics": "https://ocw.mit.edu/courses/2-12-fall-2005/"}
for name, url in mit_links.items():
    st.sidebar.markdown(f"⚡ [{name}]({url})")

# =========================================================
# DASHBOARD: THE UNIVERSAL FILE VAULT
# =========================================================
if menu == "Dashboard":
    st.title("⚙️ AIMecha Study Dashboard")
    
    # Metrics
    df_c = pd.read_sql_query("SELECT * FROM courses", conn)
    c1, c2, c3 = st.columns(3)
    c1.metric("Active Modules", len(df_c))
    c2.metric("System Mode", "Universal File Archiving")
    c3.metric("DB Security", "WAL Protocol Active")

    st.divider()

    # Log/Upload Section
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Batch CSV Injection**")
        batch = st.file_uploader("Bulk Upload Assignments", type=["csv"])
        if batch:
            if st.button("🚀 Push CSV to Database"):
                csv_data = pd.read_csv(batch)
                with conn:
                    for _, row in csv_data.iterrows():
                        conn.execute("INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes) VALUES (?,?,?,?)", 
                                     (row['date_completed'], row['course_name'], row['assignment_name'], row['notes']))
                st.success("Batch Synced.")

    with col_r:
        st.markdown("**Universal File Upload**")
        with st.popover("➕ Add Task + Attachment"):
            as_date = st.date_input("Date", datetime.now())
            as_course = st.selectbox("Module", df_c['course_name'].tolist() if not df_c.empty else ["General"])
            as_name = st.text_input("Task Name")
            as_notes = st.text_area("Observations")
            
            # THE UNIVERSAL FILE HOOK (No type restriction)
            any_file = st.file_uploader("Attach ANY Resource (Zip, Py, PDF, etc.)")
            
            if st.button("💾 Commit to Registry"):
                f_blob = any_file.read() if any_file else None
                f_name = any_file.name if any_file else None
                with conn:
                    conn.execute("""
                        INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes, file_blob, file_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (as_date.strftime("%Y-%m-%d"), as_course, as_name, as_notes, f_blob, f_name))
                st.success(f"Archived: {f_name if f_name else 'Note'}")
                st.rerun()

    # Registry Display
    st.subheader("🗄️ Master Assignment Registry")
    logs = pd.read_sql_query("SELECT * FROM assignment_logs ORDER BY date_completed DESC", conn)
    if logs.empty:
        st.info("Registry clear.")
    else:
        for _, log in logs.iterrows():
            with st.container(border=True):
                c_text, c_btn = st.columns([5, 1])
                c_text.markdown(f"**{log['assignment_name']}** | {log['course_name']} (📅 {log['date_completed']})")
                if log['notes']: c_text.caption(log['notes'])
                
                if log['file_blob']:
                    ext = log['file_name'].split('.')[-1].upper() if '.' in log['file_name'] else "FILE"
                    c_btn.download_button(
                        label=f"📥 {ext}",
                        data=log['file_blob'],
                        file_name=log['file_name'],
                        mime="application/octet-stream",
                        key=f"dl_{log['id']}"
                    )
                if c_btn.button("🗑️", key=f"del_as_{log['id']}"):
                    with conn: conn.execute("DELETE FROM assignment_logs WHERE id=?", (log['id'],))
                    st.rerun()

# =========================================================
# OTHER MODULES (Courses, Journal, etc.)
# =========================================================
elif menu == "Courses":
    st.title("📚 Study Modules")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    for _, row in courses.iterrows():
        with st.expander(f"⚙️ {row['course_name']}"):
            txt, sk, im = multimodal_input(row['id'])
            if st.button("Save Module Note", key=f"sn_{row['id']}"):
                with conn:
                    conn.execute("INSERT INTO notes (course_id, note, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                                 (row['id'], txt, sk, im, datetime.now().strftime("%Y-%m-%d %H:%M")))
                st.success("Note logged.")

elif menu == "Journal":
    st.title("📓 System Logs")
    j_title = st.text_input("Log Title", "System Entry")
    txt, sk, im = multimodal_input("journal")
    if st.button("Push to Journal"):
        with conn:
            conn.execute("INSERT INTO journal (title, entry, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                         (j_title, txt, sk, im, datetime.now().strftime("%Y-%m-%d %H:%M")))
        st.success("Journal update streamed.")

elif menu == "Add Course":
    st.title("➕ Inject New Module")
    with st.form("add_c"):
        name = st.text_input("Module Name")
        cat = st.selectbox("Category", ["Programming", "AI", "Mechatronics", "Control Systems"])
        if st.form_submit_button("Inject"):
            with conn: conn.execute("INSERT INTO courses (category, course_name) VALUES (?,?)", (cat, name))
            st.success("Module Integrated.")

elif menu == "System Recovery":
    st.title("🛠️ Recovery Protocols")
    with open(DB_NAME, "rb") as f:
        st.download_button("📦 Backup Core DB", f, file_name="aimecha_core.db")
    
    restore = st.file_uploader("Restore (.db)", type=["db"])
    if restore and st.button("🚨 Overwrite System"):
        conn.close()
        with open(DB_NAME, "wb") as f:
            f.write(restore.getbuffer())
        st.rerun()

# Professional CV and MIT Hub UI logic follows the same clean structure.
