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
    conn.commit()

init_db()

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def media_input_box(key_prefix):
    """Integrated Text, Sketch, and Image upload UI."""
    text_val = st.text_area("Write Details", key=f"text_{key_prefix}", height=100)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.caption("🎨 Sketchpad")
        canvas_result = st_canvas(
            fill_color="rgba(0, 212, 255, 0.2)",
            stroke_width=2,
            stroke_color="#00d4ff",
            background_color="#0e1117",
            height=150,
            drawing_mode="freedraw",
            key=f"canvas_{key_prefix}",
        )
    
    with col2:
        st.caption("🖼️ Upload Reference Image")
        img_file = st.file_uploader("Select Image", type=["png", "jpg", "jpeg"], key=f"img_{key_prefix}")
    
    sketch_base64 = None
    if canvas_result.image_data is not None:
        img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        sketch_base64 = base64.b64encode(buffered.getvalue()).decode()

    img_blob = img_file.read() if img_file else None
    return text_val, sketch_base64, img_blob

# =========================================================
# SIDEBAR
# =========================================================
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)

menu = st.sidebar.radio("Navigation", 
    ["Dashboard", "Courses", "Add Course", "Manage Courses", "Journal", "Exercises", "Professional CV", "System Recovery"])

st.sidebar.divider()
if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=150)
else:
    st.sidebar.caption("🎓 MIT-OCW Linked")

# =========================================================
# DASHBOARD
# =========================================================
if menu == "Dashboard":
    st.title("⚙️ AIMecha Engineering Dashboard")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    total = len(df)
    done = df["completed"].sum() if total > 0 else 0
    prog = (done / total) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Modules", total)
    c2.metric("Completed", done)
    c3.metric("Goal Progress", f"{prog*100:.1f}%")
    st.progress(prog)

