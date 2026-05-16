# =========================================================
# AIMecha Study OS - FULL RECOVERY SAFE VERSION
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
# FILES
# =========================================================

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"
MIT_LOGO_PATH = "MIT-OCW.png"

# =========================================================
# DB AUTO RECOVERY ENGINE
# =========================================================

def ensure_db():
    if not os.path.exists(DB_NAME):
        open(DB_NAME, "wb").close()

def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

conn = get_conn()

def auto_recover():
    try:
        conn.execute("SELECT 1")
    except:
        os.remove(DB_NAME)
        open(DB_NAME, "wb").close()

auto_recover()
ensure_db()

# =========================================================
# DATABASE INIT
# =========================================================

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
            VALUES (1, 'Your Name', 'AI & Mechatronics Engineer', 'AIMecha Developer')
            """)

init_db()

# =========================================================
# PDF PARSER
# =========================================================

def parse_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for p in pdf.pages:
            text += p.extract_text() or ""

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
            data["notes"] += line.split(":")[-1] + " "

    return data

# =========================================================
# MULTIMODAL INPUT
# =========================================================

def multimodal(key):
    text = st.text_area("Notes", key=f"t_{key}")

    c1, c2 = st.columns(2)

    with c1:
        canvas = st_canvas(
            stroke_color="#00d4ff",
            background_color="#0e1117",
            height=250,
            drawing_mode="freedraw",
            key=f"c_{key}"
        )

    with c2:
        img = st.file_uploader("Image", type=["png","jpg","jpeg"], key=f"i_{key}")

    sketch = None
    if canvas and canvas.image_data is not None:
        arr = canvas.image_data.astype("uint8")
        if np.any(arr > 0):
            img_obj = Image.fromarray(arr)
            buf = io.BytesIO()
            img_obj.save(buf, format="PNG")
            sketch = base64.b64encode(buf.getvalue()).decode()

    img_blob = None
    if img:
        im = Image.open(img)
        buf = io.BytesIO()
        im.save(buf, format="JPEG")
        img_blob = buf.getvalue()

    return text, sketch, img_blob

# =========================================================
# SIDEBAR + LOGOS
# =========================================================

st.sidebar.title("AIMecha OS")

if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)

menu = st.sidebar.radio("Navigation", [
    "Dashboard",
    "Courses",
    "Journal",
    "CV",
    "MIT Hub",
    "Add Course",
    "System Recovery"
])

st.sidebar.divider()

if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=180)

# =========================================================
# DASHBOARD
# =========================================================

if menu == "Dashboard":
    st.title("Dashboard")

    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    notes = pd.read_sql_query("SELECT COUNT(*) FROM notes", conn).iloc[0,0]
    journal = pd.read_sql_query("SELECT COUNT(*) FROM journal", conn).iloc[0,0]

    c1,c2,c3 = st.columns(3)
    c1.metric("Courses", len(courses))
    c2.metric("Notes", notes)
    c3.metric("Journal", journal)

    st.divider()

    st.subheader("📄 PDF Assignment Upload")

    pdf = st.file_uploader("Upload PDF", type=["pdf"])

    if pdf:
        parsed = parse_pdf(pdf)
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

    st.subheader("Assignments")
    st.dataframe(pd.read_sql_query("SELECT * FROM assignment_logs", conn))

# =========================================================
# COURSES
# =========================================================

elif menu == "Courses":
    st.title("Courses")

    courses = pd.read_sql_query("SELECT * FROM courses", conn)

    for _, c in courses.iterrows():
        with st.expander(c["course_name"]):

            txt, sk, im = multimodal(c["id"])

            if st.button("Save Note", key=f"s_{c['id']}"):
                with conn:
                    conn.execute("""
                    INSERT INTO notes
                    VALUES (NULL,?,?,?,?,?,?)
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
    txt, sk, im = multimodal("j")

    if st.button("Save"):
        with conn:
            conn.execute("""
            INSERT INTO journal
            VALUES (NULL,?,?,?,?,?,?)
            """, (
                title, txt, sk, im,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))
        st.rerun()

# =========================================================
# CV
# =========================================================

elif menu == "CV":
    st.title("Professional CV")

    df = pd.read_sql_query("SELECT * FROM profile WHERE id=1", conn)

    if not df.empty:
        p = df.iloc[0]
        st.write(p["name"])
        st.write(p["title"])
        st.write(p["bio"])

# =========================================================
# MIT HUB
# =========================================================

elif menu == "MIT Hub":
    st.title("MIT OCW Hub")
    st.write("Use sidebar links.")

# =========================================================
# ADD COURSE
# =========================================================

elif menu == "Add Course":
    st.title("Add Course")

    name = st.text_input("Name")
    cat = st.text_input("Category")

    if st.button("Add"):
        with conn:
            conn.execute("INSERT INTO courses VALUES (NULL,?,?,0)", (cat, name))
        st.success("Added")

# =========================================================
# SYSTEM RECOVERY
# =========================================================

elif menu == "System Recovery":
    st.title("System Recovery")

    with open(DB_NAME, "rb") as f:
        st.download_button("Backup DB", f, file_name="backup.db")

    restore = st.file_uploader("Restore DB", type=["db"])

    if restore and st.button("Restore"):
        with open(DB_NAME, "wb") as f:
            f.write(restore.getbuffer())
        st.success("Restored")
        st.rerun()
