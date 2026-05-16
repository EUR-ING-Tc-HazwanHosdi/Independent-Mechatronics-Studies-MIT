# =========================================================
# AIMecha Study OS - Full Production Build (Fixed Sketchpads)
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
    # Process canvas layer vectors safely
    if canvas is not None and canvas.image_data is not None:
        arr = canvas.image_data.astype("uint8")
        # Evaluate if alpha channels have concrete drawn lines
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
    # EXERCISE TELEMETRY SUB-INTERFACE
    # =========================================================
    st.subheader("🏋️ Physical Performance & Exercise Log Engine")
    
    col_upload, col_manual = st.columns([1, 1])
    
    with col_upload:
        st.markdown("**Batch CSV Exercise Log Upload Pipeline**")
        exercise_csv = st.file_uploader("Upload Workout Metrics Dataset (.csv)", type=["csv"], key="exercise_csv_drop")
        
        if exercise_csv is not None:
            try:
                uploaded_df = pd.read_csv(exercise_csv)
                required_cols = ["date", "exercise_split", "load_volume", "notes"]
                
                if all(col in uploaded_df.columns for col in required_cols):
                    if st.button("🚀 Commit File Data Arrays to DB"):
                        with conn:
                            for _, row in uploaded_df.iterrows():
                                conn.execute("""
                                    INSERT INTO exercise_logs (date, exercise_split, load_volume, notes)
                                    VALUES (?, ?, ?, ?)
                                """, (str(row['date']), str(row['exercise_split']), float(row['load_volume']), str(row['notes'])))
                        st.success("Exercise performance history records streamed successfully!")
                        st.rerun()
                else:
                    st.error(f"Data schema layout error. Ensure document contains headers: {required_cols}")
            except Exception as e:
                st.error(f"CSV Parse Subroutine Fault: {e}")

    with col_manual:
        st.markdown("**Manual Core Metric Intercept**")
        with st.popover("➕ Log Single Workout Instance"):
            ex_date = st.date_input("Training Target Date", datetime.now())
            ex_split = st.selectbox("Workout Focus Split Track", ["Push (Chest/Triceps)", "Pull (Back/Biceps)", "Legs (Anterior/Posterior)", "Core & Cardio Conditioning", "Full Body Synthesis"])
            ex_vol = st.number_input("Calculated Load Volume Total (kg)", min_value=0.0, step=0.5)
            ex_notes = st.text_input("Log Diagnostic Notes/Soreness Metrics", placeholder="Completed all active working sets to muscular failure...")
            
            if st.button("💾 Append Log Node"):
                with conn:
                    conn.execute("""
                        INSERT INTO exercise_logs (date, exercise_split, load_volume, notes)
                        VALUES (?, ?, ?, ?)
                    """, (ex_date.strftime("%Y-%m-%d"), ex_split, ex_vol, ex_notes))
                st.success("Manual workout node logged.")
                st.rerun()

    # Dynamic Grid Display
    st.markdown("### Master Physical Training Log Workspace")
    db_exercise_logs = pd.read_sql_query("SELECT * FROM exercise_logs ORDER BY date DESC, id DESC", conn)
    
    if db_exercise_logs.empty:
        st.info("No exercise logs committed inside the runtime data frame registry.")
    else:
        st.dataframe(db_exercise_logs[["id", "date", "exercise_split", "load_volume", "notes"]], use_container_width=True, hide_index=True)
        
        with st.popover("🗑️ Purge Workout Diagnostic Entries"):
            st.warning("Action will clear log arrays. Choose target parameters below.")
            target_id = st.number_input("Target Log ID to Erase", min_value=1, step=1)
            if st.button("🚨 Purge Selected Entry", key="single_ex_purge_btn"):
                with conn:
                    conn.execute("DELETE FROM exercise_logs WHERE id=?", (target_id,))
                st.success(f"Log entry node {target_id} decoupled.")
                st.rerun()
                
            if st.button("💥 Structural Zero Wipe All Data Records", key="global_ex_wipe_btn"):
                with conn:
                    conn.execute("DELETE FROM exercise_logs")
                st.success("Exercise records tables dropped and reset.")
                st.rerun()

# =========================================================
# MODULE 2: DYNAMIC ENGINEERING STUDY MODULES (COURSES)
# =========================================================

