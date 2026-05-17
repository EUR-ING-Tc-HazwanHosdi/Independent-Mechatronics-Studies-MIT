# =========================================================
# AIMecha Study OS - PDF Integrated Build
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
div.stButton > button { border-radius: 12px; border: 1px solid #00d4ff; background: #0f172a; color: white; transition: all 0.3s ease; }
div.stButton > button:hover { border-color: #00ffcc; box-shadow: 0px 0px 10px rgba(0, 255, 204, 0.4); background: #1e293b; }
div[data-testid="stMetric"] { background: rgba(0,212,255,0.05); padding: 15px; border-radius: 15px; border: 1px solid #1e293b; }
.header-card { background: linear-gradient(135deg,#0f172a,#1e293b); border-radius: 20px; padding: 30px; border: 1px solid #334155; margin-bottom: 25px; }
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
        
        # Courses Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            course_name TEXT NOT NULL,
            completed INTEGER DEFAULT 0
        )
        """)

        # Notes Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            note TEXT,
            sketch_data TEXT,
            image_blob BLOB,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
        """)

        # Assignment Logs Table (UPDATED WITH PDF_BLOB)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_completed TEXT NOT NULL,
            course_name TEXT NOT NULL,
            assignment_name TEXT NOT NULL,
            notes TEXT,
            pdf_blob BLOB,
            pdf_name TEXT
        )
        """)

        # Journal, Exercise, Profile Tables (Simplified for focus)
        cursor.execute("CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, entry TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT, updated_at TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, name TEXT, bio TEXT, title TEXT, profile_img BLOB)")

        # Migration for existing users: Ensure pdf columns exist
        try:
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN pdf_blob BLOB")
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN pdf_name TEXT")
        except sqlite3.OperationalError:
            pass

init_db()

# =========================================================
# UTILITIES
# =========================================================

def compress_img(image_file):
    if image_file is None: return None
    try:
        img = Image.open(image_file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((1000, 1000))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return buf.getvalue()
    except: return None

def multimodal_input(key):
    text = st.text_area("Technical Notes", key=f"text_input_{key}", height=100)
    c1, c2 = st.columns(2)
    with c1:
        canvas = st_canvas(fill_color="rgba(0,0,0,0)", stroke_width=3, stroke_color="#00d4ff", background_color="#0e1117", height=200, width=400, drawing_mode="freedraw", key=f"can_{key}")
    with c2:
        img = st.file_uploader("Reference Spec", type=["png", "jpg"], key=f"img_{key}")
    
    sketch_b64 = None
    if canvas is not None and canvas.image_data is not None:
        if np.any(canvas.image_data[:, :, 3] > 0):
            raw_img = Image.fromarray(canvas.image_data.astype("uint8"), 'RGBA')
            buf = io.BytesIO()
            raw_img.save(buf, format="PNG")
            sketch_b64 = base64.b64encode(buf.getvalue()).decode()
    
    return text, sketch_b64, compress_img(img) if img else None

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("⚙️ AIMecha OS")
menu = st.sidebar.radio("Navigation", ["Dashboard", "Courses", "Journal", "Professional CV", "System Recovery"])

# =========================================================
# DASHBOARD (WITH PDF UPLOADER)
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ Engineering Dashboard")
    
    # Metrics
    df_c = pd.read_sql_query("SELECT * FROM courses", conn)
    c1, c2, c3 = st.columns(3)
    c1.metric("Active Modules", len(df_c))
    c2.metric("Curriculum Progress", f"{(df_c['completed'].mean()*100):.1f}%" if not df_c.empty else "0%")
    
    st.divider()

    # Assignment Submission Section
    st.subheader("📝 Coursework & Exercise Submission")
    
    with st.expander("📤 Log New Assignment / Upload PDF Solution", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            as_date = st.date_input("Completion Date", datetime.now())
            as_course = st.selectbox("Associated Module", df_c['course_name'].tolist() if not df_c.empty else ["General"])
            as_name = st.text_input("Assignment Name", placeholder="e.g. Lab 1: Circuit Analysis")
        with col2:
            as_pdf = st.file_uploader("Attach PDF Documentation / Solution", type=["pdf"])
            as_notes = st.text_area("Submission Notes")

        if st.button("🚀 Commit Assignment to System"):
            if as_name:
                pdf_data = as_pdf.read() if as_pdf else None
                pdf_name = as_pdf.name if as_pdf else None
                with conn:
                    conn.execute("""
                        INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes, pdf_blob, pdf_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (as_date.strftime("%Y-%m-%d"), as_course, as_name, as_notes, pdf_data, pdf_name))
                st.success("Assignment logged successfully!")
                st.rerun()
            else:
                st.error("Assignment name is required.")

    st.divider()

    # Master Registry with PDF Download
    st.markdown("### 🗃️ Master Coursework Registry")
    logs = pd.read_sql_query("SELECT id, date_completed, course_name, assignment_name, notes, pdf_name FROM assignment_logs ORDER BY date_completed DESC", conn)
    
    if logs.empty:
        st.info("No assignments logged yet.")
    else:
        # Display table
        for _, row in logs.iterrows():
            with st.container(border=True):
                cols = st.columns([1, 2, 2, 3, 1])
                cols[0].write(f"#{row['id']}")
                cols[1].write(row['date_completed'])
                cols[2].write(f"**{row['course_name']}**")
                cols[3].write(row['assignment_name'])
                
                # Check for PDF
                if row['pdf_name']:
                    # Retrieve blob for specific ID
                    res = conn.execute("SELECT pdf_blob FROM assignment_logs WHERE id=?", (row['id'],)).fetchone()
                    if res and res[0]:
                        cols[4].download_button(
                            label="📄 View PDF",
                            data=res[0],
                            file_name=row['pdf_name'],
                            mime="application/pdf",
                            key=f"dl_{row['id']}"
                        )
                else:
                    cols[4].write("---")
                
                if row['notes']:
                    st.caption(f"Note: {row['notes']}")

# =========================================================
# OTHER MODULES (PLACEHOLDERS OR PREVIOUS CODE)
# =========================================================
elif menu == "Courses":
    st.title("📚 Modules")
    # ... (Include previous Courses logic here)

elif menu == "System Recovery":
    st.title("🛠️ Recovery")
    if st.button("Purge All Assignment Data"):
        conn.execute("DELETE FROM assignment_logs")
        st.rerun()
