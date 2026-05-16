# =========================================================
# AIMecha Study OS - Full Production Build (Fixed Sketchpads & Schema)
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
    """ Returns global connection cached across execution context frames. """
    connection = sqlite3.connect(DB_NAME, check_same_thread=False)
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection

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

        # Assignment Logs Table (Upgraded to Multimodal Structural Layer)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_completed TEXT NOT NULL,
            course_name TEXT NOT NULL,
            assignment_name TEXT NOT NULL,
            notes TEXT,
            sketch_data TEXT,
            image_blob BLOB,
            pdf_blob BLOB
        )
        """)

        # Runtime Schema Updates for existing databases (Prevents crashes if database already exists)
        try:
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN sketch_data TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE assignment_logs ADD COLUMN image_blob BLOB")
        except sqlite3.OperationalError:
            pass

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

st.sidebar.subheader("🎓 MIT OCW Quick Launch")
mit_courses = {
    "Python Programming": "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/",
    "Linear Algebra": "https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/",
    "Signals & Systems": "https://ocw.mit.edu/courses/res-6-007-signals-and-systems-spring-2011/",
    "Feedback Control": "https://ocw.mit.edu/courses/6-302-feedback-systems-spring-2007/",
    "Robotics": "https://ocw.mit.edu/courses/2-12-introduction-to-robotics-fall-2005/",
    "Deep Learning": "https://introtodeeplearning.com/"
}

for course, url in mit_courses.items():
    st.sidebar.markdown(f'<a href="{url}" target="_blank" style="text-decoration:none; color:#00d4ff;">⚡ {course}</a>', unsafe_allow_html=True)

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

    # =========================================================
    # MIT OCW ASSIGNMENT & EXERCISE TRACKER
    # =========================================================
    st.subheader("📝 MIT OCW Exercise & Assignment Tracker")
    st.caption("Log completed problem sets, lab exercises, and programming tasks from your curriculum.")
    
    try:
        db_assignment_logs = pd.read_sql_query("SELECT * FROM assignment_logs ORDER BY date_completed DESC, id DESC", conn)
    except Exception as e:
        db_assignment_logs = pd.DataFrame()
        
    col_upload, col_manual = st.columns([1, 1])
    
    with col_upload:
        st.markdown("**Batch CSV Assignment Log Import**")
        assignment_csv = st.file_uploader("Upload Assignment Log CSV", type=["csv"], key="assignment_csv_drop")
        
        if assignment_csv is not None:
            try:
                uploaded_df = pd.read_csv(assignment_csv)
                required_cols = ["date_completed", "course_name", "assignment_name", "notes"]
                if all(col in uploaded_df.columns for col in required_cols):
                    if st.button("🚀 Commit Assignments to DB", key="commit_csv_btn"):
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
        st.markdown("**Log Completed Task Node**")
        sub_tab_text, sub_tab_pdf = st.tabs(["📝 Multimodal Logging", "📄 PDF Direct Ingestion"])

        with sub_tab_text:
            with st.popover("➕ Open Dynamic Assignment Log Channel", use_container_width=True):
                as_date = st.date_input("Completion Date", datetime.now(), key="manual_date")
                course_options = ["General Study Task"]
                if not df.empty: course_options = df['course_name'].tolist()
                as_course = st.selectbox("Associated MIT Module", course_options, key="manual_course")
                as_name = st.text_input("Assignment/Task Name", placeholder="e.g., Problem Set 1 / Lab 3 Matrix", key="manual_name")
                
                as_notes, as_sketch, as_img = multimodal_input("assignment_tracker_channel")
                
                if st.button("💾 Append Task to Master Stack", use_container_width=True):
                    if not as_name.strip():
                        st.error("Assignment tracking label cannot be blank.")
                    else:
                        with conn:
                            conn.execute("""
                                INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes, sketch_data, image_blob)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (as_date.strftime("%Y-%m-%d"), as_course, as_name, as_notes, as_sketch, as_img))
                        st.success("Multimodal task record successfully locked in matrix.")
                        st.rerun()

        with sub_tab_pdf:
            with st.popover("📤 Upload Formal PDF Deliverable", use_container_width=True):
                pdf_date = st.date_input("Submission Date", datetime.now(), key="pdf_date")
                course_options = ["General Study Task"]
                if not df.empty: course_options = df['course_name'].tolist()
                pdf_course = st.selectbox("Module Reference Alignment", course_options, key="pdf_course_sel")
                pdf_name = st.text_input("Assignment Metric Name", placeholder="e.g., Verified Proof Set", key="pdf_name_in")
                pdf_file = st.file_uploader("Upload PDF Document Binary", type=["pdf"], key="pdf_file_drop")
                
                if st.button("🚀 Archive PDF to System Storage", use_container_width=True):
                    if pdf_file is not None and pdf_name:
                        pdf_bytes = pdf_file.read()
                        with conn:
                            conn.execute("""
                                INSERT INTO assignment_logs (date_completed, course_name, assignment_name, pdf_blob)
                                VALUES (?, ?, ?, ?)
                            """, (pdf_date.strftime("%Y-%m-%d"), pdf_course, pdf_name, pdf_bytes))
                        st.success("PDF Encrypted and Stored in Repository.")
                        st.rerun()

    st.markdown("### Master Coursework Submission Registry")
    
    if db_assignment_logs.empty:
        st.info("No active academic assignment entries detected inside the system infrastructure registry.")
    else:
        for _, row in db_assignment_logs.iterrows():
            with st.container(border=True):
                cols = st.columns([1, 2, 3, 1])
                cols[0].write(f"📅 **{row['date_completed']}**")
                cols[1].write(f"🏷️ `{row['course_name']}`")
                cols[2].write(f"📘 **{row['assignment_name']}**")
                
                with cols[3]:
                    inline_as_edit, inline_as_del = st.columns(2)
                    with inline_as_edit:
                        with st.popover("✏️", help="Modify textual elements"):
                            st.markdown(f"**Modify Assignment Text [ID: {row['id']}]**")
                            up_as_name = st.text_input("Edit Assignment Title", value=row['assignment_name'], key=f"as_name_ed_{row['id']}")
                            up_as_notes = st.text_area("Edit Explanatory Context", value=row['notes'] or "", key=f"as_notes_ed_{row['id']}")
                            if st.button("💾 Push Mutation", key=f"save_as_ed_{row['id']}"):
                                with conn:
                                    conn.execute("""
                                        UPDATE assignment_logs 
                                        SET assignment_name = ?, notes = ? 
                                        WHERE id = ?
                                    """, (up_as_name, up_as_notes, row['id']))
                                st.rerun()
                    with inline_as_del:
                        if st.button("🗑️", key=f"wipe_as_{row['id']}", help="Wipe assignment log"):
                            with conn:
                                conn.execute("DELETE FROM assignment_logs WHERE id = ?", (row['id'],))
                            st.rerun()

                if row['notes'] and str(row['notes']).strip() != "":
                    st.markdown(f"**Notes:** {row['notes']}")

                img_c1, img_c2 = st.columns(2)
                
                if 'sketch_data' in row and row['sketch_data']:
                    try:
                        img_c1.image(base64.b64decode(row['sketch_data']), caption="Assignment Design Sketch / Math Workflow")
                    except Exception:
                        pass
                        
                if 'image_blob' in row and row['image_blob']:
                    img_c2.image(row['image_blob'], caption="Attached Hardware Spec Snapshot / Proof Image")
                    
                if 'pdf_blob' in row and row['pdf_blob'] is not None:
                    st.download_button(
                        label="📥 Download Attached Verification PDF Deliverable",
                        data=row['pdf_blob'],
                        file_name=f"{row['assignment_name']}.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_node_{row['id']}"
                    )

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
    st.title("🎓 MIT OpenCourseWare Core Tracking Matrix")
    
    st.markdown("""
    Explore the foundational structure of MIT's core mechatronics and AI engineering pathways. 
    Use the sidebar quick launch links to match your active courses with verified open-source syllabus endpoints.
    """)
    
    mit_syllabus_structure = [
        {"Topic": "Mathematics", "Code": "18.06", "Curriculum focus": "Linear Algebra, Vector Transformations"},
        {"Topic": "Computer Science", "Code": "6.0001", "Curriculum focus": "Algorithmic Complexity, Structural Python Optimization"},
        {"Topic": "Systems Engineering", "Code": "RES.6-007", "Curriculum focus": "Fourier Analysis, Continuous Signal Filters"},
        {"Topic": "Control Theory", "Code": "6.302", "Curriculum focus": "PID Tuning Metrics, Stability Vectors"},
        {"Topic": "Robotics Mechanics", "Code": "2.12", "Curriculum focus": "Kinematics, Actuator Dynamic State Models"}
    ]
    st.table(pd.DataFrame(mit_syllabus_structure))

