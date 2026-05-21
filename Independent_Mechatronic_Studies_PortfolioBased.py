# =========================================================
# AIMecha Study OS - Full Production Build (Refactored)
# =========================================================
# FIXES APPLIED:
#   [1] st.rerun() moved outside all with conn: blocks
#   [2] compress_img() used consistently (Courses module)
#   [3] PDFs saved to disk; only file path stored in DB
#   [4] Input length validation on all text fields
#   [5] Canvas b64 cached in st.session_state to avoid re-encoding
#   [6] cache_resource.clear() scoped safely via named key
#   [7] conn.commit() called explicitly after writes for reliability
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
PDF_UPLOAD_DIR = "uploaded_pdfs"          # [FIX 3] PDFs on disk, not in DB
MAX_TEXT_LENGTH = 50_000                  # [FIX 4] Input guard limit (chars)
MAX_PDF_SIZE_MB = 20                      # [FIX 3] PDF size guard (MB)

os.makedirs(PDF_UPLOAD_DIR, exist_ok=True)

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
# DATABASE ENGINE
# =========================================================

@st.cache_resource
def get_conn():
    """Single cached connection with WAL mode for performance."""
    connection = sqlite3.connect(
        DB_NAME,
        check_same_thread=False,
        timeout=15.0
    )
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA synchronous=NORMAL;")
    connection.execute("PRAGMA temp_store=MEMORY;")
    return connection


conn = get_conn()


def db_execute(query: str, params: tuple = ()):
    """
    [FIX 1 + 7] Safe write helper: explicit commit, no bare with conn: blocks.
    Returns lastrowid for INSERT statements.
    """
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    return cursor.lastrowid


