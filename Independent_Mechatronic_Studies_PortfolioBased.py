# =========================================================
# AIMecha Study OS - FULL RESTORED PROFESSIONAL VERSION
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
import pdfplumber

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AIMecha Study OS",
    page_icon="⚙️",
    layout="wide"
)

# =========================================================
# FILE PATHS (LOGOS RESTORED)
# =========================================================

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"
MIT_LOGO_PATH = "MIT-OCW.png"

# =========================================================
# THEME
# =========================================================

st.markdown("""
<style>
.stApp {
    background-color: #0b1120;
    color: white;
}
[data-testid="stSidebar"] {
    background: #020617;
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

        c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            course_name TEXT,
            completed INTEGER DEFAULT 0
        )
        """)

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

        c.execute("""
        CREATE TABLE IF NOT EXISTS assignment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_completed TEXT,
            course_name TEXT,
            assignment_name TEXT,
            notes TEXT
        )
        """)

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
            INSERT INTO profile (id, name, bio, title)
            VALUES (1, 'Your Name', 'Industrial AI & Mechatronics Engineer', 'Engineering Systems Developer')
            """)

init_db()

# =========================================================
# PDF PARSER
# =========================================================

def parse_assignment_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

    data = {
        "date_completed": "",
        "course_name": "",
        "assignment_name": "",
        "notes": ""
    }

    for line in text.split("\n"):
        l = line.lower()
        if "date" in l:
            data["date_completed"] = line.split(":")[-1].strip()
        elif "course" in l:
            data["course_name"] = line.split(":")[-1].strip()
        elif "assignment" in l:
            data["assignment_name"] = line.split(":")[-1].strip()
        elif "note" in l:
            data["notes"] += line.split(":")[-1].strip() + " "

    return data

# =========================================================
# MULTIMODAL INPUT
# =========================================================

def multimodal_input(key):
    text = st.text_area("Notes", key=f"text_{key}")

    c1, c2 = st.columns(2)

    with c1:
        canvas = st_canvas(
            stroke_color="#00d4ff",
            background_color="#0e1117",
            height=250,
            drawing_mode="freedraw",
            key=f"canvas_{key}"
        )

    with c2:
        img = st.file_uploader("Upload Image", type=["png","jpg","jpeg"], key=f"img_{key}")

    sketch_b64 = None
    if canvas and canvas.image_data is not None:
        arr = canvas.image_data.astype("uint8")
        if np.any(arr > 0):
            img_obj = Image.fromarray(arr)
            buf = io.BytesIO()
            img_obj.save(buf, format="PNG")
            sketch_b64 = base64.b64encode(buf.getvalue()).decode()

    img_blob = None
    if img:
        image = Image.open(img)
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        img_blob = buf.getvalue()

    return text, sketch_b64, img_blob

# =========================================================
# SIDEBAR (LOGOS RESTORED SAFELY)
# =========================================================

st.sidebar.title("AIMecha OS")

# --- Logo safe load ---
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.caption("AIMECHA OS")

menu = st.sidebar.radio("Navigation", [
    "Dashboard",
    "Courses",
    "Journal",
    "Professional CV",
    "MIT Learning Hub",
    "Add Course",
    "System Recovery"
])

st.sidebar.divider()

# --- MIT Logo safe load ---
if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=180)

st.sidebar.subheader("MIT OCW Links")
st.sidebar.markdown("""
- https://ocw.mit.edu/
- https://introtodeeplearning.com/
""")

# =========================================================
# DASHBOARD (WITH PDF SYSTEM RESTORED)
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ Dashboard")

    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    notes = pd.read_sql_query("SELECT COUNT(*) FROM notes", conn).iloc[0,0]
    journal = pd.read_sql_query("SELECT COUNT(*) FROM journal", conn).iloc[0,0]

    c1,c2,c3 = st.columns(3)
    c1.metric("Courses", len(courses))
    c2.metric("Notes", notes)
    c3.metric("Journal", journal)

    st.divider()

    # =========================
    # PDF ASSIGNMENT SYSTEM
    # =========================
    st.subheader("📄 Assignment Upload (PDF)")

    pdf_file = st.file_uploader("Upload Assignment PDF", type=["pdf"])

    if pdf_file:
        parsed = parse_assignment_pdf(pdf_file)

        st.json(parsed)

        if st.button("Save Assignment"):
            with conn:
                conn.execute("""
                    INSERT INTO assignment_logs
                    (date_completed, course_name, assignment_name, notes)
                    VALUES (?,?,?,?)
                """, (
                    parsed["date_completed"],
                    parsed["course_name"],
                    parsed["assignment_name"],
                    parsed["notes"]
                ))
            st.success("Saved!")
            st.rerun()

    st.divider()

    st.subheader("Assignment Logs")
    df = pd.read_sql_query("SELECT * FROM assignment_logs ORDER BY id DESC", conn)
    st.dataframe(df, use_container_width=True)

# =========================================================
# COURSES
# =========================================================

elif menu == "Courses":
    st.title("Courses")

    courses = pd.read_sql_query("SELECT * FROM courses", conn)

    for _, c in courses.iterrows():
        with st.expander(c["course_name"]):
            txt, sk, im = multimodal_input(c["id"])

            if st.button("Save Note", key=f"n_{c['id']}"):
                with conn:
                    conn.execute("""
                        INSERT INTO notes
                        (course_id, note, sketch_data, image_blob, created_at, updated_at)
                        VALUES (?,?,?,?,?,?)
                    """, (
                        c["id"], txt, sk, im,
                        datetime.now().strftime("%Y-%m-%d %H:%M"),
                        datetime.now().strftime("%Y-%m-%d %H:%M")
                    ))
                st.rerun()

# =========================================================
# JOURNAL
# =========================================================

elif menu == "Journal":
    st.title("Journal")

    title = st.text_input("Title")
    txt, sk, im = multimodal_input("journal")

    if st.button("Save Journal"):
        with conn:
            conn.execute("""
                INSERT INTO journal
                (title, entry, sketch_data, image_blob, created_at, updated_at)
                VALUES (?,?,?,?,?,?)
            """, (
                title, txt, sk, im,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))
        st.rerun()

# =========================================================
# CV MODULE (RESTORED SAFE)
# =========================================================

elif menu == "Professional CV":
    st.title("Professional CV")

    df = pd.read_sql_query("SELECT * FROM profile WHERE id=1", conn)

    if df.empty:
        st.warning("No profile found")
    else:
        p = df.iloc[0]

        st.markdown(f"""
        ## {p['name']}
        ### {p['title']}
        {p['bio']}
        """)

# =========================================================
# MIT HUB
# =========================================================

elif menu == "MIT Learning Hub":
    st.title("MIT OCW Hub")

    st.write("Use sidebar links for MIT OCW learning paths.")

# =========================================================
# ADD COURSE
# =========================================================

elif menu == "Add Course":
    st.title("Add Course")

    name = st.text_input("Course Name")
    cat = st.text_input("Category")

    if st.button("Add"):
        with conn:
            conn.execute("INSERT INTO courses (category, course_name) VALUES (?,?)", (cat, name))
        st.success("Added!")

# =========================================================
# SYSTEM RECOVERY
# =========================================================

elif menu == "System Recovery":
    st.title("System Backup")

    with open(DB_NAME, "rb") as f:
        st.download_button("Download DB Backup", f, file_name="aimecha_backup.db")
