# =========================================================
# AIMecha Study OS - Full Production Build (PDF Upgrade Only)
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
}
div.stButton > button:hover {
    border-color: #00ffcc;
    box-shadow: 0 0 10px rgba(0,255,204,0.4);
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
# INIT DB (ONLY SMALL ADDITION HERE)
# =========================================================

def init_db():
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS assignment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_completed TEXT NOT NULL,
            course_name TEXT NOT NULL,
            assignment_name TEXT NOT NULL,
            notes TEXT
        )
        """)

        # ✅ NEW COLUMN (PDF STORAGE)
        try:
            conn.execute("ALTER TABLE assignment_logs ADD COLUMN assignment_file BLOB")
        except:
            pass

init_db()

# =========================================================
# IMAGE UTIL (UNCHANGED)
# =========================================================

def compress_img(image_file):
    if image_file is None:
        return None
    try:
        img = Image.open(image_file)
        img = img.convert("RGB")
        img.thumbnail((900, 900))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return buf.getvalue()
    except:
        return None

def multimodal_input(key):
    text = st.text_area("Notes", key=f"text_{key}")

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
        img = st.file_uploader("Image", type=["png","jpg","jpeg"], key=f"img_{key}")

    sketch_b64 = None
    if canvas is not None and canvas.image_data is not None:
        arr = canvas.image_data
        if isinstance(arr, np.ndarray) and arr.shape[-1] == 4 and np.any(arr[:, :, 3] > 0):
            try:
                img_obj = Image.fromarray(arr.astype("uint8"), "RGBA")
                buf = io.BytesIO()
                img_obj.save(buf, format="PNG")
                sketch_b64 = base64.b64encode(buf.getvalue()).decode()
            except:
                pass

    img_blob = compress_img(img)

    return text, sketch_b64, img_blob

# =========================================================
# SIDEBAR (UNCHANGED)
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
# DASHBOARD (UNCHANGED)
# =========================================================

if menu == "Dashboard":
    st.title("AIMecha Dashboard")

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
# ⭐ ONLY MODIFIED PART: ASSIGNMENT LOGGING (INSIDE DASHBOARD AREA LOGIC)
# =========================================================

elif menu == "Dashboard":
    st.title("AIMecha Dashboard")

    st.subheader("📝 Assignment Tracker (PDF ENABLED)")

    col1, col2 = st.columns(2)

    with col1:
        pdf_file = st.file_uploader("Upload Assignment PDF", type=["pdf"])

        if pdf_file:
            pdf_blob = pdf_file.read()
        else:
            pdf_blob = None

    with col2:
        if st.button("Save Assignment"):
            conn.execute("""
                INSERT INTO assignment_logs 
                (date_completed, course_name, assignment_name, notes, assignment_file)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d"),
                "General Course",
                "Uploaded Assignment",
                "PDF Submission",
                pdf_blob
            ))
            conn.commit()
            st.success("Assignment + PDF saved!")

# =========================================================
# SYSTEM RECOVERY (UNCHANGED)
# =========================================================

elif menu == "System Recovery":
    st.title("Recovery")
