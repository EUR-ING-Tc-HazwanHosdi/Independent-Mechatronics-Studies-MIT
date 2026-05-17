# =========================================================
# AIMecha Study OS v4 — AI ENGINE FULL PRODUCTION VERSION
# =========================================================

import streamlit as st
import sqlite3
import pandas as pd
import os
import io
import base64
import re
from datetime import datetime
from collections import Counter
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="AIMecha Study OS AI v4",
    page_icon="⚙️",
    layout="wide"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "aimecha_v4.db")

LOGO_PATH = os.path.join(BASE_DIR, "AIMECHA.png")
MIT_LOGO_PATH = os.path.join(BASE_DIR, "MIT-OCW.png")

# =========================================================
# DATABASE ENGINE (STABLE + CLOUD SAFE)
# =========================================================

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def run(query, params=None):
    conn = get_conn()
    cur = conn.cursor()

    try:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)

        conn.commit()
    finally:
        conn.close()


def fetch(query):
    conn = get_conn()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# =========================================================
# INIT DATABASE
# =========================================================

def init_db():

    run("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        course_name TEXT,
        completed INTEGER DEFAULT 0
    )
    """)

    run("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        note TEXT,
        sketch TEXT,
        image BLOB,
        created_at TEXT
    )
    """)

    run("""
    CREATE TABLE IF NOT EXISTS journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        entry TEXT,
        sketch TEXT,
        image BLOB,
        created_at TEXT
    )
    """)

    run("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        course TEXT,
        name TEXT,
        notes TEXT,
        sketch TEXT,
        image BLOB,
        pdf BLOB
    )
    """)

    run("""
    CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY,
        name TEXT,
        bio TEXT,
        title TEXT
    )
    """)

    run("""
    INSERT OR IGNORE INTO profile (id, name, bio, title)
    VALUES (1, 'AIMecha User', 'AI & Mechatronics Engineering System', 'Engineering Developer')
    """)


init_db()

# =========================================================
# AI ENGINE (LOCAL INTELLIGENCE)
# =========================================================

def extract_keywords(text):
    if not text:
        return []
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    return [w for w, _ in Counter(words).most_common(8)]


def summarize(text):
    if not text:
        return "No data."
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
    return ". ".join(sentences[:3]) + "." if sentences else text


def ai_analyze(text):
    return {
        "summary": summarize(text),
        "keywords": extract_keywords(text)
    }

# =========================================================
# UTILITIES
# =========================================================

def img_to_blob(file):
    if file is None:
        return None
    img = Image.open(file).convert("RGB")
    img.thumbnail((900, 900))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def canvas_to_b64(canvas):
    if canvas is None or canvas.image_data is None:
        return None
    arr = canvas.image_data
    if arr.shape[-1] == 4:
        img = Image.fromarray(arr.astype("uint8"), "RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    return None

# =========================================================
# SIDEBAR (RESTORED FULL)
# =========================================================

if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.title("⚙️ AIMecha OS")

st.sidebar.divider()

if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=180)

st.sidebar.subheader("🎓 MIT OCW Quick Launch")

mit_links = {
    "Python": "https://ocw.mit.edu/courses/6-0001/",
    "Linear Algebra": "https://ocw.mit.edu/courses/18-06/",
    "Signals": "https://ocw.mit.edu/courses/6-003/",
    "Control Systems": "https://ocw.mit.edu/courses/6-302/",
    "Robotics": "https://ocw.mit.edu/courses/2-12/",
    "Deep Learning": "https://introtodeeplearning.com/"
}

for k, v in mit_links.items():
    st.sidebar.markdown(f"[⚡ {k}]({v})")

menu = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Courses", "Assignments", "Journal", "Add Course", "CV"]
)

# =========================================================
# DASHBOARD
# =========================================================

if menu == "Dashboard":

    st.title("⚙️ AIMecha AI Dashboard")

    courses = fetch("SELECT * FROM courses")
    notes = fetch("SELECT * FROM notes")
    journal = fetch("SELECT * FROM journal")
    assign = fetch("SELECT * FROM assignments")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Courses", len(courses))
    c2.metric("Notes", len(notes))
    c3.metric("Journal", len(journal))
    c4.metric("Assignments", len(assign))

    st.divider()

    combined_notes = " ".join(notes["note"].dropna().astype(str))
    ai = ai_analyze(combined_notes)

    st.subheader("🧠 AI Study Insight")
    st.write("Summary:")
    st.write(ai["summary"])

    st.write("Keywords:")
    st.write(", ".join(ai["keywords"]))

# =========================================================
# COURSES
# =========================================================

elif menu == "Courses":

    st.title("📚 Courses")

    df = fetch("SELECT * FROM courses")

    for _, r in df.iterrows():
        st.write(f"📘 {r['course_name']}")

# =========================================================
# ASSIGNMENTS
# =========================================================

elif menu == "Assignments":

    st.title("📝 Assignments")

    df = fetch("SELECT * FROM assignments ORDER BY id DESC")

    with st.expander("➕ Add Assignment"):

        date = st.date_input("Date", datetime.now())
        course = st.text_input("Course")
        name = st.text_input("Name")
        notes = st.text_area("Notes")

        canvas = st_canvas(
            stroke_width=3,
            stroke_color="#00d4ff",
            background_color="#111",
            height=200,
            width=400,
            drawing_mode="freedraw",
            key="canvas"
        )

        img = st.file_uploader("Image")
        pdf = st.file_uploader("PDF", type=["pdf"])

        if st.button("Save"):

            run("""
            INSERT INTO assignments
            (date, course, name, notes, sketch, image, pdf)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                date.strftime("%Y-%m-%d"),
                course,
                name,
                notes,
                canvas_to_b64(canvas),
                img_to_blob(img),
                pdf.read() if pdf else None
            ))

            st.success("Saved")
            st.rerun()

    for _, r in df.iterrows():

        with st.container(border=True):
            st.write(f"📅 {r['date']} | 📘 {r['name']}")
            st.write(r["course"])

            if r["notes"]:
                ai = ai_analyze(r["notes"])
                with st.expander("🧠 AI Insight"):
                    st.write(ai["summary"])
                    st.write(ai["keywords"])

# =========================================================
# ADD COURSE
# =========================================================

elif menu == "Add Course":

    st.title("➕ Add Course")

    cat = st.text_input("Category")
    name = st.text_input("Course Name")

    if st.button("Add"):

        run("""
        INSERT INTO courses (category, course_name)
        VALUES (?, ?)
        """, (cat, name))

        st.success("Added")
        st.rerun()

# =========================================================
# JOURNAL
# =========================================================

elif menu == "Journal":

    st.title("📓 Journal")

    df = fetch("SELECT * FROM journal ORDER BY id DESC")

    for _, r in df.iterrows():
        st.write(f"📝 {r['title']}")

        ai = ai_analyze(r["entry"])

        with st.expander("🧠 AI Analysis"):
            st.write(ai["summary"])
            st.write(ai["keywords"])

# =========================================================
# CV
# =========================================================

elif menu == "CV":

    st.title("📄 AI CV")

    profile = fetch("SELECT * FROM profile WHERE id=1")

    notes = fetch("SELECT * FROM notes")

    if not profile.empty:

        p = profile.iloc[0]

        st.subheader(p["name"])
        st.write(p["title"])
        st.write(p["bio"])

        combined = " ".join(notes["note"].dropna().astype(str))
        ai = ai_analyze(combined)

        st.divider()

        st.subheader("🧠 AI Skill Profile")
        st.write(ai["keywords"])

        st.subheader("📌 AI Summary")
        st.write(ai["summary"])