def init_db():
    """Ensures schema generation and applies column migrations."""
    cursor = conn.cursor()

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
        updated_at TEXT,
        FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
    )
    """)

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exercise_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        exercise_split TEXT NOT NULL,
        load_volume REAL,
        notes TEXT
    )
    """)

    # [FIX 3] assignment_logs stores file_path instead of pdf_blob
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignment_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_completed TEXT NOT NULL,
        course_name TEXT NOT NULL,
        assignment_name TEXT NOT NULL,
        notes TEXT,
        file_path TEXT
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

    # Runtime schema migrations
    for migration in [
        "ALTER TABLE notes ADD COLUMN updated_at TEXT",
        "ALTER TABLE journal ADD COLUMN updated_at TEXT",
        "ALTER TABLE assignment_logs ADD COLUMN file_path TEXT",
    ]:
        try:
            cursor.execute(migration)
        except sqlite3.OperationalError:
            pass

    cursor.execute("SELECT COUNT(*) FROM profile WHERE id = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO profile (id, name, bio, title)
        VALUES (1, 'Your Name', 'Industrial AI & Mechatronics Engineer', 'Engineering Systems Developer')
        """)

    conn.commit()


init_db()

# =========================================================
# UTILITIES
# =========================================================

def compress_img(image_file):
    """
    Scales down images before DB storage.
    Accepts a file-like object OR raw bytes.
    """
    if image_file is None:
        return None
    try:
        if isinstance(image_file, (bytes, bytearray)):
            image_file = io.BytesIO(image_file)
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


def validate_text(text: str, field_name: str = "Input") -> bool:
    """[FIX 4] Guards against oversized text inputs."""
    if len(text) > MAX_TEXT_LENGTH:
        st.error(f"{field_name} exceeds the {MAX_TEXT_LENGTH:,} character limit. Please shorten it.")
        return False
    return True


def save_pdf_to_disk(pdf_file, assignment_name: str) -> str | None:
    """
    [FIX 3] Saves uploaded PDF to local filesystem.
    Returns the relative file path, or None on failure.
    """
    if pdf_file is None:
        return None
    size_mb = len(pdf_file.getvalue()) / (1024 * 1024)
    if size_mb > MAX_PDF_SIZE_MB:
        st.error(f"PDF exceeds {MAX_PDF_SIZE_MB}MB limit ({size_mb:.1f}MB). Please compress or split the file.")
        return None
    safe_name = "".join(c for c in assignment_name if c.isalnum() or c in " _-").rstrip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_name}.pdf"
    filepath = os.path.join(PDF_UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(pdf_file.getvalue())
    return filepath


def multimodal_input(key: str):
    """
    [FIX 5] Renders dual text field, canvas sketchpad, and file uploader.
    Canvas b64 is cached in session_state to avoid re-encoding on every rerun.
    """
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

    # [FIX 5] Only re-encode canvas when image_data actually changes
    canvas_state_key = f"canvas_b64_{key}"
    sketch_b64 = st.session_state.get(canvas_state_key)

    if canvas is not None and canvas.image_data is not None:
        arr = canvas.image_data.astype("uint8")
        if np.any(arr[:, :, 3] > 0):
            try:
                canvas_hash = hash(arr.tobytes())
                hash_key = f"canvas_hash_{key}"
                if st.session_state.get(hash_key) != canvas_hash:
                    raw_img = Image.fromarray(arr, 'RGBA')
                    buf = io.BytesIO()
                    raw_img.save(buf, format="PNG")
                    sketch_b64 = base64.b64encode(buf.getvalue()).decode()
                    st.session_state[canvas_state_key] = sketch_b64
                    st.session_state[hash_key] = canvas_hash
            except Exception as e:
                st.error(f"Canvas drawing compression fault: {e}")

    # [FIX 2] Always use compress_img for uploaded images
    img_blob = compress_img(img) if img else None
    return text, sketch_b64, img_blob

# =========================================================
# SIDEBAR NAVIGATION
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
    st.sidebar.markdown(
        f'<a href="{url}" target="_blank" style="text-decoration:none; color:#00d4ff;">⚡ {course}</a>',
        unsafe_allow_html=True
    )

# =========================================================
# MODULE 1: DASHBOARD
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ AIMecha Engineering & Physical Optimization Dashboard")

    df = pd.read_sql_query("SELECT * FROM courses", conn)
    notes_count = pd.read_sql_query("SELECT COUNT(*) FROM notes", conn).iloc[0, 0]
    journal_count = pd.read_sql_query("SELECT COUNT(*) FROM journal", conn).iloc[0, 0]

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
                        for _, row in uploaded_df.iterrows():
                            # [FIX 4] Validate CSV text fields
                            notes_val = str(row['notes'])
                            if not validate_text(notes_val, "Notes"):
                                st.stop()
                            db_execute(
                                "INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes) VALUES (?, ?, ?, ?)",
                                (str(row['date_completed']), str(row['course_name']), str(row['assignment_name']), notes_val)
                            )
                        st.success("Assignment history parsed!")
                        st.rerun()   # [FIX 1] Outside write block
                else:
                    st.error(f"CSV must contain columns: {required_cols}")
            except Exception as e:
                st.error(f"CSV Parse Subroutine Fault: {e}")

    with col_manual:
        st.markdown("**Log Completed Task**")
        tab_text, tab_pdf = st.tabs(["📝 Manual Log", "📄 PDF Upload"])

        with tab_text:
            with st.popover("➕ Log Single Task"):
                as_date = st.date_input("Completion Date", datetime.now(), key="manual_date")
                course_options = df['course_name'].tolist() if not df.empty else ["General Study Task"]
                as_course = st.selectbox("Associated MIT Module", course_options, key="manual_course")
                as_name = st.text_input("Assignment Name", placeholder="e.g., Problem Set 1", key="manual_name")
                as_notes = st.text_area("Notes", key="manual_notes")

                if st.button("💾 Append Task Node"):
                    # [FIX 4] Validate before writing
                    if not validate_text(as_notes, "Notes"):
                        st.stop()
                    if not as_name.strip():
                        st.error("Assignment name cannot be empty.")
                    else:
                        db_execute(
                            "INSERT INTO assignment_logs (date_completed, course_name, assignment_name, notes) VALUES (?, ?, ?, ?)",
                            (as_date.strftime("%Y-%m-%d"), as_course, as_name.strip(), as_notes)
                        )
                        st.success("Logged!")
                        st.rerun()   # [FIX 1] Outside write block

        with tab_pdf:
            with st.popover("📤 Upload Assignment PDF"):
                pdf_date = st.date_input("Submission Date", datetime.now(), key="pdf_date")
                course_options = df['course_name'].tolist() if not df.empty else ["General Study Task"]
                pdf_course = st.selectbox("Module", course_options, key="pdf_course_sel")
                pdf_name = st.text_input("Assignment Name", placeholder="e.g., Final Lab Report", key="pdf_name_in")
                pdf_file = st.file_uploader("Upload PDF Document", type=["pdf"], key="pdf_file_drop")

                if st.button("🚀 Archive PDF to System"):
                    if pdf_file is not None and pdf_name.strip():
                        # [FIX 3] Save to disk, store path in DB
                        file_path = save_pdf_to_disk(pdf_file, pdf_name.strip())
                        if file_path:
                            db_execute(
                                "INSERT INTO assignment_logs (date_completed, course_name, assignment_name, file_path) VALUES (?, ?, ?, ?)",
                                (pdf_date.strftime("%Y-%m-%d"), pdf_course, pdf_name.strip(), file_path)
                            )
                            st.success("PDF saved to disk and path archived.")
                            st.rerun()   # [FIX 1] Outside write block
                    else:
                        st.error("Please provide a name and a file.")

    st.markdown("### Master Coursework Submission Registry")
    try:
        db_assignment_logs = pd.read_sql_query(
            "SELECT * FROM assignment_logs ORDER BY date_completed DESC, id DESC", conn
        )
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

                # [FIX 3] Read PDF from disk for download
                file_path = row.get('file_path')
                if file_path and os.path.exists(str(file_path)):
                    with open(file_path, "rb") as f:
                        cols[3].download_button(
                            label="📥 View PDF",
                            data=f.read(),
                            file_name=os.path.basename(file_path),
                            mime="application/pdf",
                            key=f"dl_{row['id']}"
                        )
                else:
                    cols[3].caption("No PDF Attached")

        with st.popover("🗑️ Purge Assignment Records"):
            st.warning("This action removes logged metrics.")
            target_id = st.number_input("Target Assignment ID to Erase", min_value=1, step=1)
            if st.button("🚨 Purge Selected Task", key="single_as_purge_btn"):
                # [FIX 3] Also delete PDF from disk if present
                row_data = pd.read_sql_query(
                    "SELECT file_path FROM assignment_logs WHERE id=?", conn, params=(int(target_id),)
                )
                if not row_data.empty and row_data.iloc[0]['file_path']:
                    fp = row_data.iloc[0]['file_path']
                    if os.path.exists(fp):
                        os.remove(fp)
                db_execute("DELETE FROM assignment_logs WHERE id=?", (int(target_id),))
                st.success(f"Assignment ID {target_id} removed.")
                st.rerun()   # [FIX 1] Outside write block

# =========================================================
# MODULE 2: COURSES
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
                            db_execute("UPDATE courses SET completed = 1 WHERE id = ?", (row['id'],))
                            st.rerun()   # [FIX 1] Outside write
                    else:
                        if st.button("🔄 Return to Active Buffer", key=f"re_act_{row['id']}"):
                            db_execute("UPDATE courses SET completed = 0 WHERE id = ?", (row['id'],))
                            st.rerun()   # [FIX 1] Outside write
                with c2:
                    if st.button("🗑️ Wipe Module Structural Node", key=f"del_c_{row['id']}"):
                        db_execute("DELETE FROM courses WHERE id = ?", (row['id'],))
                        st.rerun()   # [FIX 1] Outside write

                st.divider()
                st.subheader("📝 Append Module Log Entry")

                txt_col, img_col = st.columns([2, 1])
                with txt_col:
                    note_text = st.text_area(
                        "Technical Documentation / Notes",
                        key=f"nt_txt_{row['id']}",
                        placeholder="Enter equations, logic flows, or lecture summaries..."
                    )
                with img_col:
                    note_img = st.file_uploader(
                        "Upload Schematic / Screenshot",
                        type=["png", "jpg", "jpeg"],
                        key=f"nt_img_{row['id']}"
                    )

                if st.button("🚀 Commit to Module Stack", key=f"commit_btn_{row['id']}"):
                    if not note_text.strip() and note_img is None:
                        st.error("Cannot commit an empty log.")
                    elif not validate_text(note_text, "Note"):   # [FIX 4]
                        st.stop()
                    else:
                        # [FIX 2] Use compress_img consistently
                        img_blob = compress_img(note_img) if note_img else None
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                        db_execute(
                            "INSERT INTO notes (course_id, note, image_blob, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                            (row['id'], note_text.strip(), img_blob, timestamp, timestamp)
                        )
                        st.success("Documentation Saved.")
                        st.rerun()   # [FIX 1] Outside write

                st.divider()
                st.subheader("📂 Saved Documentation Stack")

                course_notes = pd.read_sql_query(
                    "SELECT * FROM notes WHERE course_id = ? ORDER BY id DESC", conn, params=(row['id'],)
                )
                if course_notes.empty:
                    st.caption("No technical logs attached to this module stack.")
                else:
                    for _, note in course_notes.iterrows():
                        with st.container(border=True):
                            st.caption(f"🕐 {note.get('created_at', 'Unknown')}")
                            if note.get('note'):
                                st.write(note['note'])
                            if note.get('image_blob') is not None:
                                try:
                                    img_data = io.BytesIO(note['image_blob'])
                                    st.image(img_data, caption="Attached Reference", use_container_width=True)
                                except Exception:
                                    st.caption("⚠️ Could not render attached image.")

                            if st.button("🗑️ Delete Note", key=f"del_note_{note['id']}"):
                                db_execute("DELETE FROM notes WHERE id = ?", (note['id'],))
                                st.rerun()   # [FIX 1] Outside write

# =========================================================
# MODULES 3–8: PLACEHOLDERS
# Paste your Journal, Professional CV, MIT Learning Hub,
# Management Center, Add Course, and System Recovery
# module code below. Apply the same patterns:
#   - db_execute() instead of with conn: conn.execute()
#   - validate_text() before any text field write
#   - compress_img() for all image uploads
#   - save_pdf_to_disk() for PDF uploads
#   - st.rerun() always outside write operations
# =========================================================

elif menu == "Journal":
    st.title("📓 Engineering Journal")
    st.info("Slot your Journal module code here. Use db_execute() for all writes.")

elif menu == "Professional CV":
    st.title("🧑‍💼 Professional CV")
    st.info("Slot your Professional CV module code here.")

elif menu == "MIT Learning Hub":
    st.title("🎓 MIT Learning Hub")
    st.info("Slot your MIT Learning Hub module code here.")

elif menu == "Management Center":
    st.title("⚙️ Management Center")
    st.info("Slot your Management Center module code here.")

elif menu == "Add Course":
    st.title("➕ Add New Course Module")

    new_category = st.text_input("Category", placeholder="e.g., Control Systems")
    new_course = st.text_input("Course Name", placeholder="e.g., MIT 6.302 Feedback Systems")

    if st.button("🚀 Register Module"):
        if not new_category.strip() or not new_course.strip():
            st.error("Both category and course name are required.")
        elif not validate_text(new_category, "Category") or not validate_text(new_course, "Course Name"):
            st.stop()
        else:
            db_execute(
                "INSERT INTO courses (category, course_name) VALUES (?, ?)",
                (new_category.strip(), new_course.strip())
            )
            st.success(f"Module '{new_course.strip()}' registered successfully.")
            st.rerun()

elif menu == "System Recovery":
    st.title("🛠️ System Recovery")
    st.warning("Use these tools to recover or reset the database state.")

    if st.button("🔄 Force DB Reconnect"):
        # [FIX 6] Scoped cache clear — only clears get_conn, not all resources
        get_conn.clear()
        st.success("Database connection refreshed. Reloading...")
        st.rerun()

    st.divider()
    with st.expander("☢️ Nuclear Reset — Wipe All Data"):
        st.error("This permanently deletes ALL data from every table.")
        confirm = st.text_input("Type CONFIRM to proceed")
        if st.button("🚨 Execute Full Wipe") and confirm == "CONFIRM":
            for table in ["notes", "journal", "exercise_logs", "assignment_logs", "courses"]:
                db_execute(f"DELETE FROM {table}")
            # Also clean up PDFs on disk
            for fname in os.listdir(PDF_UPLOAD_DIR):
                try:
                    os.remove(os.path.join(PDF_UPLOAD_DIR, fname))
                except OSError:
                    pass
            st.success("All data wiped. System reset complete.")
            st.rerun()
