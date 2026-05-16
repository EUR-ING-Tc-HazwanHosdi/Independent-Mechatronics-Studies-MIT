# =========================================================
# AIMecha Study OS - Complete Functional Unified Distribution
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

# --- TEXT SPECIFICATION EXTRACTION SYSTEM HOOKS ---
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# =========================================================
# SYSTEM ENVIRONMENT CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="AIMecha Study OS",
    page_icon="⚙️",
    layout="wide"
)

DB_NAME = "aimecha_study_os.db"

# =========================================================
# CYBERPUNK STYLING EMBED (THEMING MATRIX)
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
</style>
""", unsafe_allow_html=True)

# =========================================================
# SQLite PERSISTENT STORAGE CONNECTOR
# =========================================================

@st.cache_resource
def get_conn():
    connection = sqlite3.connect(DB_NAME, check_same_thread=False)
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection

conn = get_conn()

def init_db():
    with conn:
        cursor = conn.cursor()
        
        # Core Architecture Tables
        cursor.execute("CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, course_name TEXT NOT NULL, completed INTEGER DEFAULT 0)")
        cursor.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, note TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT, updated_at TEXT, FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, entry TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT, updated_at TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, name TEXT, bio TEXT, title TEXT, profile_img BLOB)")
        
        # Hardened Exercise Metrics Engine Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercise_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            exercise_split TEXT NOT NULL,
            load_volume REAL,
            notes TEXT
        )
        """)
        
        # Bootstrap default profile context if empty
        cursor.execute("SELECT COUNT(*) FROM profile WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO profile (id, name, bio, title) VALUES (1, 'Your Name', 'Data Science & Automation Engineer', 'Python Infrastructure Developer')")

init_db()

# =========================================================
# MULTIMODAL ENGINEERING CANVAS COMPONENT
# =========================================================

def compress_img(image_file):
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
        st.error(f"Image processing fault: {e}")
        return None

def multimodal_input(key):
    text = st.text_area("Technical Log / Implementation Documentation Context", key=f"text_input_{key}", height=120)
    c1, c2 = st.columns(2)
    with c1:
        st.caption("🎨 Interactive Blueprint Sketchpad")
        canvas = st_canvas(
            fill_color="rgba(0, 212, 255, 0.05)", 
            stroke_width=3, 
            stroke_color="#00d4ff", 
            background_color="#0e1117", 
            height=200, 
            width=450, 
            drawing_mode="freedraw", 
            key=f"canvas_component_{key}", 
            update_streamlit=True
        )
    with c2:
        st.caption("🖼️ Data Asset / Reference Spec Snapshot")
        img = st.file_uploader("Upload Engineering Frame Attachment", type=["png", "jpg", "jpeg"], key=f"img_upload_{key}")

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
                st.error(f"Sketch compression anomaly: {e}")

    img_blob = compress_img(img) if img else None
    return text, sketch_b64, img_blob

# =========================================================
# APPLICATION CONTROL SIDEBAR
# =========================================================

st.sidebar.title("⚙️ AIMecha OS")
menu = st.sidebar.radio(
    "System Sub-Interface Navigation", 
    ["Dashboard", "Courses", "Journal", "Professional CV", "MIT Learning Hub", "Management Center", "Add Course", "System Recovery"]
)

