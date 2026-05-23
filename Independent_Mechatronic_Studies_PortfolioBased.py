# =========================================================
# AIMecha Study OS - Full Production Build (Optimized)
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
# CUSTOM CYBERPUNK THEMING ENGINE
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
.stCanvas {
    pointer-events: auto !important;
    visibility: visible !important;
    z-index: 1000;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE ENGINE WITH CONTEXT ISOLATION
# =========================================================

@st.cache_resource
def get_conn():

    connection = sqlite3.connect(
        DB_NAME,
        check_same_thread=False,
        timeout=15.0
    )

    # =====================================================
    # SQLITE PERFORMANCE + STABILITY
    # =====================================================

    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA synchronous=NORMAL;")
    connection.execute("PRAGMA temp_store=MEMORY;")

    return connection


def refresh_connection():
    st.cache_resource.clear()
    return get_conn()


conn = get_conn()

def init_db():
    """ Ensures schema generation and applies column migrations. """
    with conn:
        cursor = conn.cursor()

        # Courses Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            course_name TEXT NOT NULL,
            completed INTEGER DEFAULT 0
        )
        """)

        # Notes Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            note TEXT,
            sketch_data TEXT,
            image_blob BLOB,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
        """)

        # Journal Table
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

        # Exercise Data Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercise_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            exercise_split TEXT NOT NULL,
            load_volume REAL,
            notes TEXT
        )
        """)

        # Assignment Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_completed TEXT NOT NULL,
            course_name TEXT NOT NULL,
            assignment_name TEXT NOT NULL,
            notes TEXT
        )
        """)

        # Profile Portfolio Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            name TEXT,
            bio TEXT,
            title TEXT,
            profile_img BLOB
        )
        """)

        # Runtime Schema Updates
        try:
            cursor.execute("ALTER TABLE notes ADD COLUMN updated_at TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE journal ADD COLUMN updated_at TEXT")
        except sqlite3.OperationalError:
            pass

        # Seed configuration identity
        cursor.execute("SELECT COUNT(*) FROM profile WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO profile (id, name, bio, title)
            VALUES (1, 'Your Name', 'Industrial AI & Mechatronics Engineer', 'Engineering Systems Developer')
            """)

        try:
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN pdf_blob BLOB")
        except sqlite3.OperationalError:
            pass

init_db()

# =========================================================
# MULTIMODAL IMAGING & CANVAS CONVERSION UTILITIES
# =========================================================