elif menu == "Courses":
    st.title("📚 Engineering Study Modules")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    
    if courses.empty:
        st.info("No educational modules registered inside the local database environment. Head over to 'Add Course' to get started.")
    else:
        search_note = st.text_input("🔍 Filter Notes Workspace By Phrase Key", placeholder="Type keywords here...")
        
        for _, row in courses.iterrows():
            status_tag = "✅ Done" if row['completed'] else "⏳ In Progress"
            with st.expander(f"⚙️ {row['course_name']} [{row['category']}] — {status_tag}"):
                
                m1, m2, m3 = st.columns([2, 2, 3])
                with m1:
                    with st.popover("✏️ Modify Module Specs"):
                        new_name = st.text_input("Edit Name", value=row['course_name'], key=f"nm_{row['id']}")
                        categories = ["Programming", "Artificial Intelligence", "Mechatronics", "Electronics", "Control Systems", "Robotics", "Computer Vision", "Embedded Systems"]
                        new_cat = st.selectbox("Edit Category", categories, index=categories.index(row['category']) if row['category'] in categories else 0, key=f"ct_{row['id']}")
                        
                        if st.button("💾 Apply Modifications", key=f"sv_{row['id']}"):
                            with conn:
                                conn.execute("UPDATE courses SET course_name=?, category=? WHERE id=?", (new_name, new_cat, row['id']))
                            st.success("Changes successfully persisted!")
                            st.rerun()
                
                with m2:
                    with st.popover("🗑️ Decommission Module"):
                        st.error("Warning: Purging this module drops all corresponding child engineering records and telemetry logs.")
                        if st.button("🚨 Confirm Full Purge", key=f"del_c_{row['id']}"):
                            with conn:
                                conn.execute("DELETE FROM notes WHERE course_id=?", (row['id'],))
                                conn.execute("DELETE FROM courses WHERE id=?", (row['id'],))
                            st.success("Module systematically scrubbed.")
                            st.rerun()
                
                with m3:
                    completed = st.checkbox("Mark Module Workload Complete", value=bool(row['completed']), key=f"chk_{row['id']}")
                    if completed != bool(row['completed']):
                        with conn:
                            conn.execute("UPDATE courses SET completed=? WHERE id=?", (int(completed), row['id']))
                        st.rerun()
                
                st.divider()
                
                # Add Note Input Field with Linked Sketchpad
                st.subheader("Add Course Log / Documentation Entry")
                txt, sk, im = multimodal_input(f"course_module_entry_{row['id']}")
                
                if st.button("🚀 Commit Entry to Module Stack", key=f"btn_n_{row['id']}"):
                    if txt.strip() == "" and sk is None and im is None:
                        st.error("Cannot commit an empty modular log entry.")
                    else:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                        with conn:
                            conn.execute("""
                            INSERT INTO notes (course_id, note, sketch_data, image_blob, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """, (row['id'], txt, sk, im, timestamp, timestamp))
                        st.success("Entry logged successfully!")
                        st.rerun()
                
                st.divider()
                
                # Render Historical Module Notes & Drawings
                notes_df = pd.read_sql_query("""
                    SELECT * FROM notes 
                    WHERE course_id=? AND (note LIKE ? OR note IS NULL)
                    ORDER BY id DESC
                """, conn, params=(row['id'], f"%{search_note}%"))
                
                for _, note in notes_df.iterrows():
                    with st.container(border=True):
                        t1, t2, t3 = st.columns([6, 1, 1])
                        t1.caption(f"📅 Logged: {note['created_at']} | Sync: {note['updated_at'] or 'Initial'}")
                        
                        with t2:
                            with st.popover("✏️"):
                                edit_txt = st.text_area("Update Note Content", value=note['note'] or "", key=f"ed_nt_{note['id']}")
                                if st.button("💾 Update Text", key=f"up_nt_{note['id']}"):
                                    with conn:
                                        conn.execute("UPDATE notes SET note=?, updated_at=? WHERE id=?", (edit_txt, datetime.now().strftime("%Y-%m-%d %H:%M"), note['id']))
                                    st.rerun()
                        
                        with t3:
                            if st.button("🗑️", key=f"del_nt_{note['id']}"):
                                with conn:
                                    conn.execute("DELETE FROM notes WHERE id=?", (note['id'],))
                                st.rerun()
                        
                        if note['note']:
                            st.write(note['note'])
                            
                        n1, n2 = st.columns(2)
                        if note['sketch_data']:
                            try:
                                n1.image(base64.b64decode(note['sketch_data']), caption="Vector Sketch Blueprint")
                            except Exception:
                                pass
                        if note['image_blob']:
                            n2.image(note['image_blob'], caption="Reference Spec Attachment")

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
            jh1, jh2, jh3 = st.columns([6, 1, 1])
            jh1.subheader(j['title'])
            
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
        {"Topic": "Control Theory", "Code": "6.302", "Curriculum focus": "PID Tuning Metrics, State-Space Models"},
        {"Topic": "Hardware & Robotics", "Code": "2.12", "Curriculum focus": "Kinematic Transforms, Spatial Jacobians"}
    ]
    st.table(pd.DataFrame(mit_syllabus_structure))

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
# MODULE 8: SYSTEM RESILIENCY RECOVERY PROTOCOLS
# =========================================================

elif menu == "System Recovery":
    st.title("🛠️ System Resiliency & Recovery Protocols")
    
    st.warning("Executing a recovery action direct-overwrites or drops system infrastructure assets.")
    
    b1, b2 = st.columns(2)
    
    with b1:
        st.subheader("Data Export Subroutine")
        if st.button("📦 Execute Local DB Compilation"):
            try:
                with open(DB_NAME, "rb") as f:
                    db_bytes = f.read()
                st.download_button(
                    label="💾 Download Raw Database Asset",
                    data=db_bytes,
                    file_name=f"aimecha_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                    mime="application/x-sqlite3"
                )
            except Exception as e:
                st.error(f"Backup serialization breakdown: {e}")
                
    with b2:
        st.subheader("System Restoration Pipeline")
        restore_file = st.file_uploader("Drop Backup File for System Injection (.db)", type=["db"])
        if restore_file is not None:
            if st.button("🚨 Overwrite System Core Matrix"):
                try:
                    conn.close()
                    with open(DB_NAME, "wb") as f:
                        f.write(restore_file.getbuffer())
                    st.cache_resource.clear()
                    st.success("System architecture restoration successful. Reloading app processes...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Restoration pipeline failure: {e}")