# =========================================================
# TAB 1: INTEGRATED CORE METRICS & EXERCISE TELESCOPE
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ Telemetry Analytics & Performance Dashboard")
    
    courses_df = pd.read_sql_query("SELECT * FROM courses", conn)
    notes_count = pd.read_sql_query("SELECT COUNT(*) FROM notes", conn).iloc[0,0]
    journal_count = pd.read_sql_query("SELECT COUNT(*) FROM journal", conn).iloc[0,0]
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Modules Running", len(courses_df))
    completion = (courses_df['completed'].mean() * 100) if not courses_df.empty else 0
    c2.metric("Curriculum Progress Track", f"{completion:.1f}%")
    c3.metric("Committed Study Notes", notes_count)
    c4.metric("Chronological Journal Entries", journal_count)

    st.divider()

    # --- UPGRADED WORKOUT TELEMETRY HUB ---
    st.subheader("🏋️ Physical Performance & Exercise Log Engine")
    col_upload, col_manual = st.columns([1, 1])
    
    with col_upload:
        st.markdown("**Exercise Matrix Input Pipeline (.CSV / .PDF)**")
        exercise_file = st.file_uploader("Drop workout sheets directly into processing buffer", type=["csv", "pdf"], key="exercise_file_drop")
        
        if exercise_file is not None:
            filename = exercise_file.name.lower()
            
            if filename.endswith('.csv'):
                try:
                    uploaded_df = pd.read_csv(exercise_file)
                    required_cols = ["date", "exercise_split", "load_volume", "notes"]
                    if all(col in uploaded_df.columns for col in required_cols):
                        if st.button("🚀 Commit CSV Records to Storage Array"):
                            with conn:
                                for _, row in uploaded_df.iterrows():
                                    conn.execute("INSERT INTO exercise_logs (date, exercise_split, load_volume, notes) VALUES (?, ?, ?, ?)", (str(row['date']), str(row['exercise_split']), float(row['load_volume']), str(row['notes'])))
                            st.success("CSV dataset matrix compiled into local tables!"); st.rerun()
                    else:
                        st.error(f"Invalid layout format. System demands headers: {required_cols}")
                except Exception as e:
                    st.error(f"CSV Parse Subroutine Error: {e}")
            
            elif filename.endswith('.pdf'):
                if fitz is None:
                    st.error("Missing Parser Hooks: Run `pip install pymupdf` inside your terminal to handle PDF layers.")
                else:
                    try:
                        pdf_bytes = exercise_file.read()
                        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                        full_extracted_text = "".join([page.get_text() for page in doc])
                        
                        st.info("📄 Document character array mapped! Confirm or overwrite metrics before tracking block emission:")
                        st.text_area("Extracted Layout Preview Box", value=full_extracted_text, height=120, disabled=True)
                        
                        with st.form("pdf_extraction_verification_form"):
                            pdf_date = st.date_input("Target File Extraction Date", datetime.now())
                            pdf_split = st.selectbox("Extracted Split Target", ["Push (Chest/Triceps)", "Pull (Back/Biceps)", "Legs (Anterior/Posterior)", "Core & Cardio Conditioning", "Full Body Synthesis"])
                            pdf_vol = st.number_input("Extracted Cumulative Training Mass (kg)", min_value=0.0, step=0.5)
                            pdf_notes = st.text_area("Filtered Text Context Summary", value=full_extracted_text[:400])
                            
                            if st.form_submit_button("💾 Write PDF Derived Record"):
                                with conn:
                                    conn.execute("INSERT INTO exercise_logs (date, exercise_split, load_volume, notes) VALUES (?, ?, ?, ?)", (pdf_date.strftime("%Y-%m-%d"), pdf_split, pdf_vol, pdf_notes))
                                st.success("PDF metrics safely written to persistence storage layers."); st.rerun()
                    except Exception as e:
                        st.error(f"PDF Extraction Routine Failure: {e}")

    with col_manual:
        st.markdown("**Manual Core Metric Intercept**")
        with st.popover("➕ Direct Entry Panel"):
            ex_date = st.date_input("Training Timestamp Date", datetime.now())
            ex_split = st.selectbox("Target Splits Block", ["Push (Chest/Triceps)", "Pull (Back/Biceps)", "Legs (Anterior/Posterior)", "Core & Cardio Conditioning", "Full Body Synthesis"])
            ex_vol = st.number_input("Calculated Load Volume Total (kg)", min_value=0.0, step=0.5)
            ex_notes = st.text_input("Workout Evaluation Notes / Context", placeholder="Targeted progressive overload sets successfully...")
            
            if st.button("💾 Append Node Record"):
                with conn:
                    conn.execute("INSERT INTO exercise_logs (date, exercise_split, load_volume, notes) VALUES (?, ?, ?, ?)", (ex_date.strftime("%Y-%m-%d"), ex_split, ex_vol, ex_notes))
                st.success("Manual metrics entry locked inside system registers."); st.rerun()

    st.markdown("### Master Physical Optimization Records Workspace")
    db_exercise_logs = pd.read_sql_query("SELECT * FROM exercise_logs ORDER BY date DESC, id DESC", conn)
    
    if db_exercise_logs.empty:
        st.info("No exercise logs committed inside the runtime database environment.")
    else:
        st.dataframe(db_exercise_logs, use_container_width=True, hide_index=True)
        
        c1, c2 = st.columns(2)
        with c1.popover("🗑️ Purge Targeted Record Node"):
            target_id = st.number_input("Target Node Log ID to Erase", min_value=1, step=1)
            if st.button("🚨 Purge Selected Entry"):
                with conn: conn.execute("DELETE FROM exercise_logs WHERE id=?", (target_id,))
                st.success(f"Log entry node {target_id} decoupled."); st.rerun()
        with c2.popover("💥 Structural Wipe Operations"):
            if st.button("🚨 CONFIRM DATA RESET"):
                with conn: conn.execute("DELETE FROM exercise_logs")
                st.success("All logging records completely cleared from memory banks."); st.rerun()

