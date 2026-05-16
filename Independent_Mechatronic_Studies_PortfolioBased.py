# =========================================================
# AIMecha Study OS - Full Production Build (PDF Vault Edition)
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
# DATABASE ENGINE
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
        
        # Core Infrastructure Tables
        cursor.execute("CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, course_name TEXT NOT NULL, completed INTEGER DEFAULT 0)")
        cursor.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, note TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT, updated_at TEXT, FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, entry TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT, updated_at TEXT)")
        
        # Assignment Logs with PDF Blob Support
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

        # Migration Logic: In case the table already existed without PDF columns
        try:
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN file_blob BLOB")
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN file_name TEXT")
        except sqlite3.OperationalError:
            pass # Columns already exist

        cursor.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, name TEXT, bio TEXT, title TEXT)")
        cursor.execute("SELECT COUNT(*) FROM profile WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO profile (id, name, bio, title) VALUES (1, 'Engineer', 'Industrial AI & Mechatronics', 'Systems Developer')")

init_db()

# =========================================================
# UTILITIES
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
    text = st.text_area("Documentation Context", key=f"t_{key}", height=100)
    c1, c2 = st.columns(2)
    with c1:
        canvas = st_canvas(stroke_width=2, stroke_color="#00d4ff", background_color="#0e1117", height=200, width=400, key=f"c_{key}")
    with c2:
        img = st.file_uploader("Reference Attachment", type=["png", "jpg", "jpeg"], key=f"i_{key}")
    
    sketch_b64 = None
    if canvas is not None and canvas.image_data is not None:
        if np.any(canvas.image_data[:, :, 3] > 0):
            raw_img = Image.fromarray(canvas.image_data.astype("uint8"), 'RGBA')
            buf = io.BytesIO()
            raw_img.save(buf, format="PNG")
            sketch_b64 = base64.b64encode(buf.getvalue()).decode()
    
    return text, sketch_b64, compress_img(img)

# =========================================================
# SIDEBAR
# =========================================================

if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
menu = st.sidebar.radio("System Menu", ["Dashboard", "Courses", "Journal", "Professional CV", "MIT Hub", "System Recovery"])

# =========================================================
# MODULE: DASHBOARD (PDF INTEGRATED TRACKER)
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ AIMecha Optimization Dashboard")
    
    # Analytics
    df_c = pd.read_sql_query("SELECT * FROM courses", conn)
    c1, c2, c3 = st.columns(3)
    c1.metric("Active Modules", len(df_c))
    c2.metric("System Mode", "PDF Vault Active")
    c3.metric("DB Protocol", "WAL-Active")

    st.divider()

    st.subheader("📝 MIT OCW Exercise & Assignment Tracker")
    
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**CSV Batch Injection**")
        batch = st.file_uploader("Upload Assignment CSV", type=["csv"])
        if batch and st.button("🚀 Sync Records"):
            csv_df = pd.read_csv(batch)
            with conn:
                for _, row in csv_df.iterrows():
                    conn.execute("INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes) VALUES (?,?,?,?)", 
                                 (row['date_completed'], row['course_name'], row['assignment_name'], row['notes']))
            st.success("Batch Uploaded.")

    with col_r:
        st.markdown("**Log New Submission**")
        with st.popover("➕ New Assignment + PDF"):
            as_date = st.date_input("Date", datetime.now())
            course_list = df_c['course_name'].tolist() if not df_c.empty else ["General"]
            as_course = st.selectbox("Course Module", course_list)
            as_name = st.text_input("Task Title")
            as_notes = st.text_area("Submission Notes")
            
            # PDF Uploader Hook
            pdf_file = st.file_uploader("Attach PDF Solution (Optional)", type=["pdf"])
            
            if st.button("💾 Commit to Registry"):
                f_blob = pdf_file.read() if pdf_file else None
                f_name = pdf_file.name if pdf_file else None
                with conn:
                    conn.execute("""
                        INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes, file_blob, file_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (as_date.strftime("%Y-%m-%d"), as_course, as_name, as_notes, f_blob, f_name))
                st.success("Submission Archived.")
                st.rerun()

    # Master Registry with PDF Downloads
    st.markdown("### Master Coursework Submission Registry")
    logs = pd.read_sql_query("SELECT * FROM assignment_logs ORDER BY date_completed DESC", conn)
    
    if logs.empty:
        st.info("Registry empty.")
    else:
        for _, log in logs.iterrows():
            with st.container(border=True):
                main_c, btn_c = st.columns([6, 1])
                main_c.markdown(f"**{log['assignment_name']}** | {log['course_name']} (📅 {log['date_completed']})")
                if log['notes']: main_c.caption(log['notes'])
                
                # PDF Download logic
                if log['file_blob']:
                    btn_c.download_button(
                        label="📄 PDF",
                        data=log['file_blob'],
                        file_name=log['file_name'] or "submission.pdf",
                        mime="application/pdf",
                        key=f"dl_{log['id']}"
                    )
                
                if btn_c.button("🗑️", key=f"del_as_{log['id']}"):
                    with conn: conn.execute("DELETE FROM assignment_logs WHERE id=?", (log['id'],))
                    st.rerun()

# =========================================================
# OTHER MODULES (MINIMIZED FOR CLARITY)
# =========================================================

elif menu == "Courses":
    st.title("📚 Engineering Modules")
    df_c = pd.read_sql_query("SELECT * FROM courses", conn)
    if df_c.empty:
        st.info("Go to 'System Recovery' to add courses or use DB.")
    else:
        for _, row in df_c.iterrows():
            with st.expander(f"⚙️ {row['course_name']}"):
                txt, sk, im = multimodal_input(row['id'])
                if st.button("Save", key=f"sn_{row['id']}"):
                    with conn:
                        conn.execute("INSERT INTO notes (course_id, note, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                                     (row['id'], txt, sk, im, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    st.success("Saved.")

elif menu == "Journal":
    st.title("📓 System Logs")
    txt, sk, im = multimodal_input("journal")
    if st.button("Push Log"):
        with conn:
            conn.execute("INSERT INTO journal (title, entry, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                         ("System Log", txt, sk, im, datetime.now().strftime("%Y-%m-%d %H:%M")))
        st.success("Synced.")

elif menu == "System Recovery":
    st.title("🛠️ Recovery Protocols")
    with open(DB_NAME, "rb") as f:
        st.download_button("📦 Backup DB", f, file_name="aimecha_backup.db")
    
    st.divider()
    if st.button("➕ Quick Add Placeholder Course"):
        with conn: conn.execute("INSERT INTO courses (category, course_name) VALUES ('Programming', 'Intro to Python')")
        st.rerun()
