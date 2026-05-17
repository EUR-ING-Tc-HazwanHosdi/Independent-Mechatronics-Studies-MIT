# =========================================================
# AIMecha Study OS - V4 FINAL STABLE PRODUCTION BUILD
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
# CONFIG
# =========================================================

st.set_page_config(
    page_title="AIMecha Study OS V4",
    page_icon="⚙️",
    layout="wide"
)

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"
MIT_LOGO_PATH = "MIT-OCW.png"

# =========================================================
# THEME
# =========================================================

st.markdown("""
<style>
.stApp { background-color:#0b1120; color:white; }

[data-testid="stSidebar"] { background:#020617; }

div.stButton > button {
    border-radius:12px;
    border:1px solid #00d4ff;
    background:#0f172a;
    color:white;
}

div.stButton > button:hover {
    border-color:#00ffcc;
    box-shadow:0 0 10px rgba(0,255,204,0.3);
}

.header-card {
    background:linear-gradient(135deg,#0f172a,#1e293b);
    padding:20px;
    border-radius:15px;
    border:1px solid #334155;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE (FIXED SAFE CONNECTION)
# =========================================================

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
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
            note TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            entry TEXT,
            created_at TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS assignment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_completed TEXT,
            course_name TEXT,
            assignment_name TEXT,
            notes TEXT,
            sketch_data TEXT,
            image_blob BLOB,
            pdf_blob BLOB
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
            INSERT INTO profile (id,name,bio,title)
            VALUES (1,'Your Name','AIMecha Engineer','Systems Developer')
            """)

init_db()

# =========================================================
# UTILITIES
# =========================================================

def compress_img(file):
    if file is None:
        return None
    img = Image.open(file)
    if img.mode in ("RGBA","P"):
        img = img.convert("RGB")
    img.thumbnail((900,900))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()

def multimodal(key):
    text = st.text_area("Notes", key=f"txt_{key}")

    c1,c2 = st.columns(2)

    with c1:
        canvas = st_canvas(
            stroke_width=3,
            stroke_color="#00d4ff",
            background_color="#0e1117",
            height=220,
            drawing_mode="freedraw",
            key=f"canvas_{key}"
        )

    with c2:
        img = st.file_uploader("Image", type=["png","jpg","jpeg"], key=f"img_{key}")

    sketch = None
    if canvas and canvas.image_data is not None:
        arr = canvas.image_data.astype("uint8")
        if np.any(arr[:,:,3] > 0):
            im = Image.fromarray(arr, "RGBA")
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            sketch = base64.b64encode(buf.getvalue()).decode()

    return text, sketch, compress_img(img)

# =========================================================
# SIDEBAR
# =========================================================

if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.title("AIMecha OS")

menu = st.sidebar.radio(
    "Navigation",
    ["Dashboard","Courses","Journal","Professional CV","MIT Hub","Add Course","System Recovery"]
)

if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=160)

st.sidebar.markdown("### MIT OCW Links")
st.sidebar.markdown("""
- Python Programming  
- Linear Algebra  
- Signals & Systems  
- Robotics  
- Deep Learning  
""")

# =========================================================
# DASHBOARD
# =========================================================

if menu == "Dashboard":
    st.title("AIMecha Dashboard")

    df = pd.read_sql_query("SELECT * FROM courses", conn)
    notes = pd.read_sql_query("SELECT COUNT(*) FROM notes", conn).iloc[0,0]
    journal = pd.read_sql_query("SELECT COUNT(*) FROM journal", conn).iloc[0,0]

    c1,c2,c3 = st.columns(3)
    c1.metric("Courses", len(df))
    c2.metric("Notes", notes)
    c3.metric("Journal", journal)

    st.markdown("<div class='header-card'>System Online</div>", unsafe_allow_html=True)

# =========================================================
# COURSES
# =========================================================

elif menu == "Courses":
    st.title("Courses")

    df = pd.read_sql_query("SELECT * FROM courses", conn)

    for _,r in df.iterrows():
        st.write(f"📘 {r['course_name']} ({r['category']})")

        new = st.checkbox("Completed", bool(r["completed"]), key=r["id"])

        if new != bool(r["completed"]):
            with conn:
                conn.execute(
                    "UPDATE courses SET completed=? WHERE id=?",
                    (int(new), r["id"])
                )
            st.rerun()

# =========================================================
# ADD COURSE
# =========================================================

elif menu == "Add Course":
    st.title("Add Course")

    cat = st.text_input("Category")
    name = st.text_input("Course Name")

    if st.button("Add"):
        with conn:
            conn.execute(
                "INSERT INTO courses(category,course_name) VALUES(?,?)",
                (cat,name)
            )
        st.success("Added")
        st.rerun()

# =========================================================
# JOURNAL
# =========================================================

elif menu == "Journal":
    st.title("Journal")

    t = st.text_input("Title")
    e = st.text_area("Entry")

    if st.button("Save"):
        with conn:
            conn.execute(
                "INSERT INTO journal(title,entry,created_at) VALUES(?,?,?)",
                (t,e,str(datetime.now()))
            )
        st.success("Saved")
        st.rerun()

# =========================================================
# CV
# =========================================================

elif menu == "Professional CV":
    st.title("CV")

    df = pd.read_sql_query("SELECT * FROM profile WHERE id=1", conn)
    st.write(df)

# =========================================================
# MIT HUB
# =========================================================

elif menu == "MIT Hub":
    st.title("MIT Learning Hub")
    st.info("MIT OCW learning dashboard (expandable next upgrade)")

# =========================================================
# SYSTEM RECOVERY
# =========================================================

elif menu == "System Recovery":
    st.title("System Backup")

    if st.button("Export Courses CSV"):
        df = pd.read_sql_query("SELECT * FROM courses", conn)
        st.download_button(
            "Download Backup",
            df.to_csv(index=False),
            "aimecha_backup.csv",
            "text/csv"
        )