# =========================================================
# TAB 2: ACTIVE EDUCATION COURSE MODULE MANAGEMENT HUB
# =========================================================

elif menu == "Courses":
    st.title("📚 Registered Engineering Study Modules")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    
    if courses.empty:
        st.info("No modules initialized. Please click 'Add Course' in the control sidebar menu.")
    else:
        search_note = st.text_input("🔍 Filter Notes Workspace By Phrase Key")
        for _, row in courses.iterrows():
            status_tag = "✅ Complete" if row['completed'] else "⏳ Evaluation Phase"
            with st.expander(f"📦 {row['course_name']} [{row['category']}] — {status_tag}"):
                
                st.subheader("Add Course Log / Documentation Entry")
                txt, sk, im = multimodal_input(f"course_module_entry_{row['id']}")
                
                if st.button("🚀 Commit Entry to Module Stack", key=f"btn_n_{row['id']}"):
                    if txt.strip() == "" and sk is None and im is None:
                        st.error("Cannot commit empty workspace structures.")
                    else:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                        with conn:
                            conn.execute("INSERT INTO notes (course_id, note, sketch_data, image_blob, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (row['id'], txt, sk, im, timestamp, timestamp))
                        st.success("Technical log appended onto module matrix stack!"); st.rerun()
                
                st.divider()
                
                notes_df = pd.read_sql_query("SELECT * FROM notes WHERE course_id=? AND (note LIKE ? OR note IS NULL) ORDER BY id DESC", conn, params=(row['id'], f"%{search_note}%"))
                for _, note in notes_df.iterrows():
                    with st.container(border=True):
                        st.caption(f"📅 Logged: {note['created_at']}")
                        if note['note']: st.write(note['note'])
                        n1, n2 = st.columns(2)
                        if note['sketch_data']:
                            try: n1.image(base64.b64decode(note['sketch_data']), caption="Vector Blueprint Sketch")
                            except Exception: pass
                        if note['image_blob']: n2.image(note['image_blob'], caption="Reference Spec Attachment")

# =========================================================
# TAB 3: SYSTEM LOG CHRONOLOGICAL JOURNAL STREAM
# =========================================================

elif menu == "Journal":
    st.title("📓 Chronological System Log Journal")
    
    with st.expander("➕ Open New Chronological System Entry Channel", expanded=True):
        j_title = st.text_input("Log Diagnostic Target Title", "Daily System Engineering Iteration Report")
        txt, sk, im = multimodal_input("journal_master_channel")
        
        if st.button("🚀 Push Log Entry to Master Stream", key="commit_journal_btn"):
            if txt.strip() == "" and sk is None and im is None:
                st.error("Cannot write an empty configuration matrix trace.")
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                with conn:
                    conn.execute("INSERT INTO journal (title, entry, sketch_data, image_blob, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (j_title, txt, sk, im, timestamp, timestamp))
                st.success("System journal stream updated successfully!"); st.rerun()
            
    st.divider()
    
    journal_df = pd.read_sql_query("SELECT * FROM journal ORDER BY id DESC", conn)
    for _, j in journal_df.iterrows():
        with st.container(border=True):
            st.subheader(j['title'])
            st.caption(f"🕒 Node Creation Metric: {j['created_at']}")
            if j['entry']: st.write(j['entry'])
            jc1, jc2 = st.columns(2)
            if j['sketch_data']:
                try: jc1.image(base64.b64decode(j['sketch_data']), caption="Diagnostic Workspace Sketch")
                except Exception: pass
            if j['image_blob']: jc2.image(j['image_blob'], caption="Hardware Component Reference Photo")

# =========================================================
# TAB 4: PROFILE COMPILATION CARD INTERFACE
# =========================================================

elif menu == "Professional CV":
    st.title("🗂️ Engineering Portfolio Identity Engine")
    profile = pd.read_sql_query("SELECT * FROM profile WHERE id = 1", conn).iloc[0]
    
    st.markdown(f"""
    <div class="header-card">
        <h2>{profile["name"]}</h2>
        <h4 style="color: #00d4ff;">{profile["title"]}</h4>
        <p style="margin-top:15px; color:#cbd5e1; font-size: 1.1rem; line-height: 1.6;">{profile["bio"]}</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("📝 Modify System Operator Credentials"):
        with st.form("profile_adjustment_form"):
            new_name = st.text_input("Operator Name Designation", value=profile["name"])
            new_title = st.text_input("System Professional Title assignment", value=profile["title"])
            new_bio = st.text_area("Technical Profile Overview Meta Summary", value=profile["bio"])
            
            if st.form_submit_button("💾 Save Operator Profile Layout Updates"):
                with conn:
                    conn.execute("UPDATE profile SET name=?, title=?, bio=? WHERE id=1", (new_name, new_title, new_bio))
                st.success("Operator profile layout properties verified and recompiled."); st.rerun()

# =========================================================
# TAB 5: TECHNICAL SYLLABUS DIRECTORY REFERENCE
# =========================================================

elif menu == "MIT Learning Hub":
    st.title("🎓 MIT OpenCourseWare Core Tracking Matrix")
    st.markdown("Use this reference matrix to anchor data processing models, algorithm selections, and software system benchmarks.")
    
    mit_syllabus_structure = [
        {"Topic": "Mathematics", "Code": "18.06", "Curriculum focus": "Linear Algebra, Vector Transformations, Matrix Decompositions"},
        {"Topic": "Computer Science", "Code": "6.0001", "Curriculum focus": "Algorithmic Complexity, Structural Python Optimization, Object Models"},
        {"Topic": "Systems Engineering", "Code": "RES.6-007", "Curriculum focus": "Fourier Analysis, Continuous Signal Filters, Sampling Laws"},
        {"Topic": "Control Theory", "Code": "6.302", "Curriculum focus": "PID Tuning Metrics, State-Space Models, Root Locus Stability"},
        {"Topic": "Hardware & Robotics", "Code": "2.12", "Curriculum focus": "Kinematic Transforms, Spatial Jacobians, Dynamics Analysis"}
    ]
    st.table(pd.DataFrame(mit_syllabus_structure))

# =========================================================
# TAB 6: COMPLETE MODULE INVENTORY LIST WITH INLINE STATS
# =========================================================

elif menu == "Management Center":
    st.title("🎛️ Curriculum Management Operations Center")
    st.markdown("Review running courses, toggle milestone execution criteria, or delete orphaned infrastructure records.")
    
    c_list = pd.read_sql_query("SELECT id, category, course_name, completed FROM courses ORDER BY category, id DESC", conn)
    
    if c_list.empty:
        st.info("System registry maps show zero active tracking cells.")
    else:
        for idx, row in c_list.iterrows():
            col_info, col_toggle, col_drop = st.columns([5, 2, 1])
            
            status_text = "🟢 COMPLETE" if row['completed'] else "🟡 ACTIVE LIFECYCLE"
            col_info.markdown(f"**[{row['category']}]** {row['course_name']} &mdash; *{status_text}*")
            
            toggle_label = "Mark Active" if row['completed'] else "Mark Complete"
            if col_toggle.button(toggle_label, key=f"tgl_{row['id']}"):
                new_state = 0 if row['completed'] else 1
                with conn:
                    conn.execute("UPDATE courses SET completed=? WHERE id=?", (new_state, row['id']))
                st.rerun()
                
            if col_drop.button("🗑️", key=f"drp_{row['id']}"):
                with conn:
                    conn.execute("DELETE FROM courses WHERE id=?", (row['id'],))
                st.success("Module removed."); st.rerun()

# =========================================================
# TAB 7: PIPELINE SOURCE FOR INJECTING NOVEL TRACKS
# =========================================================

elif menu == "Add Course":
    st.title("➕ Track New Educational Engineering Module")
    st.markdown("Register standard lecture configurations to monitor note frameworks and progress vectors.")
    
    with st.form("course_addition_form", clear_on_submit=True):
        c_name = st.text_input("Module Tracking Nomenclature Name (e.g., CS50P, Data Science Foundations)")
        c_cat = st.selectbox("Operational Classification Category", ["Programming", "Artificial Intelligence", "Mechatronics", "Electronics", "Control Systems", "Robotics", "Computer Vision", "Embedded Systems"])
        
        if st.form_submit_button("🚀 Inject Course Module into System Array"):
            if c_name.strip() == "":
                st.error("A validation string definition is required to run initialization parameters.")
            else:
                with conn: 
                    conn.execute("INSERT INTO courses (category, course_name, completed) VALUES (?, ?, 0)", (c_cat, c_name.strip()))
                st.success(f"Integrated '{c_name}' cleanly into operational tracking array.")

# =========================================================
# TAB 8: ENCAPSULATED RECOVERY HUB FOR COLD DATA STORAGE
# =========================================================

elif menu == "System Recovery":
    st.title("🛠️ System Resiliency & Recovery Protocols")
    st.markdown("Compile local state repositories into a portable payload asset or safely clear application database structures.")
    
    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.subheader("📦 Database State Compilation")
        st.write("Package the local SQLite file into an exportable asset container to preserve tracking telemetry.")
        try:
            with open(DB_NAME, "rb") as f: 
                db_bytes = f.read()
            st.download_button(label="💾 Download Raw Database Asset", data=db_bytes, file_name="aimecha_study_os_backup.db", mime="application/x-sqlite3")
        except Exception as e:
            st.error(f"Failed to load target database matrix asset: {e}")
            
    with c2.container(border=True):
        st.subheader("🚨 Global Clear Options")
        st.write("Erase application tables entirely to clear old testing parameters and rebuild fresh database tracking cells.")
        
        if st.button("💥 Wipe Entire Platform Storage System", key="global_hard_wipe_btn"):
            with conn:
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS courses")
                cursor.execute("DROP TABLE IF EXISTS notes")
                cursor.execute("DROP TABLE IF EXISTS journal")
                cursor.execute("DROP TABLE IF EXISTS profile")
                cursor.execute("DROP TABLE IF EXISTS exercise_logs")
            st.warning("Database layers completely cleared. Re-initializing blank system assets..."); init_db(); st.rerun()
