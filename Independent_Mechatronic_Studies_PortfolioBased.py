import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import base64
import io
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# =========================================================
# CONFIG & INITIALIZATION
# =========================================================
st.set_page_config(page_title="AIMecha Study OS", layout="wide", page_icon="⚙️")

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"
MIT_LOGO_PATH = "MIT-OCW.png"

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;") 
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

conn = get_conn()

def init_db():
    c = conn.cursor()
    # 1. Create Core Tables
    c.execute("""CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, course_name TEXT, completed INTEGER DEFAULT 0)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER, note TEXT, sketch_data TEXT, 
                image_blob BLOB, created_at TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, entry TEXT, sketch_data TEXT, 
                image_blob BLOB, created_at TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER, course_name TEXT, 
                file_name TEXT, file_blob BLOB, created_at TEXT)""")
    
    # 2. Schema Migration Check (Fixes the OperationalError)
    # This adds the new columns to old databases automatically
    tables_to_check = ["notes", "journal"]
    new_cols = [("sketch_data", "TEXT"), ("image_blob", "BLOB")]
    
    for table in tables_to_check:
        c.execute(f"PRAGMA table_info({table})")
        existing_cols = [col[1] for col in c.fetchall()]
        for col_name, col_type in new_cols:
            if col_name not in existing_cols:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
    
    conn.commit()

init_db()

# =========================================================
# UI HELPERS
# =========================================================

def media_input_box(key_prefix):
    """Integrated UI for Writing, Sketching, and Image Uploading."""
    text_val = st.text_area("Write Details", key=f"text_{key_prefix}", height=120)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.caption("🎨 Sketchpad (Draw technical diagrams here)")
        canvas_result = st_canvas(
            fill_color="rgba(0, 212, 255, 0.2)",
            stroke_width=2,
            stroke_color="#00d4ff",
            background_color="#0e1117",
            height=200,
            drawing_mode="freedraw",
            key=f"canvas_{key_prefix}",
        )
    
    with col2:
        st.caption("🖼️ Reference Image (Upload schematics or screenshots)")
        img_file = st.file_uploader("Select Image", type=["png", "jpg", "jpeg"], key=f"img_{key_prefix}")
    
    sketch_base64 = None
    if canvas_result.image_data is not None:
        # Check if user actually drew something before processing
        img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        sketch_base64 = base64.b64encode(buffered.getvalue()).decode()

    img_blob = img_file.read() if img_file else None
    return text_val, sketch_base64, img_blob

# =========================================================
# NAVIGATION & LOGOS
# =========================================================
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)

menu = st.sidebar.radio("Navigation", 
    ["Dashboard", "Courses", "Add Course", "Manage Courses", "Journal", "Exercises", "Professional CV", "System Recovery"])

st.sidebar.divider()
if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=150)
else:
    st.sidebar.caption("🎓 MIT-OCW Integrated")

# =========================================================
# TABS LOGIC
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ AIMecha Engineering Dashboard")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    total = len(df)
    done = df["completed"].sum() if total > 0 else 0
    prog = (done / total) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Modules", total)
    c2.metric("Completed", done)
    c3.metric("OS Completion Status", f"{prog*100:.1f}%")
    st.progress(prog)