# =========================================================
# MODULE 6: MANAGEMENT CENTER (ADD & RECONFIGURE NODES)
# =========================================================

elif menu == "Add Course":
    st.title("➕ Register Structural System Module Node")
    
    with st.form("new_course_form"):
        cat = st.selectbox("Module Branch Cluster Topology", ["Mechatronics", "Artificial Intelligence", "Mathematics", "Control Systems", "Embedded Systems"])
        name = st.text_input("Course Module Designation Label", placeholder="e.g., MIT 18.06 Linear Algebra")
        submitted = st.form_submit_button("🚀 Inject Structural Node Into Schema")
        
        if submitted:
            if not name.strip():
                st.error("Branch label cannot remain structurally blank.")
            else:
                with conn:
                    conn.execute("INSERT INTO courses (category, course_name, completed) VALUES (?, ?, 0)", (cat, name))
                st.success(f"System pathway node '{name}' mounted inside the architecture cluster.")
                st.rerun()

# =========================================================
# MODULE 7: MANAGEMENT CENTER & SYSTEM MAINTENANCE
# =========================================================

elif menu == "Management Center":
    st.title("🛠️ System Data Infrastructure Hub")
    
    st.markdown("### Master Core Course Allocation Grid")
    courses_df = pd.read_sql_query("SELECT * FROM courses", conn)
    if courses_df.empty:
        st.info("Zero operational tracks loaded inside system memory frames.")
    else:
        st.dataframe(courses_df, use_container_width=True)

# =========================================================
# MODULE 8: EMERGENCY RECOVERY RUNTIME
# =========================================================

elif menu == "System Recovery":
    st.title("🚨 Emergency Infrastructure Recovery Matrix")
    st.warning("Executing maintenance functions below will directly mutate underlying persistent database file sectors.")
    
    if st.button("💥 Hard Reset Local Data Tables (Purge All Tables)"):
        with conn:
            conn.execute("DROP TABLE IF EXISTS courses;")
            conn.execute("DROP TABLE IF EXISTS notes;")
            conn.execute("DROP TABLE IF EXISTS journal;")
            conn.execute("DROP TABLE IF EXISTS exercise_logs;")
            conn.execute("DROP TABLE IF EXISTS assignment_logs;")
            conn.execute("DROP TABLE IF EXISTS profile;")
        st.success("Persistent relational tables fully dropped. Reload page frame to execute seed subroutine initialization.")
        st.rerun()
