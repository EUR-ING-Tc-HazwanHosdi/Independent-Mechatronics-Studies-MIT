# =========================================================
# AIMecha Study OS
# Production-Stable Database Engine Upgrade
# READY TO RUN
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
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AIMecha Study OS",
    page_icon="⚙️",
    layout="wide"
)

# =========================================================
# ABSOLUTE PATH ENGINE
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.path.join(BASE_DIR, "aimecha_study_os.db")
BACKUP_JSON = os.path.join(BASE_DIR, "aimecha_backup.json")

LOGO_PATH = os.path.join(BASE_DIR, "AIMECHA.png")
MIT_LOGO_PATH = os.path.join(BASE_DIR, "MIT-OCW.png")

# =========================================================
# CYBERPUNK THEME
# =========================================================

st.markdown("""
<style>

.stApp{
    background-color:#0b1120;
    color:white;
}

[data-testid="stSidebar"]{
    background:#020617;
}

div.stButton > button{
    border-radius:12px;
    border:1px solid #00d4ff;
    background:#0f172a;
    color:white;
    transition:0.3s;
}

div.stButton > button:hover{
    border-color:#00ffcc;
    box-shadow:0px 0px 10px rgba(0,255,204,0.4);
    background:#1e293b;
}

.header-card{
    background:linear-gradient(135deg,#0f172a,#1e293b);
    border-radius:20px;
    padding:30px;
    border:1px solid #334155;
    margin-bottom:25px;
}

.course-card{
    background:rgba(255,255,255,0.03);
    border-radius:15px;
    padding:20px;
    border:1px solid #1e293b;
    margin-bottom:15px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE ENGINE (FIXED)
# =========================================================

def get_conn():
    conn = sqlite3.connect(DB_NAME, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_conn()
    cursor = conn.cursor()

    try:

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
            title TEXT,
            entry TEXT,
            sketch_data TEXT,
            image_blob BLOB,
            created_at TEXT,
            updated_at TEXT
        )
        """)

        cursor.execute("""
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

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            name TEXT,
            bio TEXT,
            title TEXT,
            profile_img BLOB
        )
        """)

        cursor.execute("""
        SELECT COUNT(*) FROM profile WHERE id = 1
        """)

        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO profile (id, name, bio, title)
            VALUES (
                1,
                'Your Name',
                'Industrial AI & Mechatronics Engineer',
                'Engineering Systems Developer'
            )
            """)

        conn.commit()

    finally:
        conn.close()

init_db()

# =========================================================
# IMAGE UTILITIES
# =========================================================

def compress_img(image_file):

    if image_file is None:
        return None

    try:

        img = Image.open(image_file)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.thumbnail((1000,1000))

        buf = io.BytesIO()

        img.save(buf, format="JPEG", quality=80)

        return buf.getvalue()

    except Exception as e:
        st.error(f"Image compression fault: {e}")
        return None

# =========================================================
# MULTIMODAL INPUT
# =========================================================

def multimodal_input(key):

    text = st.text_area(
        "Technical Notes",
        key=f"text_{key}",
        height=120
    )

    c1, c2 = st.columns(2)

    with c1:

        st.caption("🎨 Engineering Sketchpad")

        canvas = st_canvas(
            fill_color="rgba(0,212,255,0.05)",
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
            "Upload Reference Image",
            type=["png","jpg","jpeg"],
            key=f"img_{key}"
        )

    sketch_b64 = None

    if canvas.image_data is not None:

        arr = canvas.image_data.astype("uint8")

        if np.any(arr[:,:,3] > 0):

            raw_img = Image.fromarray(arr, "RGBA")

            buf = io.BytesIO()

            raw_img.save(buf, format="PNG")

            sketch_b64 = base64.b64encode(
                buf.getvalue()
            ).decode()

    img_blob = compress_img(img) if img else None

    return text, sketch_b64, img_blob

# =========================================================
# SIDEBAR
# =========================================================

if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.title("⚙️ AIMecha OS")

menu = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Courses",
        "Journal",
        "Professional CV",
        "MIT Learning Hub",
        "Add Course",
        "System Recovery"
    ]
)

# =========================================================
# DASHBOARD
# =========================================================

if menu == "Dashboard":

    st.title("⚙️ AIMecha Engineering Dashboard")

    conn = get_conn()

    df = pd.read_sql_query(
        "SELECT * FROM courses",
        conn
    )

    notes_count = pd.read_sql_query(
        "SELECT COUNT(*) as total FROM notes",
        conn
    ).iloc[0]["total"]

    journal_count = pd.read_sql_query(
        "SELECT COUNT(*) as total FROM journal",
        conn
    ).iloc[0]["total"]

    conn.close()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Modules", len(df))

    completion = (
        df["completed"].mean() * 100
        if not df.empty else 0
    )

    c2.metric("Completion", f"{completion:.1f}%")

    c3.metric("Notes", notes_count)

    c4.metric("Journal", journal_count)

    st.markdown("""
    <div class="header-card">
    <h3>AIMecha System Matrix</h3>
    <p>
    AI-assisted mechatronics engineering learning ecosystem.
    </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # =====================================================
    # ASSIGNMENT TRACKER
    # =====================================================

    st.subheader("📝 Assignment Tracker")

    conn = get_conn()

    assignments = pd.read_sql_query(
        """
        SELECT *
        FROM assignment_logs
        ORDER BY id DESC
        """,
        conn
    )

    conn.close()

    with st.expander("➕ Add Assignment", expanded=False):

        as_date = st.date_input(
            "Completion Date",
            datetime.now()
        )

        conn = get_conn()

        course_df = pd.read_sql_query(
            "SELECT * FROM courses",
            conn
        )

        conn.close()

        course_options = ["General Study Task"]

        if not course_df.empty:
            course_options = course_df["course_name"].tolist()

        as_course = st.selectbox(
            "Course",
            course_options
        )

        as_name = st.text_input(
            "Assignment Name"
        )

        as_notes, as_sketch, as_img = multimodal_input(
            "assignment"
        )

        pdf_file = st.file_uploader(
            "Upload PDF",
            type=["pdf"]
        )

        if st.button("💾 Save Assignment"):

            pdf_blob = None

            if pdf_file:
                pdf_blob = pdf_file.read()

            conn = get_conn()

            conn.execute("""
            INSERT INTO assignment_logs (
                date_completed,
                course_name,
                assignment_name,
                notes,
                sketch_data,
                image_blob,
                pdf_blob
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                as_date.strftime("%Y-%m-%d"),
                as_course,
                as_name,
                as_notes,
                as_sketch,
                as_img,
                pdf_blob
            ))

            conn.commit()
            conn.close()

            st.success("Assignment saved successfully.")

            st.rerun()

    # =====================================================
    # DISPLAY ASSIGNMENTS
    # =====================================================

    if assignments.empty:

        st.info("No assignments logged.")

    else:

        for _, row in assignments.iterrows():

            with st.container(border=True):

                c1, c2, c3 = st.columns([1,2,1])

                c1.write(f"📅 {row['date_completed']}")
                c2.write(f"📘 {row['assignment_name']}")

                with c3:

                    if st.button(
                        "🗑️ Delete",
                        key=f"del_{row['id']}"
                    ):

                        conn = get_conn()

                        conn.execute(
                            """
                            DELETE FROM assignment_logs
                            WHERE id = ?
                            """,
                            (row['id'],)
                        )

                        conn.commit()
                        conn.close()

                        st.rerun()

                st.write(f"🏷️ {row['course_name']}")

                if row["notes"]:
                    st.markdown(row["notes"])

                img1, img2 = st.columns(2)

                if row["sketch_data"]:

                    img1.image(
                        base64.b64decode(
                            row["sketch_data"]
                        ),
                        caption="Sketch"
                    )

                if row["image_blob"]:

                    img2.image(
                        row["image_blob"],
                        caption="Reference Image"
                    )

                if row["pdf_blob"]:

                    st.download_button(
                        "📥 Download PDF",
                        row["pdf_blob"],
                        file_name=f"{row['assignment_name']}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{row['id']}"
                    )

# =========================================================
# COURSES
# =========================================================

elif menu == "Courses":

    st.title("📚 Courses")

    conn = get_conn()

    courses = pd.read_sql_query(
        "SELECT * FROM courses",
        conn
    )

    conn.close()

    if courses.empty:

        st.info("No courses added.")

    else:

        for _, row in courses.iterrows():

            with st.container(border=True):

                c1, c2, c3 = st.columns([3,1,1])

                c1.write(f"📘 {row['course_name']}")
                c2.write(f"🏷️ {row['category']}")

                completed = bool(row["completed"])

                new_status = c3.checkbox(
                    "Completed",
                    value=completed,
                    key=f"chk_{row['id']}"
                )

                if new_status != completed:

                    conn = get_conn()

                    conn.execute("""
                    UPDATE courses
                    SET completed = ?
                    WHERE id = ?
                    """, (
                        int(new_status),
                        row["id"]
                    ))

                    conn.commit()
                    conn.close()

                    st.rerun()

# =========================================================
# ADD COURSE
# =========================================================

elif menu == "Add Course":

    st.title("➕ Add Course")

    category = st.text_input("Category")

    course_name = st.text_input("Course Name")

    if st.button("🚀 Add Course"):

        if course_name.strip():

            conn = get_conn()

            conn.execute("""
            INSERT INTO courses (
                category,
                course_name
            )
            VALUES (?, ?)
            """, (
                category,
                course_name
            ))

            conn.commit()
            conn.close()

            st.success("Course added.")

            st.rerun()

# =========================================================
# SYSTEM RECOVERY
# =========================================================

elif menu == "System Recovery":

    st.title("🛡️ System Recovery")

    st.subheader("📦 Export Database Backup")

    if st.button("Generate JSON Backup"):

        conn = get_conn()

        backup_data = {}

        tables = [
            "courses",
            "notes",
            "journal",
            "assignment_logs",
            "profile"
        ]

        for table in tables:

            df = pd.read_sql_query(
                f"SELECT * FROM {table}",
                conn
            )

            backup_data[table] = df.to_dict(
                orient="records"
            )

        conn.close()

        with open(BACKUP_JSON, "w") as f:
            json.dump(
                backup_data,
                f,
                indent=4,
                default=str
            )

        st.success("Backup generated.")

        with open(BACKUP_JSON, "rb") as f:

            st.download_button(
                "📥 Download Backup",
                f,
                file_name="aimecha_backup.json",
                mime="application/json"
            )

    st.divider()

    st.subheader("♻️ Restore JSON Backup")

    uploaded_backup = st.file_uploader(
        "Upload Backup JSON",
        type=["json"]
    )

    if uploaded_backup:

        if st.button("🚀 Restore Backup"):

            data = json.load(uploaded_backup)

            conn = get_conn()

            cursor = conn.cursor()

            try:

                for table, rows in data.items():

                    cursor.execute(
                        f"DELETE FROM {table}"
                    )

                    if rows:

                        cols = rows[0].keys()

                        placeholders = ",".join(
                            ["?"] * len(cols)
                        )

                        query = f"""
                        INSERT INTO {table}
                        ({",".join(cols)})
                        VALUES ({placeholders})
                        """

                        for row in rows:

                            cursor.execute(
                                query,
                                tuple(row.values())
                            )

                conn.commit()

                st.success(
                    "Backup restored successfully."
                )

            except Exception as e:

                st.error(
                    f"Restore failure: {e}"
                )

            finally:

                conn.close()

# =========================================================
# MIT HUB
# =========================================================

elif menu == "MIT Learning Hub":

    st.title("🎓 MIT Learning Hub")

    st.markdown("""
    - Python Programming  
    - Linear Algebra  
    - Signals & Systems  
    - Robotics  
    - Deep Learning  
    """)

# =========================================================
# PROFESSIONAL CV
# =========================================================

elif menu == "Professional CV":

    st.title("📄 Professional CV")

    conn = get_conn()

    profile = pd.read_sql_query(
        "SELECT * FROM profile WHERE id = 1",
        conn
    )

    conn.close()

    if not profile.empty:

        profile = profile.iloc[0]

        st.subheader(profile["name"])
        st.write(profile["title"])
        st.write(profile["bio"])