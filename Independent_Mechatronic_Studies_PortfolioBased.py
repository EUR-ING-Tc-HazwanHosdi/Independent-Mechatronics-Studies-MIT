# =========================================================
# AIMecha Study OS - Production Stable Build (FIXED)
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
# PAGE CONFIG (MUST BE FIRST STREAMLIT CALL)
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
    border-radius: 20px;
    padding: 25px;
    border: 1px solid #334155;
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

def init_db():
    with conn:
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            course_name TEXT,
            completed INTEGER DEFAULT 0
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            note TEXT,
            sketch_data TEXT,
            image_blob BLOB,
            created_at TEXT,
            updated_at TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            entry TEXT,
            sketch_data TEXT,
            image_blob BLOB,
            created_at TEXT,
            updated_at TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS assignment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_completed TEXT,
            course_name TEXT,
            assignment_name TEXT,
            notes TEXT,
            sketch_data TEXT,
            image_blob BLOB,
            pdf_blob BLOB
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            name TEXT,
            bio TEXT,
            title TEXT,
            profile_img BLOB
        )""")

        # Seed profile
        c.execute("SELECT COUNT(*) FROM profile WHERE id=1")
        if c.fetchone()[0] == 0:
            c.execute("""
                INSERT INTO profile (id, name, bio, title)
                VALUES (1,'Your Name','Industrial AI & Mechatronics Engineer','Engineering Developer')
            """)

init_db()

# =========================================================
# UTILITIES
# =========================================================

def compress_img(file):
    if file is None:
        return None
    img = Image.open(file)
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((1000,1000))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()

def multimodal_input(key):
    text = st.text_area("Notes", key=f"t_{key}", height=120)

    c1, c2 = st.columns(2)

    with c1:
        canvas = st_canvas(
            fill_color="rgba(0, 212, 255, 0.05)",
            stroke_color="#00d4ff",
            stroke_width=3,
            background_color="#0e1117",
            height=250,
            drawing_mode="freedraw",
            key=f"cv_{key}"
        )

    with c2:
        img = st.file_uploader("Image", type=["png","jpg","jpeg"], key=f"img_{key}")

    sketch = None
    if canvas and canvas.image_data is not None:
        arr = canvas.image_data.astype("uint8")
        if arr.shape[-1] == 4 and np.any(arr[:,:,3] > 0):
            buf = io.BytesIO()
            Image.fromarray(arr, "RGBA").save(buf, format="PNG")
            sketch = base64.b64encode(buf.getvalue()).decode()

    return text, sketch, compress_img(img)

# =========================================================
# SIDEBAR
# =========================================================

menu = st.sidebar.radio("Navigation", [
    "Dashboard","Courses","Journal","Professional CV",
    "MIT Learning Hub","Management Center","Add Course","System Recovery"
])

# =========================================================
# DASHBOARD (FIXED SAFE AGGREGATION)
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ Dashboard")

    df = pd.read_sql_query("SELECT * FROM courses", conn)
    notes_count = pd.read_sql_query("SELECT COUNT(*) FROM notes", conn).iloc[0,0]
    journal_count = pd.read_sql_query("SELECT COUNT(*) FROM journal", conn).iloc[0,0]

    completed_pct = 0
    if not df.empty and "completed" in df.columns:
        completed_pct = float(df["completed"].mean() * 100)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Modules", len(df))
    c2.metric("Completion", f"{completed_pct:.1f}%")
    c3.metric("Notes", notes_count)
    c4.metric("Journal", journal_count)

    st.markdown("""
    <div class="header-card">
    System engineering dashboard active.
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# JOURNAL (SAFE)
# =========================================================

elif menu == "Journal":
    st.title("Journal")

    title = st.text_input("Title")
    txt, sk, im = multimodal_input("j")

    if st.button("Save Journal"):
        if txt.strip():
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            conn.execute("""INSERT INTO journal VALUES (NULL,?,?,?,?,?,?)""",
                         (title,txt,sk,im,now,now))
            conn.commit()
            st.rerun()

    df = pd.read_sql_query("SELECT * FROM journal ORDER BY id DESC", conn)
    for _, r in df.iterrows():
        st.subheader(r["title"])
        st.write(r["entry"])

# =========================================================
# CV MODULE
# =========================================================

elif menu == "Professional CV":
    st.title("CV Engine")

    profile = pd.read_sql_query("SELECT * FROM profile WHERE id=1", conn).iloc[0]

    st.markdown(f"""
    <div class="header-card">
    <h2>{profile['name']}</h2>
    <h4>{profile['title']}</h4>
    <p>{profile['bio']}</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Update CV"):
        conn.execute("UPDATE profile SET name=?,title=?,bio=? WHERE id=1",
                     (profile["name"],profile["title"],profile["bio"]))
        conn.commit()
        st.rerun()

# =========================================================
# ADD COURSE
# =========================================================

elif menu == "Add Course":
    st.title("Add Course")

    name = st.text_input("Course Name")
    cat = st.selectbox("Category", ["AI","Robotics","CS","Control"])

    if st.button("Add"):
        conn.execute("INSERT INTO courses VALUES (NULL,?,?,0)", (cat,name))
        conn.commit()
        st.success("Added")

# =========================================================
# SYSTEM RECOVERY
# =========================================================

elif menu == "System Recovery":
    st.title("Recovery")

    if st.button("Download DB"):
        with open(DB_NAME,"rb") as f:
            st.download_button("DB Backup", f, "backup.db")