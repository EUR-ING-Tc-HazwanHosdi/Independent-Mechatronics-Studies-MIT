# =========================================================
# AIMecha Study OS - CLEAN INTERACTIVE PRODUCTION VERSION
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

DB_NAME = "aimecha.db"
LOGO = "AIMECHA.png"
MIT_LOGO = "MIT-OCW.png"

# =========================================================
# SAFE DB ENGINE (AUTO RECOVERY)
# =========================================================

def init_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

conn = init_connection()

def safe_db():
    try:
        conn.execute("SELECT 1")
    except:
        open(DB_NAME, "wb").close()

safe_db()

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
            sketch TEXT,
            image BLOB,
            created TEXT,
            updated TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            entry TEXT,
            sketch TEXT,
            image BLOB,
            created TEXT,
            updated TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            course TEXT,
            assignment TEXT,
            notes TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            name TEXT,
            title TEXT,
            bio TEXT
        )
        """)

        c.execute("SELECT COUNT(*) FROM profile WHERE id=1")
        if c.fetchone()[0] == 0:
            c.execute("""
            INSERT INTO profile VALUES
            (1,'Your Name','AIMecha Engineer','Mechatronics & AI Systems Developer')
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
        "date": "",
        "course": "",
        "assignment": "",
        "notes": ""
    }

    for line in text.split("\n"):
        l = line.lower()
        if "date" in l:
            data["date"] = line.split(":")[-1].strip()
        elif "course" in l:
            data["course"] = line.split(":")[-1].strip()
        elif "assignment" in l:
            data["assignment"] = line.split(":")[-1].strip()
        elif "note" in l:
            data["notes"] += line.split(":")[-1].strip() + " "

    return data

# =========================================================
# MULTIMODAL INPUT (TEXT + SKETCH + IMAGE)
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
        img = st.file_uploader("Upload Image", type=["png","jpg","jpeg"], key=f"i_{key}")

    sketch = None
    if canvas and canvas.image_data is not None:
        arr = canvas.image_data.astype("uint8")
        if np.any(arr > 0):
            img_obj = Image.fromarray(arr)
            buf = io.BytesIO()
            img_obj.save(buf, "PNG")
            sketch = base64.b64encode(buf.getvalue()).decode()

    img_blob = None
    if img:
        im = Image.open(img)
        buf = io.BytesIO()
        im.save(buf, "JPEG")
        img_blob = buf.getvalue()

    return text, sketch, img_blob

# =========================================================
# SIDEBAR + LOGOS
# =========================================================

st.sidebar.title("⚙️ AIMecha OS")

if os.path.exists(LOGO):
    st.sidebar.image(LOGO, use_container_width=True)

menu = st.sidebar.radio("Menu", [
    "Dashboard",
    "Courses",
    "Journal",
    "CV",
    "Add Course",
    "System Recovery"
])

st.sidebar.divider()

if os.path.exists(MIT_LOGO):
    st.sidebar.image(MIT_LOGO, width=160)

# =========================================================
# DASHBOARD
# =========================================================

if menu == "Dashboard":
    st.title("📊 Dashboard")

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
        data = parse_pdf(pdf)
        st.json(data)

        if st.button("Save Assignment"):
            with conn:
                conn.execute("""
                INSERT INTO assignments
                VALUES (NULL,?,?,?,?)
                """, (
                    data["date"],
                    data["course"],
                    data["assignment"],
                    data["notes"]
                ))
            st.success("Saved!")
            st.rerun()

    st.dataframe(pd.read_sql_query("SELECT * FROM assignments", conn))

# =========================================================
# COURSES
# =========================================================

elif menu == "Courses":
    st.title("📚 Courses")

    courses = pd.read_sql_query("SELECT * FROM courses", conn)

    for _, c in courses.iterrows():
        with st.expander(c["course_name"]):

            txt, sk, im = multimodal(c["id"])

            if st.button("Save Note", key=c["id"]):
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
    st.title("📓 Journal")

    title = st.text_input("Title")
    txt, sk, im = multimodal("journal")

    if st.button("Save Entry"):
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
# CV MODULE
# =========================================================

elif menu == "CV":
    st.title("🗂 Professional CV")

    df = pd.read_sql_query("SELECT * FROM profile WHERE id=1", conn)

    if not df.empty:
        p = df.iloc[0]
        st.markdown(f"""
        ## {p['name']}
        ### {p['title']}
        {p['bio']}
        """)

# =========================================================
# ADD COURSE
# =========================================================

elif menu == "Add Course":
    st.title("➕ Add Course")

    name = st.text_input("Course Name")
    cat = st.text_input("Category")

    if st.button("Add"):
        with conn:
            conn.execute("INSERT INTO courses VALUES (NULL,?,?,0)", (cat, name))
        st.success("Added!")

# =========================================================
# SYSTEM RECOVERY (BACKUP + RESTORE)
# =========================================================

elif menu == "System Recovery":
    st.title("🛠 System Recovery")

    st.subheader("📦 Backup")
    with open(DB_NAME, "rb") as f:
        st.download_button("Download DB", f, file_name="aimecha_backup.db")

    st.subheader("🔄 Restore")

    file = st.file_uploader("Upload DB", type=["db"])

    if file and st.button("Restore"):
        with open(DB_NAME, "wb") as f:
            f.write(file.getbuffer())
        st.success("Restored!")
        st.rerun()
