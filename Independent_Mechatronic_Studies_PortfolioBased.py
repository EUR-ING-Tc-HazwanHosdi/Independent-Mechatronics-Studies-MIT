# =========================================================
# AIMecha OS V5 - Full Production Ready System
# =========================================================

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import base64
import io
import os
import json
import numpy as np
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="AIMecha OS V5",
    page_icon="⚙️",
    layout="wide"
)

DB = "aimecha_v5.db"
LOGO = "AIMECHA.png"
MIT_LOGO = "MIT-OCW.png"

# =========================================================
# STYLE
# =========================================================

st.markdown("""
<style>
.stApp {background:#0b1120; color:white;}
[data-testid="stSidebar"] {background:#020617;}

div.stButton > button {
    border-radius:12px;
    border:1px solid #00d4ff;
    background:#0f172a;
    color:white;
}
div.stButton > button:hover {
    border-color:#00ffcc;
    box-shadow:0 0 10px rgba(0,255,204,0.4);
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE
# =========================================================

@st.cache_resource
def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.execute("PRAGMA foreign_keys=ON;")
    return c

db = conn()

def init():
    cur = db.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS courses(
        id INTEGER PRIMARY KEY,
        category TEXT,
        course TEXT,
        completed INTEGER DEFAULT 0
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS journal(
        id INTEGER PRIMARY KEY,
        title TEXT,
        entry TEXT,
        sketch TEXT,
        image BLOB,
        created TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS notes(
        id INTEGER PRIMARY KEY,
        course TEXT,
        note TEXT,
        sketch TEXT,
        image BLOB,
        created TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS assignments(
        id INTEGER PRIMARY KEY,
        date TEXT,
        course TEXT,
        title TEXT,
        notes TEXT,
        sketch TEXT,
        image BLOB,
        pdf BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS cv_profile(
        id INTEGER PRIMARY KEY,
        name TEXT,
        title TEXT,
        email TEXT,
        phone TEXT,
        location TEXT,
        summary TEXT,
        photo BLOB
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS cv_exp(
        id INTEGER PRIMARY KEY,
        company TEXT,
        role TEXT,
        duration TEXT,
        desc TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS cv_skills(
        id INTEGER PRIMARY KEY,
        skill TEXT,
        level TEXT
    )""")

    db.commit()

init()

# =========================================================
# HELPERS
# =========================================================

def img_blob(upload):
    if upload:
        img = Image.open(upload).convert("RGB")
        img.thumbnail((800,800))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80)
        return buf.getvalue()
    return None

def canvas(key):
    t = st.text_area("Notes", key=f"t_{key}")

    c1,c2 = st.columns(2)

    with c1:
        draw = st_canvas(
            stroke_width=3,
            stroke_color="#00d4ff",
            background_color="#0e1117",
            height=200,
            drawing_mode="freedraw",
            key=f"c_{key}"
        )

    with c2:
        img = st.file_uploader("Image", type=["png","jpg","jpeg"], key=f"i_{key}")

    sketch = None
    if draw.image_data is not None:
        arr = draw.image_data.astype("uint8")
        if np.any(arr[:,:,3] > 0):
            buf = io.BytesIO()
            Image.fromarray(arr,"RGBA").save(buf,"PNG")
            sketch = base64.b64encode(buf.getvalue()).decode()

    return t, sketch, img_blob(img)

# =========================================================
# SIDEBAR
# =========================================================

if os.path.exists(LOGO):
    st.sidebar.image(LOGO)

st.sidebar.title("AIMecha OS V5")

menu = st.sidebar.radio(
    "Menu",
    ["Dashboard","Courses","Journal","Notes","Assignments","CV Builder","Backup"]
)

st.sidebar.divider()

if os.path.exists(MIT_LOGO):
    st.sidebar.image(MIT_LOGO, width=150)

st.sidebar.markdown("### MIT OCW")

links = {
    "Python": "https://ocw.mit.edu",
    "Linear Algebra": "https://ocw.mit.edu",
    "Robotics": "https://ocw.mit.edu"
}

for k,v in links.items():
    st.sidebar.markdown(f"🔗 [{k}]({v})")

# =========================================================
# DASHBOARD
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ AIMecha Dashboard")

    courses = pd.read_sql("SELECT * FROM courses", db)
    notes = pd.read_sql("SELECT COUNT(*) FROM notes", db).iloc[0,0]
    journal = pd.read_sql("SELECT COUNT(*) FROM journal", db).iloc[0,0]
    assign = pd.read_sql("SELECT COUNT(*) FROM assignments", db).iloc[0,0]

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Courses", len(courses))
    c2.metric("Notes", notes)
    c3.metric("Journal", journal)
    c4.metric("Assignments", assign)

# =========================================================
# COURSES
# =========================================================

