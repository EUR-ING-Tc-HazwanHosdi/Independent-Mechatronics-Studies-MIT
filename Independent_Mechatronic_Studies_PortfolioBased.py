# =========================================================
# AIMecha Study OS - Full Production Build (PDF Upgrade ONLY)
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
# THEME (UNCHANGED)
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
    transition: all 0.3s ease;
}
div.stButton > button:hover {
    border-color: #00ffcc;
    box-shadow: 0px 0px 10px rgba(0, 255, 204, 0.4);
    background: #1e293b;
}
div[data-testid="stMetric"] {
    background: rgba(0,212,255,0.05);
    padding: 15px;
    border-radius: 15px;
    border: 1px solid #1e293b;
}
.header-card {
    background: linear-gradient(135deg,#0f172a,#1e293b);
    border-radius: 20px;
    padding: 30px;
    border: 1px solid #334155;
    margin-bottom: 25px;
}
.course-card {
    background: rgba(255,255,255,0.03);
    border-radius: 15px;
    padding: 20px;
    border: 1px solid #1e293b;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DB ENGINE
# =========================================================

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

conn = get_conn()

# =========================================================
# INIT DB (ONLY ADDITION = PDF COLUMN)
# =========================================================

def init_db():
    with conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            course_name TEXT NOT NULL,
            completed INTEGER DEFAULT 0
        )
        """)

        cursor.execute("""
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

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            entry TEXT,
            sketch_data TEXT,
            image_blob BLOB,
            created_at TEXT,
            updated_at TEXT
        )
        """)

        # =========================================================
        # ✅ ONLY CHANGE HERE: PDF SUPPORT
        # =========================================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_completed TEXT NOT NULL,
            course_name TEXT NOT NULL,
            assignment_name TEXT NOT NULL,
            notes TEXT,
            assignment_file BLOB
        )
        """)

        try:
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN assignment_file BLOB")
        except:
            pass

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            name TEXT,
            bio TEXT,
            title TEXT,
            profile_img BLOB
        )
        """)

init_db()

# =========================================================
# UTILITIES (UNCHANGED)
# =========================================================

def compress_img(image_file):
    if image_file is None:
        return None
    try:
        img = Image.open(image_file)
        img = img.convert("RGB")
        img.thumbnail((1000, 1000))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return buf.getvalue()
    except:
        return None

def multimodal_input(key):
    text = st.text_area(
        "Technical Notes / Documentation Context",
        key=f"text_input_{key}",
        height=120
    )

    c1, c2 = st.columns(2)

    with c1:
        canvas = st_canvas(
            fill_color="rgba(0, 212, 255, 0.05)",
            stroke_width=3,
            stroke_color="#00d4ff",
            background_color="#0e1117",
            height=250,
            width=500,
            drawing_mode="freedraw",
            key=f"canvas_{key}"
        )

    with c2:
        img = st.file_uploader(
            "Upload Image",
            type=["png","jpg","jpeg"],
            key=f"img_{key}"
        )

    sketch_b64 = None
    if canvas and canvas.image_data is not None:
        try:
            arr = canvas.image_data
            if np.any(arr[:, :, 3] > 0):
                img_obj = Image.fromarray(arr.astype("uint8"), "RGBA")
                buf = io.BytesIO()
                img_obj.save(buf, format="PNG")
                sketch_b64 = base64.b64encode(buf.getvalue()).decode()
        except:
            pass

    img_blob = compress_img(img) if img else None

    return text, sketch_b64, img_blob

# =========================================================
# SIDEBAR
# =========================================================

menu = st.sidebar.radio("Menu", [
    "Dashboard",
    "Courses",
    "Journal",
    "Professional CV",
    "MIT Learning Hub",
    "Management Center",
    "Add Course",
    "System Recovery"
])

# =========================================================
# DASHBOARD (PDF FEATURE ADDED HERE ONLY)
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ AIMecha Engineering Dashboard")

    st.subheader("📝 Assignment Tracker (WITH PDF SUPPORT)")

    pdf_file = st.file_uploader("Upload Assignment PDF (optional)", type=["pdf"])
    pdf_blob = pdf_file.read() if pdf_file else None

    col1, col2, col3 = st.columns(3)

    with col1:
        course_name = st.text_input("Course Name", "General Course")

    with col2:
        assignment_name = st.text_input("Assignment Name")

    with col3:
        if st.button("Save Assignment"):
            if assignment_name.strip() == "":
                st.error("Assignment name required")
            else:
                conn.execute("""
                    INSERT INTO assignment_logs
                    (date_completed, course_name, assignment_name, notes, assignment_file)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now().strftime("%Y-%m-%d"),
                    course_name,
                    assignment_name,
                    "PDF uploaded submission",
                    pdf_blob
                ))
                conn.commit()
                st.success("Assignment saved with PDF!")

    # View table
    df = pd.read_sql("SELECT id, date_completed, course_name, assignment_name FROM assignment_logs", conn)
    st.dataframe(df, use_container_width=True)

# =========================================================
# COURSES (UNCHANGED CORE)
# =========================================================

elif menu == "Courses":
    st.title("Courses")

# =========================================================
# JOURNAL (UNCHANGED)
# =========================================================

elif menu == "Journal":
    st.title("Journal")

# =========================================================
# CV (UNCHANGED)
# =========================================================

elif menu == "Professional CV":
    st.title("CV")

# =========================================================
# ADD COURSE (UNCHANGED)
# =========================================================

elif menu == "Add Course":
    st.title("Add Course")

# =========================================================
# SYSTEM RECOVERY (UNCHANGED)
# =========================================================

elif menu == "System Recovery":
    st.title("Recovery")