elif menu == "Courses":
    st.title("📚 Learning Modules")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    if df.empty:
        st.info("Start by adding a course in the 'Add Course' tab.")
    else:
        for _, row in df.iterrows():
            with st.expander(f"📖 {row['course_name']} ({row['category']})"):
                col_h1, col_h2 = st.columns([1, 4])
                is_done = col_h1.checkbox("Completed", value=bool(row["completed"]), key=f"chk_{row['id']}")
                conn.execute("UPDATE courses SET completed=? WHERE id=?", (int(is_done), row['id']))
                conn.commit()

                # Combined Write/Sketch/Upload UI
                t_val, s_val, i_blob = media_input_box(f"course_{row['id']}")
                
                if st.button("Save Technical Entry", key=f"btn_{row['id']}"):
                    conn.execute("""INSERT INTO notes (course_id, note, sketch_data, image_blob, created_at) 
                                 VALUES (?,?,?,?,?)""",
                                 (row['id'], t_val, s_val, i_blob, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("Entry Synchronized!")
                    st.rerun()

                # History
                st.write("---")
                notes = pd.read_sql_query(f"SELECT * FROM notes WHERE course_id={row['id']} ORDER BY id DESC", conn)
                for _, n in notes.iterrows():
                    with st.container(border=True):
                        st.caption(f"📅 {n['created_at']}")
                        if n['note']: st.write(n['note'])
                        hcol1, hcol2 = st.columns(2)
                        if n['sketch_data']: hcol1.image(base64.b64decode(n['sketch_data']), caption="Technical Sketch")
                        if n['image_blob']: hcol2.image(n['image_blob'], caption="Uploaded Ref")

elif menu == "Journal":
    st.title("📓 Engineering Journal")
    j_title = st.text_input("Entry Header", "Weekly System Reflection")
    t_val, s_val, i_blob = media_input_box("journal")
    
    if st.button("Commit Journal Entry"):
        conn.execute("INSERT INTO journal (title, entry, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                     (j_title, t_val, s_val, i_blob, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        st.success("Journal Entry Locked.")
        st.rerun()

    st.divider()
    logs = pd.read_sql_query("SELECT * FROM journal ORDER BY id DESC", conn)
    for _, log in logs.iterrows():
        with st.expander(f"{log['title']} — {log['created_at']}"):
            if log['entry']: st.write(log['entry'])
            jcol1, jcol2 = st.columns(2)
            if log['sketch_data']: jcol1.image(base64.b64decode(log['sketch_data']), caption="Visual Log")
            if log['image_blob']: jcol2.image(log['image_blob'], caption="Resource")

elif menu == "Exercises":
    st.title("📤 Assignment & Exercise Vault")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    
    with st.form("ex_upload"):
        c1, c2 = st.columns(2)
        target_c = c1.selectbox("Course Link", courses["course_name"] if not courses.empty else ["None"])
        task_name = c1.text_input("Assignment Title")
        file_obj = c2.file_uploader("Upload Lab Report/Code/Artifact")
        if st.form_submit_button("Store Assignment") and file_obj and not courses.empty:
            c_id = courses[courses["course_name"] == target_c]["id"].values[0]
            conn.execute("INSERT INTO exercises (course_id, course_name, file_name, file_blob, created_at) VALUES (?,?,?,?,?)",
                         (int(c_id), target_c, file_obj.name, file_obj.read(), datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            st.success(f"Archived: {file_obj.name}")
            st.rerun()

    st.divider()
    ex_list = pd.read_sql_query("SELECT id, course_name, file_name, file_blob FROM exercises ORDER BY id DESC", conn)
    for _, ex in ex_list.iterrows():
        ecol1, ecol2 = st.columns([4, 1])
        ecol1.write(f"📁 **{ex['file_name']}** (*{ex['course_name']}*)")
        ecol2.download_button("Download", ex['file_blob'], file_name=ex['file_name'], key=f"dl_{ex['id']}")

elif menu == "Professional CV":
    st.title("📄 Professional Engineering Portfolio")
    st.markdown("""<style>.cv-card { background: rgba(255, 255, 255, 0.05); border-left: 5px solid #00d4ff; padding: 20px; border-radius: 10px; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)
    
    comp = pd.read_sql_query("SELECT * FROM courses WHERE completed = 1", conn)
    if comp.empty:
        st.warning("Complete courses to populate your portfolio achievements.")
    else:
        for _, row in comp.iterrows():
            st.markdown(f'<div class="cv-card"><h3>✅ {row["course_name"]}</h3><p>Field: {row["category"]}</p></div>', unsafe_allow_html=True)

elif menu == "Manage Courses":
    st.title("🗑️ Curriculum Management")
    m_df = pd.read_sql_query("SELECT * FROM courses", conn)
    for _, m_row in m_df.iterrows():
        mc1, mc2, mc3 = st.columns([3, 2, 1])
        mc1.write(f"**{m_row['course_name']}**")
        mc2.write(f"({m_row['category']})")
        if mc3.button("Delete", key=f"del_{m_row['id']}", type="primary"):
            conn.execute("DELETE FROM courses WHERE id=?", (m_row['id'],))
            conn.execute("DELETE FROM notes WHERE course_id=?", (m_row['id'],))
            conn.commit()
            st.rerun()

elif menu == "Add Course":
    st.title("➕ Create Study Module")
    with st.form("new_c"):
        c_cat = st.selectbox("Specialization", ["Programming", "Robotics", "Mechatronics", "AI/ML", "Physics"])
        c_name = st.text_input("Module Name")
        if st.form_submit_button("Add to OS") and c_name:
            conn.execute("INSERT INTO courses (category, course_name) VALUES (?, ?)", (c_cat, c_name))
            conn.commit()
            st.success(f"{c_name} added.")

elif menu == "System Recovery":
    st.title("💾 System Backup")
    with open(DB_NAME, "rb") as db_file:
        st.download_button("📥 Export OS Database", db_file, file_name="aimecha_study_backup.db")
    
    st.write("---")
    res_file = st.file_uploader("📥 Restore OS Database", type=["db"])
    if res_file and st.button("⚠️ Wipe & Restore"):
        conn.close()
        with open(DB_NAME, "wb") as f: f.write(res_file.getbuffer())
        st.cache_resource.clear()
        st.rerun()