elif menu == "Courses":
    st.title("Courses")

    df = pd.read_sql("SELECT * FROM courses", db)

    for _,r in df.iterrows():
        c1,c2,c3 = st.columns([3,2,1])

        c1.write(r["course"])
        c2.write(r["category"])

        done = c3.checkbox("Done", bool(r["completed"]), key=f"c_{r['id']}")

        if done != r["completed"]:
            db.execute("UPDATE courses SET completed=? WHERE id=?",
                       (int(done), r["id"]))
            db.commit()
            st.rerun()

    st.divider()

    cat = st.text_input("Category")
    course = st.text_input("Course")

    if st.button("Add"):
        db.execute("INSERT INTO courses(category,course) VALUES (?,?)",(cat,course))
        db.commit()
        st.rerun()

# =========================================================
# JOURNAL
# =========================================================

elif menu == "Journal":
    st.title("Journal")

    title = st.text_input("Title")
    entry, sketch, img = canvas("journal")

    if st.button("Save"):
        db.execute("""
        INSERT INTO journal(title,entry,sketch,image,created)
        VALUES (?,?,?,?,?)
        """,(title,entry,sketch,img,datetime.now().isoformat()))
        db.commit()
        st.rerun()

    df = pd.read_sql("SELECT * FROM journal ORDER BY id DESC", db)
    for _,r in df.iterrows():
        st.write("###",r["title"])
        st.write(r["entry"])

# =========================================================
# NOTES
# =========================================================

elif menu == "Notes":
    st.title("Notes")

    course = st.text_input("Course")
    note, sketch, img = canvas("notes")

    if st.button("Save"):
        db.execute("""
        INSERT INTO notes(course,note,sketch,image,created)
        VALUES (?,?,?,?,?)
        """,(course,note,sketch,img,datetime.now().isoformat()))
        db.commit()
        st.rerun()

# =========================================================
# ASSIGNMENTS
# =========================================================

elif menu == "Assignments":
    st.title("Assignments")

    course = st.text_input("Course")
    title = st.text_input("Title")

    notes, sketch, img = canvas("assign")

    pdf = st.file_uploader("PDF", type=["pdf"])

    if st.button("Save"):
        db.execute("""
        INSERT INTO assignments(date,course,title,notes,sketch,image,pdf)
        VALUES (?,?,?,?,?,?,?)
        """,(
            datetime.now().strftime("%Y-%m-%d"),
            course,title,notes,sketch,img,
            pdf.read() if pdf else None
        ))
        db.commit()
        st.rerun()

# =========================================================
# CV BUILDER (RECRUITER READY)
# =========================================================

elif menu == "CV Builder":
    st.title("📄 Professional CV Builder")

    p = pd.read_sql("SELECT * FROM cv_profile WHERE id=1", db)

    if p.empty:
        db.execute("INSERT INTO cv_profile(id) VALUES (1)")
        db.commit()
        p = pd.read_sql("SELECT * FROM cv_profile WHERE id=1", db)

    p = p.iloc[0]

    name = st.text_input("Name", p.get("name",""))
    title = st.text_input("Title", p.get("title",""))
    email = st.text_input("Email", p.get("email",""))
    phone = st.text_input("Phone", p.get("phone",""))
    location = st.text_input("Location", p.get("location",""))
    summary = st.text_area("Summary", p.get("summary",""))

    photo = st.file_uploader("Photo", type=["png","jpg"])
    photo_blob = img_blob(photo) if photo else p.get("photo")

    if st.button("Save Profile"):
        db.execute("""
        UPDATE cv_profile
        SET name=?,title=?,email=?,phone=?,location=?,summary=?,photo=?
        WHERE id=1
        """,(name,title,email,phone,location,summary,photo_blob))
        db.commit()
        st.rerun()

    st.divider()

    st.subheader("Preview")
    st.write(name, title)
    st.write(email, phone, location)
    st.write(summary)

    if photo_blob:
        st.image(photo_blob, width=120)

# =========================================================
# BACKUP
# =========================================================

elif menu == "Backup":
    st.title("Backup / Restore")

    if st.button("Export"):
        tables = ["courses","journal","notes","assignments","cv_profile"]
        data = {}

        for t in tables:
            df = pd.read_sql(f"SELECT * FROM {t}", db)
            data[t] = df.to_dict(orient="records")

        st.download_button("Download", json.dumps(data,default=str),"backup.json")

    file = st.file_uploader("Restore JSON")

    if file and st.button("Restore"):
        data = json.load(file)

        for table, rows in data.items():
            db.execute(f"DELETE FROM {table}")
            for r in rows:
                q = f"INSERT INTO {table} ({','.join(r.keys())}) VALUES ({','.join(['?']*len(r))})"
                db.execute(q, tuple(r.values()))

        db.commit()
        st.success("Restored")