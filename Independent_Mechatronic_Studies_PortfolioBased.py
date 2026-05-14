import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import base64
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# =========================================================
# CONFIG & INITIALIZATION
# =========================================================
st.set_page_config(page_title="AIMecha Study OS", layout="wide")

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
    c.execute("""CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, course_name TEXT, completed INTEGER DEFAULT 0)""")
    
    # Updated NOTES table to handle images and sketches
    c.execute("""CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER, note TEXT, sketch_data TEXT, 
                image_blob BLOB, created_at TEXT)""")

    # Updated JOURNAL table to handle images and sketches
    c.execute("""CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, entry TEXT, sketch_data TEXT, 
                image_blob BLOB, created_at TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER, course_name TEXT, 
                file_name TEXT, file_blob BLOB, created_at TEXT)""")
    conn.commit()

init_db()

# =========================================================
# UI COMPONENTS FOR WRITING/SKETCHING
# =========================================================

def media_input_box(key_prefix):
    """Renders a combined Text, Sketch, and Image upload UI."""
    st.write("---")
    text_val = st.text_area("Write Notes/Reflection", key=f"text_{key_prefix}", height=150)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write("🎨 Sketchpad")
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=3,
            stroke_color="#00d4ff",
            background_color="#111",
            height=200,
            drawing_mode="freedraw",
            key=f"canvas_{key_prefix}",
        )
    
    with col2:
        st.write("🖼️ Image Upload")
        img_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], key=f"img_{key_prefix}")
    
    sketch_base64 = None
    if canvas_result.image_data is not None:
        # Convert canvas to base64 string
        img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        sketch_base64 = base64.b64encode(buffered.getvalue()).decode()

    img_blob = img_file.read() if img_file else None
    
    return text_val, sketch_base64, img_blob

# =========================================================
# NAVIGATION & SIDEBAR
# =========================================================
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)

menu = st.sidebar.radio("Navigation", 
    ["Dashboard", "Courses", "Add Course", "Manage Courses", "Journal", "Exercises", "Professional CV", "System Recovery"])

st.sidebar.divider()
if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=150)

# =========================================================
# COURSES & NOTES
# =========================================================
if menu == "Courses":
    st.title("📚 Learning Modules")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    if df.empty:
        st.info("Add a course to start taking notes.")
    else:
        for _, row in df.iterrows():
            with st.expander(f"{row['course_name']} ({row['category']})"):
                # Input Section
                t_val, s_val, i_blob = media_input_box(f"course_{row['id']}")
                
                if st.button("Save Entry", key=f"save_n_{row['id']}"):
                    conn.execute("""INSERT INTO notes (course_id, note, sketch_data, image_blob, created_at) 
                                 VALUES (?, ?, ?, ?, ?)""",
                                 (row['id'], t_val, s_val, i_blob, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("Entry Saved!")
                
                # Display History
                st.write("### 📜 History")
                history = pd.read_sql_query(f"SELECT * FROM notes WHERE course_id={row['id']} ORDER BY id DESC", conn)
                for _, entry in history.iterrows():
                    with st.container(border=True):
                        st.caption(f"📅 {entry['created_at']}")
                        if entry['note']: st.write(entry['note'])
                        
                        hcol1, hcol2 = st.columns(2)
                        if entry['sketch_data']:
                            hcol1.image(base64.b64decode(entry['sketch_data']), caption="Sketch")
                        if entry['image_blob']:
                            hcol2.image(entry['image_blob'], caption="Uploaded Image")

# =========================================================
# JOURNAL
# =========================================================
elif menu == "Journal":
    st.title("📓 Engineering Journal")
    title = st.text_input("Entry Title", value="Daily Reflection")
    
    t_val, s_val, i_blob = media_input_box("journal_main")
    
    if st.button("Save Journal Entry"):
        conn.execute("""INSERT INTO journal (title, entry, sketch_data, image_blob, created_at) 
                     VALUES (?, ?, ?, ?, ?)""",
                     (title, t_val, s_val, i_blob, datetime.now().isoformat()))
        conn.commit()
        st.success("Journal Updated!")

    st.divider()
    journals = pd.read_sql_query("SELECT * FROM journal ORDER BY id DESC", conn)
    for _, j in journals.iterrows():
        with st.expander(f"{j['title']} - {j['created_at'][:10]}"):
            if j['entry']: st.write(j['entry'])
            jcol1, jcol2 = st.columns(2)
            if j['sketch_data']:
                jcol1.image(base64.b64decode(j['sketch_data']), caption="Sketch")
            if j['image_blob']:
                jcol2.image(j['image_blob'], caption="Image")

# =========================================================
# DASHBOARD (Summary View)
# =========================================================
elif menu == "Dashboard":
    st.title("⚙️ AIMecha Engineering Dashboard")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    total = len(df)
    done = df["completed"].sum() if total > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Modules", total); c2.metric("Completed", done); c3.metric("Progress", f"{(done/total*100) if total > 0 else 0:.1f}%")
    st.progress((done/total) if total > 0 else 0)

# (Other menus Add Course, Manage Courses, Exercises, Professional CV, System Recovery follow previous logic)
# ... [Keeping logic consistent with previous versions] ...
