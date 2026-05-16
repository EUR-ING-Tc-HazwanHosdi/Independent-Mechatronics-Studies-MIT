# =========================================================
# AIMecha Study OS - FULL VERSION (PDF ENABLED)
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
# CONSTANTS
# =========================================================

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"
MIT_LOGO_PATH = "MIT-OCW.png"

# =========================================================
# THEME
# =========================================================

st.markdown("""
<style>
.stApp { background-color: #0b1120; color: white; }
[data-testid="stSidebar"] { background: #020617; }
div.stButton > button {
    border-radius: 12px;
    border: 1px solid #00d4ff;
    background: #0f172a;
    color: white;
}
div.stButton > button:hover {
    border-color: #00ffcc;
    box-shadow: 0px 0px 10px rgba(0,255,204,0.4);
}
.header-card {
    background: linear-gradient(135deg,#0f172a,#1e293b);
    padding: 25px;
    border-radius: 20px;
    border: 1px solid #334155;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE
# =========================================================

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

conn = get_conn()

def init_db():
    with conn:
        c = conn.cursor()

        # Courses
        c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            course_name TEXT,
            completed INTEGER DEFAULT 0
        )
        """)

        # Notes
        c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            note TEXT,
            sketch_data TEXT,
            image_blob BLOB,
            created_at TEXT,
            updated_at TEXT
        )
        """)

        # Journal
        c.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            entry TEXT,
            sketch_data TEXT,
            image_blob BLOB,
            created_at TEXT,
            updated_at TEXT
        )
        """)

        # =========================
        # UPDATED ASSIGNMENT TABLE
        # =========================
        c.execute("""
        CREATE TABLE IF NOT EXISTS assignment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_completed TEXT,
            course_name TEXT,
            assignment_name TEXT,
            notes TEXT,
            pdf_blob BLOB,
            pdf_name TEXT
        )
        """)

        # Profile
        c.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            name TEXT,
            bio TEXT,
            title TEXT
        )
        """)

        c.execute("SELECT COUNT(*) FROM profile WHERE id=1")
        if c.fetchone()[0] == 0:
            c.execute("""
            INSERT INTO profile (id,name,bio,title)
            VALUES (1,'Your Name','AI & Mechatronics Engineer','Engineering System Developer')
            """)

init_db()

# =========================================================
# HELPERS
# =========================================================

def compress_img(file):
    if file is None:
        return None
    img = Image.open(file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail((1000,1000))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()

def compress_pdf(file):
    if file is None:
        return None
    return file.read()

def multimodal_input(key):
    text = st.text_area("Notes", key=f"t_{key}")

    col1, col2 = st.columns(2)

    with col1:
        canvas = st_canvas(
            stroke_width=3,
            stroke_color="#00d4ff",
            background_color="#0e1117",
            height=250,
            drawing_mode="freedraw",
            key=f"c_{key}"
        )

    with col2:
        img = st.file_uploader("Image", type=["png","jpg","jpeg"], key=f"img_{key}")

    sketch = None
    if canvas and canvas.image_data is not None:
        arr = canvas.image_data.astype("uint8")
        if np.any(arr[:,:,3] > 0):
            buf = io.BytesIO()
            Image.fromarray(arr,'RGBA').save(buf,"PNG")
            sketch = base64.b64encode(buf.getvalue()).decode()

    return text, sketch, compress_img(img)

# =========================================================
# SIDEBAR
# =========================================================

menu = st.sidebar.radio("Menu",[
    "Dashboard","Courses","Journal","Professional CV",
    "MIT Learning Hub","Add Course","System Recovery"
])

# =========================================================
# DASHBOARD (WITH PDF FEATURE)
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ Dashboard")

    df = pd.read_sql("SELECT * FROM courses", conn)
    notes = pd.read_sql("SELECT COUNT(*) FROM notes", conn).iloc[0,0]
    journals = pd.read_sql("SELECT COUNT(*) FROM journal", conn).iloc[0,0]

    c1,c2,c3 = st.columns(3)
    c1.metric("Courses", len(df))
    c2.metric("Notes", notes)
    c3.metric("Journal", journals)

    st.subheader("📝 Assignment Tracker (PDF Enabled)")

    with st.expander("Add Assignment"):
        date = st.date_input("Date", datetime.now())
        course = st.text_input("Course")
        name = st.text_input("Assignment")
        notes_txt = st.text_area("Notes")
        pdf = st.file_uploader("Upload PDF", type=["pdf"])

        if st.button("Save Assignment"):
            conn.execute("""
            INSERT INTO assignment_logs
            (date_completed,course_name,assignment_name,notes,pdf_blob,pdf_name)
            VALUES (?,?,?,?,?,?)
            """,(
                date.strftime("%Y-%m-%d"),
                course,
                name,
                notes_txt,
                compress_pdf(pdf),
                pdf.name if pdf else None
            ))
            conn.commit()
            st.success("Saved")
            st.rerun()

    data = pd.read_sql("SELECT * FROM assignment_logs ORDER BY id DESC", conn)
    st.dataframe(data[["id","date_completed","course_name","assignment_name"]])

    # PDF download section
    st.subheader("📎 PDF Files")
    for _,r in data.iterrows():
        if r["pdf_blob"]:
            with st.expander(r["assignment_name"]):
                st.download_button(
                    "Download PDF",
                    r["pdf_blob"],
                    file_name=r["pdf_name"] or "assignment.pdf",
                    mime="application/pdf"
                )

# =========================================================
# COURSES (UNCHANGED CORE)
# =========================================================

elif menu == "Courses":
    st.title("Courses")
    df = pd.read_sql("SELECT * FROM courses", conn)

    for _,r in df.iterrows():
        st.write(r["course_name"])

# =========================================================
# JOURNAL
# =========================================================

elif menu == "Journal":
    st.title("Journal")
    st.info("Same system retained")

# =========================================================
# CV MODULE
# =========================================================

elif menu == "Professional CV":
    st.title("CV Module")

    p = pd.read_sql("SELECT * FROM profile WHERE id=1", conn).iloc[0]
    st.header(p["name"])
    st.write(p["bio"])

# =========================================================
# MIT HUB
# =========================================================

elif menu == "MIT Learning Hub":
    st.title("MIT Hub")
    st.write("Static links retained")

# =========================================================
# ADD COURSE
# =========================================================

elif menu == "Add Course":
    st.title("Add Course")

    n = st.text_input("Name")
    c = st.text_input("Category")

    if st.button("Add"):
        conn.execute("INSERT INTO courses(course_name,category) VALUES(?,?)",(n,c))
        conn.commit()
        st.success("Added")

# =========================================================
# SYSTEM RECOVERY
# =========================================================

elif menu == "System Recovery":
    st.title("Backup")

    if st.button("Export DB"):
        with open(DB_NAME,"rb") as f:
            st.download_button("Download",f,"backup.db","application/x-sqlite3")