def compress_img(image_file):
    """ Scales down attached hardware spec captures to protect DB storage footprint. """
    if image_file is None:
        return None
    try:
        img = Image.open(image_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((1000, 1000))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return buf.getvalue()
    except Exception as e:
        st.error(f"Image compression error: {e}")
        return None

def multimodal_input(key):
    """ Renders the dual text field, responsive canvas sketchpad, and file attachment hooks. """
    text = st.text_area(
        "Technical Notes / Documentation Context",
        key=f"text_input_{key}",
        height=120,
        placeholder="Enter equations, operational thresholds, or execution logs..."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.caption("🎨 Engineering Sketchpad Workspace")
        canvas = st_canvas(
            fill_color="rgba(0, 212, 255, 0.05)",
            stroke_width=3,
            stroke_color="#00d4ff",
            background_color="#0e1117",
            height=250,
            width=500,
            drawing_mode="freedraw",
            key=f"canvas_component_{key}",
            update_streamlit=True
        )

    with c2:
        st.caption("🖼️ Upload Reference Documentation Spec")
        img = st.file_uploader(
            "Upload Image Attachment",
            type=["png", "jpg", "jpeg"],
            key=f"img_upload_{key}"
        )

    sketch_b64 = None
    if canvas is not None and canvas.image_data is not None:
        arr = canvas.image_data.astype("uint8")
        if np.any(arr[:, :, 3] > 0):  
            try:
                raw_img = Image.fromarray(arr, 'RGBA')
                buf = io.BytesIO()
                raw_img.save(buf, format="PNG")
                sketch_b64 = base64.b64encode(buf.getvalue()).decode()
            except Exception as e:
                st.error(f"Canvas drawing compression fault: {e}")

    img_blob = compress_img(img) if img else None
    return text, sketch_b64, img_blob

# =========================================================
# APPLICATION NAVIGATION & QUICK LAUNCH SIDEBAR
# =========================================================

if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.title("⚙️ AIMecha OS")

menu = st.sidebar.radio(
    "System Navigation Menu",
    [
        "Dashboard",
        "Courses",
        "Journal",
        "Professional CV",
        "MIT Learning Hub",
        "Management Center",
        "Add Course",
        "System Recovery"
    ]
)

st.sidebar.divider()

if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=180)

st.sidebar.subheader("🎓 MIT Scholar Learning Pathways")
mit_scholar_tracks = {

    "📘 Mathematics Foundation": {
        "18.01SC Calculus":
        "https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/",

        "18.06SC Linear Algebra":
        "https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/",

        "18.03SC Differential Equations":
        "https://ocw.mit.edu/courses/18-03sc-differential-equations-fall-2011/"
    },

    "⚡ Physics & Engineering": {
        "8.01SC Classical Mechanics":
        "https://ocw.mit.edu/courses/8-01sc-classical-mechanics-fall-2016/",

        "8.02SC Electricity & Magnetism":
        "https://ocw.mit.edu/courses/8-02sc-physics-ii-electricity-and-magnetism-fall-2010/"
    },

    "💻 EECS & Computing": {
        "6.01SC Intro EECS":
        "https://ocw.mit.edu/courses/6-01sc-introduction-to-electrical-engineering-and-computer-science-i-spring-2011/",

        "6.0001 Python":
        "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/"
    },

    "🤖 Mechatronics & AI": {
        "Signals & Systems":
        "https://ocw.mit.edu/courses/res-6-007-signals-and-systems-spring-2011/",

        "Feedback Control":
        "https://ocw.mit.edu/courses/6-302-feedback-systems-spring-2007/",

        "Robotics":
        "https://ocw.mit.edu/courses/2-12-introduction-to-robotics-fall-2005/"
    }
}

for category, subjects in mit_scholar_tracks.items():

    st.sidebar.markdown(f"### {category}")

    for course, url in subjects.items():

        st.sidebar.markdown(
            f'''
            <a href="{url}" target="_blank"
            style="text-decoration:none; color:#00d4ff;">
            ⚡ {course}
            </a>
            ''',
            unsafe_allow_html=True
        )

# =========================================================
# MODULE 1: INTERACTIVE ANALYTICS DASHBOARD WITH EXERCISE LOGS
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ AIMecha Engineering & Physical Optimization Dashboard")

    df = pd.read_sql_query("SELECT * FROM courses", conn)
    notes_count = pd.read_sql_query("SELECT COUNT(*) FROM notes", conn).iloc[0,0]
    journal_count = pd.read_sql_query("SELECT COUNT(*) FROM journal", conn).iloc[0,0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Modules", len(df))
    completion = (df['completed'].mean() * 100) if not df.empty else 0
    c2.metric("Curriculum Completion", f"{completion:.1f}%")
    c3.metric("Technical Notes Stack", notes_count)
    c4.metric("Journal Logs Committed", journal_count)

    st.markdown("""
    <div class="header-card">
        <h3>System Overview Matrix</h3>
        <p style="color: #94a3b8;">AIMecha Study OS operates as an isolated knowledge containment engine. 
        Engineered specifically for organizing mathematical models, real-time control system diagrams, 
        and hardware engineering notes across robotics, machine learning, and embedded firmware design tracks.</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.subheader("📝 MIT OCW Exercise & Assignment Tracker")
    st.caption("Log completed problem sets, lab exercises, and programming tasks from your curriculum.")

    col_upload, col_manual = st.columns([1, 1])

    with col_upload:
        st.markdown("**Batch CSV Assignment Log Import**")
        assignment_csv = st.file_uploader("Upload Assignment Log CSV", type=["csv"], key="assignment_csv_drop")

        if assignment_csv is not None:
            try:
                uploaded_df = pd.read_csv(assignment_csv)
                required_cols = ["date_completed", "course_name", "assignment_name", "notes"]
                if all(col in uploaded_df.columns for col in required_cols):
                    if st.button("🚀 Commit Assignments to DB"):
                        with conn:
                            for _, row in uploaded_df.iterrows():
                                conn.execute("""
                                    INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes)
                                    VALUES (?, ?, ?, ?)
                                """, (str(row['date_completed']), str(row['course_name']), str(row['assignment_name']), str(row['notes'])))
                        st.success("Assignment history parsed!")
                        st.rerun()
            except Exception as e:
                st.error(f"CSV Parse Subroutine Fault: {e}")

    with col_manual:
        st.markdown("**Log Completed Task**")
        tab_text, tab_pdf = st.tabs(["📝 Manual Log", "📄 PDF Upload"])

        with tab_text:
            with st.popover("➕ Log Single Task"):
                as_date = st.date_input("Completion Date", datetime.now(), key="manual_date")
                course_options = ["General Study Task"]
                if not df.empty: course_options = df['course_name'].tolist()
                as_course = st.selectbox("Associated MIT Module", course_options, key="manual_course")
                as_name = st.text_input("Assignment Name", placeholder="e.g., Problem Set 1", key="manual_name")
                as_notes = st.text_area("Notes", key="manual_notes")

                if st.button("💾 Append Task Node"):
                    with conn:
                        conn.execute("""
                            INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes)
                            VALUES (?, ?, ?, ?)
                        """, (as_date.strftime("%Y-%m-%d"), as_course, as_name, as_notes))
                    st.success("Logged!")
                    st.rerun()

        with tab_pdf:
            with st.popover("📤 Upload Assignment PDF"):
                pdf_date = st.date_input("Submission Date", datetime.now(), key="pdf_date")
                course_options = ["General Study Task"]
                if not df.empty: course_options = df['course_name'].tolist()
                pdf_course = st.selectbox("Module", course_options, key="pdf_course_sel")
                pdf_name = st.text_input("Assignment Name", placeholder="e.g., Final Lab Report", key="pdf_name_in")
                pdf_file = st.file_uploader("Upload PDF Document", type=["pdf"], key="pdf_file_drop")

                if st.button("🚀 Archive PDF to System"):
                    if pdf_file is not None and pdf_name:
                        pdf_bytes = pdf_file.read()
                        with conn:
                            conn.execute("""
                                INSERT INTO assignment_logs (date_completed, course_name, assignment_name, pdf_blob)
                                VALUES (?, ?, ?, ?)
                            """, (pdf_date.strftime("%Y-%m-%d"), pdf_course, pdf_name, pdf_bytes))
                        st.success("PDF Encrypted and Stored.")
                        st.rerun()
                    else:
                        st.error("Please provide a name and a file.")

    st.markdown("### Master Coursework Submission Registry")
    try:
        db_assignment_logs = pd.read_sql_query("SELECT * FROM assignment_logs ORDER BY date_completed DESC, id DESC", conn)
    except sqlite3.OperationalError:
        db_assignment_logs = pd.DataFrame()

    if db_assignment_logs.empty:
        st.info("No assignment logs committed inside the runtime registry yet.")
    else:
        for _, row in db_assignment_logs.iterrows():
            with st.container(border=True):
                cols = st.columns([1, 2, 2, 1])
                cols[0].write(f"📅 {row['date_completed']}")
                cols[1].write(f"🏷️ **{row['course_name']}**")
                cols[2].write(f"📘 {row['assignment_name']}")

                if 'pdf_blob' in row and row['pdf_blob'] is not None:
                    cols[3].download_button(
                        label="📥 View PDF",
                        data=row['pdf_blob'],
                        file_name=f"{row['assignment_name']}.pdf",
                        mime="application/pdf",
                        key=f"dl_{row['id']}"
                    )
                else:
                    cols[3].caption("No PDF Attached")

        with st.popover("🗑️ Purge Assignment Records"):
            st.warning("This action removes logged metrics.")
            target_id = st.number_input("Target Assignment ID to Erase", min_value=1, step=1)
            if st.button("🚨 Purge Selected Task", key="single_as_purge_btn"):
                with conn:
                    conn.execute("DELETE FROM assignment_logs WHERE id=?", (target_id,))
                st.success(f"Assignment ID {target_id} removed.")
                st.rerun()

# =========================================================
# MODULE 2: DYNAMIC ENGINEERING STUDY MODULES (COURSES)
# =========================================================

elif menu == "Courses":
    st.title("📚 Engineering Study Modules")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)

    if courses.empty:
        st.info("No educational modules registered.")
    else:
        for _, row in courses.iterrows():
            status_tag = "✅ Done" if row['completed'] else "⏳ In Progress"

            with st.expander(f"⚙️ {row['course_name']} — {status_tag}"):
                c1, c2 = st.columns([1, 1])
                with c1:
                    if not row['completed']:
                        if st.button("🔗 Flag As Complete", key=f"comp_{row['id']}"):
                            with conn:
                                conn.execute("UPDATE courses SET completed = 1 WHERE id = ?", (row['id'],))
                            st.rerun()
                    else:
                        if st.button("🔄 Return to Active Buffer", key=f"re_act_{row['id']}"):
                            with conn:
                                conn.execute("UPDATE courses SET completed = 0 WHERE id = ?", (row['id'],))
                            st.rerun()
                with c2:
                    if st.button("🗑️ Wipe Module Structural Node", key=f"del_c_{row['id']}"):
                        with conn:
                            conn.execute("DELETE FROM courses WHERE id = ?", (row['id'],))
                        st.rerun()

                st.divider()
                st.subheader("📝 Append Module Log Entry")

                txt_col, img_col = st.columns([2, 1])
                with txt_col:
                    note_text = st.text_area("Technical Documentation / Notes", 
                                             key=f"nt_txt_{row['id']}", 
                                             placeholder="Enter equations, logic flows, or lecture summaries...")

                with img_col:
                    note_img = st.file_uploader("Upload Schematic / Screenshot", 
                                               type=["png", "jpg", "jpeg"], 
                                               key=f"nt_img_{row['id']}")

                if st.button("🚀 Commit to Module Stack", key=f"commit_btn_{row['id']}"):
                    if note_text.strip() == "" and note_img is None:
                        st.error("Cannot commit an empty log.")
                    else:
                        img_blob = None
                        if note_img:
                            img_blob = note_img.read()

                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                        with conn:
                            conn.execute("""
                                INSERT INTO notes (course_id, note, image_blob, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?)
                            """, (row['id'], note_text, img_blob, timestamp, timestamp))
                        st.success("Documentation Saved.")
                        st.rerun()

                st.divider()
                st.subheader("📂 Saved Documentation Stack")

                course_notes = pd.read_sql_query("SELECT * FROM notes WHERE course_id = ? ORDER BY id DESC", conn, params=(row['id'],))
                if course_notes.empty:
                    st.caption("No technical logs attached to this module sequence.")
                else:
                    for _, n in course_notes.iterrows():
                        with st.container(border=True):
                            nh1, nh2 = st.columns([5, 1])
                            with nh1:
                                st.caption(f"🕒 Registered: {n['created_at']} | Latency Modification: {n['updated_at'] or 'None'}")

                            with nh2:
                                inline_edit_col, inline_del_col = st.columns(2)

                                with inline_edit_col:
                                    with st.popover("✏️", help="Edit local documentation text"):
                                        st.markdown(f"**Modify Entry Layer [Node ID: {n['id']}]**")
                                        updated_note_val = st.text_area(
                                            "Edit Content String", 
                                            value=n['note'] or "", 
                                            key=f"edit_str_{n['id']}",
                                            height=150
                                        )
                                        if st.button("💾 Apply Change", key=f"save_edit_{n['id']}"):
                                            mod_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                                            with conn:
                                                conn.execute("""
                                                    UPDATE notes 
                                                    SET note = ?, updated_at = ? 
                                                    WHERE id = ?
                                                """, (updated_note_val, mod_time, n['id']))
                                            st.success("Buffer modified.")
                                            st.rerun()

                                with inline_del_col:
                                    if st.button("🗑️", key=f"wipe_note_{n['id']}", help="Purge record entirely"):
                                        with conn:
                                            conn.execute("DELETE FROM notes WHERE id = ?", (n['id'],))
                                        st.success("Purged.")
                                        st.rerun()

                            if n['note']:
                                st.markdown(n['note'])
                            if n['image_blob']:
                                st.image(n['image_blob'], use_container_width=False, width=400)

# =========================================================
# MODULE 3: CHRONOLOGICAL ENGINEERING JOURNAL
# =========================================================

elif menu == "Journal":
    st.title("📓 Chronological System Log Journal")

    with st.expander("➕ Open New Chronological System Entry Channel", expanded=True):
        j_title = st.text_input("Log Diagnostic Target Title", "Daily System Engineering Iteration Report")
        txt, sk, im = multimodal_input("journal_master_channel")

        if st.button("🚀 Push Log Entry to Master Stream", key="commit_journal_btn"):
            if txt.strip() == "" and sk is None and im is None:
                st.error("Cannot commit an empty system journal entry.")
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                with conn:
                    conn.execute("""
                    INSERT INTO journal (title, entry, sketch_data, image_blob, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (j_title, txt, sk, im, timestamp, timestamp))
                st.success("Journal update streamed to system storage array.")
                st.rerun()

    st.divider()
    search_j = st.text_input("🔍 Filter Master Journal Stream By String Value", placeholder="Search records...")

    journal_df = pd.read_sql_query("""
        SELECT * FROM journal 
        WHERE title LIKE ? OR entry LIKE ? 
        ORDER BY id DESC
    """, conn, params=(f"%{search_j}%", f"%{search_j}%"))

    for _, j in journal_df.iterrows():
        with st.container(border=True):
            jh1, jh2, jh3 = st.columns([1, 10, 2])
            jh2.subheader(j['title'])

            with jh2:
                with st.popover("✏️"):
                    e_title = st.text_input("Modify Title Header", value=j['title'], key=f"ejt_{j['id']}")
                    e_entry = st.text_area("Modify Body Context", value=j['entry'] or "", key=f"eje_{j['id']}")
                    if st.button("💾 Apply Edits", key=f"sve_j_{j['id']}"):
                        with conn:
                            conn.execute("UPDATE journal SET title=?, entry=?, updated_at=? WHERE id=?", (e_title, e_entry, datetime.now().strftime("%Y-%m-%d %H:%M"), j['id']))
                        st.rerun()

            with jh3:
                if st.button("🗑️", key=f"del_j_{j['id']}"):
                    with conn:
                        conn.execute("DELETE FROM journal WHERE id=?", (j['id'],))
                    st.rerun()

            st.caption(f"🕒 Node Creation Metric: {j['created_at']} | Alteration Marker: {j['updated_at'] or 'No Changes'}")
            if j['entry']:
                st.write(j['entry'])

            jc1, jc2 = st.columns(2)
            if j['sketch_data']:
                try:
                    jc1.image(base64.b64decode(j['sketch_data']), caption="Diagnostic Workspace Sketch")
                except Exception:
                    pass
            if j['image_blob']:
                jc2.image(j['image_blob'], caption="Hardware Component Reference Photo")

# =========================================================
# MODULE 4: SYSTEM OPERATING PORTFOLIO (CV MANAGER)
# =========================================================

elif menu == "Professional CV":
    st.title("🗂️ Engineering Portfolio Identity Engine")

    profile = pd.read_sql_query("SELECT * FROM profile WHERE id = 1", conn).iloc[0]

    st.markdown(f"""
    <div class="header-card">
        <h2>{profile['name']}</h2>
        <h4 style="color: #00d4ff;">{profile['title']}</h4>
        <p style="margin-top:15px; line-height:1.6; color:#cbd5e1;">{profile['bio']}</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("⚙️ Open Local Portfolio Identification Edit Console"):
        u_name = st.text_input("Operational Full Name Label", value=profile['name'])
        u_title = st.text_input("Current System Professional Posture Title", value=profile['title'])
        u_bio = st.text_area("System Biography Meta Text", value=profile['bio'], height=150)

        if st.button("💾 Commit Portfolio Identity Fields"):
            with conn:
                conn.execute("UPDATE profile SET name=?, title=?, bio=? WHERE id=1", (u_name, u_title, u_bio))
            st.success("Identity profile reconfigured.")
            st.rerun()

# =========================================================
# MODULE 5: MIT ACADEMIC CURRICULUM OVERVIEW
# =========================================================

elif menu == "MIT Learning Hub":
    st.title("🎓 MIT Scholar Curriculum Framework")

    st.markdown("""
    Explore the foundational structure of MIT's core mechatronics and AI engineering pathways. 
    Use the sidebar quick launch links to match your active courses with verified open-source syllabus endpoints.
    """)

    mit_scholar_framework = [

    {
        "Phase": "Foundation Mathematics",
        "MIT Scholar Course": "18.01SC Calculus",
        "Purpose": "Engineering mathematics foundation"
    },

    {
        "Phase": "Foundation Mathematics",
        "MIT Scholar Course": "18.06SC Linear Algebra",
        "Purpose": "Robotics and AI matrix operations"
    },

    {
        "Phase": "Engineering Physics",
        "MIT Scholar Course": "8.01SC Mechanics",
        "Purpose": "Motion systems and dynamics"
    },

    {
        "Phase": "EECS Foundation",
        "MIT Scholar Course": "6.01SC Intro EECS",
        "Purpose": "Electrical systems and computation"
    },

    {
        "Phase": "Control Systems",
        "MIT Scholar Course": "6.302 Feedback Systems",
        "Purpose": "Automation and PID systems"
    },

    {
        "Phase": "Robotics",
        "MIT Scholar Course": "2.12 Robotics",
        "Purpose": "Kinematics and robot systems"
    }
]
    st.dataframe(pd.DataFrame(mit_scholar_framework),
use_container_width=True)

st.markdown("""
### AIMecha Scholar Integration Philosophy

This system integrates MIT OpenCourseWare Scholar-based
engineering learning pathways into a portfolio-driven
independent mechatronics and industrial AI framework.

Focus Areas:
- Mathematics foundations
- Engineering physics
- EECS systems
- Robotics
- Automation
- Industrial AI

The objective is structured competency development
through guided independent learning and engineering practice.
""")

# =========================================================
# MODULE 6: COMPREHENSIVE COMPONENT INTERFACE MANAGEMENT
# =========================================================

elif menu == "Management Center":
    st.title("🎛️ Curriculum Management Operations Center")
    st.caption("Perform complete administrative audits over active database vectors and diagnostic datasets.")

    c_list = pd.read_sql_query("SELECT id, category, course_name FROM courses", conn)
    st.subheader("System Modules Register")
    st.dataframe(c_list, use_container_width=True)

# =========================================================
# MODULE 7: INTUITIVE CURRICULUM ACQUISITION INTERFACE
# =========================================================

elif menu == "Add Course":
    st.title("➕ Track New Educational Engineering Module")

    with st.form("course_addition_form", clear_on_submit=True):
        c_name = st.text_input("Module Tracking Nomenclature Name", placeholder="e.g., Computer Vision State Estimation")
        categories = ["Programming", "Artificial Intelligence", "Mechatronics", "Electronics", "Control Systems", "Robotics", "Computer Vision", "Embedded Systems"]
        c_cat = st.selectbox("Structural Operational Field Classification Category", categories)

        if st.form_submit_button("🚀 Inject Course Module into System Array"):
            if c_name.strip() == "":
                st.error("Operation Denied: Course Name cannot consist of empty parameters.")
            else:
                with conn:
                    conn.execute("INSERT INTO courses (category, course_name, completed) VALUES (?, ?, 0)", (c_cat, c_name.strip()))
                st.success(f"Successfully integrated '{c_name}' into database structural array.")

# =========================================================
# MODULE: SYSTEM RECOVERY
# =========================================================

elif menu == "System Recovery":

    st.title("🛡️ AIMecha Recovery Center")

    st.markdown("""
    Full database backup and restore system.

    Includes:
    - Courses
    - Notes
    - Journals
    - PDFs
    - Images
    - Assignment logs
    - Progress tracking
    """)

    st.divider()

    # =====================================================
    # EXPORT DATABASE
    # =====================================================

    st.subheader("📦 Export Full System Backup")
    st.caption("Downloads the COMPLETE AIMecha database.")

    try:
        # SAFE SQLITE BACKUP SNAPSHOT
        conn.commit()

        backup_conn = sqlite3.connect("temp_backup.db")

        with backup_conn:
            conn.backup(backup_conn)

        backup_conn.close()

        with open("temp_backup.db", "rb") as f:
            db_bytes = f.read()

        os.remove("temp_backup.db")

        st.download_button(
            label="📥 Download Full Backup",
            data=db_bytes,
            file_name="aimecha_full_backup.db",
            mime="application/octet-stream"
        )

    except Exception as e:
        st.error(f"Backup Export Failure: {e}")

    st.divider()

    # =====================================================
    # IMPORT DATABASE
    # =====================================================

    st.subheader("♻️ Restore Full System Backup")

    uploaded_db = st.file_uploader(
        "Upload AIMecha Backup Database",
        type=["db"]
    )

    if uploaded_db is not None:

        st.warning("""
        Restoring a backup will OVERWRITE
        the current runtime database.
        """)

        if st.button("🚨 Restore Backup Database"):

            try:

                # =====================================================
                # FORCE CLOSE EXISTING CONNECTION
                # =====================================================

                try:
                    conn.commit()
                    conn.close()
                except:
                    pass

                # =====================================================
                # REMOVE WAL FILES
                # =====================================================

                wal_file = DB_NAME + "-wal"
                shm_file = DB_NAME + "-shm"

                if os.path.exists(wal_file):
                    os.remove(wal_file)

                if os.path.exists(shm_file):
                    os.remove(shm_file)

                # =====================================================
                # RESTORE DATABASE FILE
                # =====================================================

                uploaded_db.seek(0)

                with open(DB_NAME, "wb") as f:
                    f.write(uploaded_db.read())

                # =====================================================
                # RESET STREAMLIT CACHE
                # =====================================================

                st.cache_resource.clear()

                # =====================================================
                # RECONNECT DATABASE
                # =====================================================

                conn = get_conn()

                # =====================================================
                # VALIDATION CHECK
                # =====================================================

                pd.read_sql_query(
                    "SELECT name FROM sqlite_master LIMIT 1",
                    conn
                )

                st.success("✅ Recovery Completed Successfully")
                st.info("Database integrity verified.")

                st.rerun()

            except Exception as e:
                st.error(f"Recovery Failure: {e}")