# =========================================================
# COURSES & NOTES
# =========================================================
elif menu == "Courses":
    st.title("📚 Learning Modules")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    if df.empty:
        st.info("Add a course to start.")
    else:
        for _, row in df.iterrows():
            with st.expander(f"📖 {row['course_name']} ({row['category']})"):
                is_done = st.checkbox("Course Completed", value=bool(row["completed"]), key=f"check_{row['id']}")
                conn.execute("UPDATE courses SET completed=? WHERE id=?", (int(is_done), row['id']))
                conn.commit()

                t_val, s_val, i_blob = media_input_box(f"course_{row['id']}")
                if st.button("Save Entry", key=f"save_n_{row['id']}"):
                    conn.execute("INSERT INTO notes (course_id, note, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                                 (row['id'], t_val, s_val, i_blob, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("Note and Visuals Saved!")
                
                # History Display
                history = pd.read_sql_query(f"SELECT * FROM notes WHERE course_id={row['id']} ORDER BY id DESC", conn)
                for _, entry in history.iterrows():
                    with st.container(border=True):
                        st.caption(f"📅 {entry['created_at']}")
                        if entry['note']: st.write(entry['note'])
                        hcol1, hcol2 = st.columns(2)
                        if entry['sketch_data']: hcol1.image(base64.b64decode(entry['sketch_data']), caption="Sketch")
                        if entry['image_blob']: hcol2.image(entry['image_blob'], caption="Uploaded Ref")

# =========================================================
# JOURNAL
# =========================================================
elif menu == "Journal":
    st.title("📓 Engineering Journal")
    title = st.text_input("Reflection Title", "Daily Log")
    t_val, s_val, i_blob = media_input_box("journal")
    
    if st.button("Save Journal Entry"):
        conn.execute("INSERT INTO journal (title, entry, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                     (title, t_val, s_val, i_blob, datetime.now().isoformat()))
        conn.commit()
        st.success("Journal Entry Secured.")

    st.divider()
    journals = pd.read_sql_query("SELECT * FROM journal ORDER BY id DESC", conn)
    for _, j in journals.iterrows():
        with st.expander(f"{j['title']} - {j['created_at'][:10]}"):
            if j['entry']: st.write(j['entry'])
            jcol1, jcol2 = st.columns(2)
            if j['sketch_data']: jcol1.image(base64.b64decode(j['sketch_data']), caption="Sketch")
            if j['image_blob']: jcol2.image(j['image_blob'], caption="Image")

# =========================================================
# EXERCISES (ASSIGNMENT VAULT)
# =========================================================
elif menu == "Exercises":
    st.title("📤 Assignment & Exercise Vault")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    
    with st.form("upload_task"):
        c1, c2 = st.columns(2)
        sel_c = c1.selectbox("Course", courses["course_name"] if not courses.empty else ["None"])
        t_name = c1.text_input("Task/Assignment Name")
        up_file = c2.file_uploader("Upload Document/Archive")
        submitted = st.form_submit_button("Upload Task")
        
        if submitted and up_file and not courses.empty:
            c_id = courses[courses["course_name"] == sel_c]["id"].values[0]
            conn.execute("INSERT INTO exercises (course_id, course_name, file_name, file_blob, created_at) VALUES (?,?,?,?,?)",
                         (int(c_id), sel_c, up_file.name, up_file.read(), datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            st.success("Assignment Archived!")

    st.divider()
    all_ex = pd.read_sql_query("SELECT id, course_name, file_name, file_blob FROM exercises ORDER BY id DESC", conn)
    for _, row in all_ex.iterrows():
        col_f, col_d = st.columns([4, 1])
        col_f.write(f"📁 **{row['file_name']}** — *{row['course_name']}*")
        col_d.download_button("Download", row['file_blob'], file_name=row['file_name'], key=f"dl_{row['id']}")

# =========================================================
# PROFESSIONAL CV
# =========================================================
elif menu == "Professional CV":
    st.title("📄 Engineering Portfolio")
    st.markdown("""<style>.cv-card { background: rgba(255, 255, 255, 0.05); border-left: 5px solid #00d4ff; padding: 20px; border-radius: 10px; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)
    
    comp = pd.read_sql_query("SELECT * FROM courses WHERE completed = 1", conn)
    if comp.empty:
        st.warning("Complete courses to show verified achievements here.")
    else:
        for _, row in comp.iterrows():
            st.markdown(f'<div class="cv-card"><h3>✅ {row["course_name"]}</h3><p>Category: {row["category"]}</p></div>', unsafe_allow_html=True)

# =========================================================
# MANAGE COURSES
# =========================================================
elif menu == "Manage Courses":
    st.title("🗑️ Manage Inventory")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    for _, row in df.iterrows():
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(f"**{row['course_name']}**")
        c2.write(row['category'])
        if c3.button("Delete", key=f"del_{row['id']}", type="primary"):
            conn.execute("DELETE FROM courses WHERE id=?", (row['id'],))
            conn.commit()
            st.rerun()

# =========================================================
# SYSTEM RECOVERY & ADD COURSE
# =========================================================
elif menu == "Add Course":
    st.title("➕ Add New Module")
    with st.form("add_c"):
        cat = st.selectbox("Category", ["AI", "Robotics", "Mechatronics", "Programming", "Mathematics"])
        name = st.text_input("Course Name")
        if st.form_submit_button("Add"):
            conn.execute("INSERT INTO courses (category, course_name) VALUES (?, ?)", (cat, name))
            conn.commit()
            st.success("Module Added!")

elif menu == "System Recovery":
    st.title("💾 Recovery & Backup")
    with open(DB_NAME, "rb") as f:
        st.download_button("📥 Backup Database", f, file_name="aimecha_os.db")
    
    up_db = st.file_uploader("📤 Restore System", type=["db"])
    if up_db and st.button("⚠️ Confirm Restore"):
        conn.close()
        with open(DB_NAME, "wb") as f: f.write(up_db.getbuffer())
        st.cache_resource.clear()
        st.rerun()
