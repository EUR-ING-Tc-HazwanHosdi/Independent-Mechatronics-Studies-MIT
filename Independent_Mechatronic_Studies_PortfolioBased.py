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
# 1. CORE ENGINE & DATABASE MIGRATION
# =========================================================
st.set_page_config(page_title="AIMecha Study OS", layout="wide", page_icon="⚙️")

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"
MIT_LOGO_PATH = "MIT-OCW.png"

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;") # Better concurrency
    return conn

conn = get_conn()

def init_db():
    c = conn.cursor()
    # Create tables
    c.execute("CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, category TEXT, course_name TEXT, completed INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, course_id INTEGER, note TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, title TEXT, entry TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS exercises (id INTEGER PRIMARY KEY, course_id INTEGER, course_name TEXT, file_name TEXT, file_blob BLOB, created_at TEXT)")
    
    # Auto-Migration Check: Adds columns if they are missing from older versions
    c.execute("PRAGMA table_info(notes)")
    cols = [col[1] for col in c.fetchall()]
    if "sketch_data" not in cols:
        try:
            c.execute("ALTER TABLE notes ADD COLUMN sketch_data TEXT")
            c.execute("ALTER TABLE notes ADD COLUMN image_blob BLOB")
            c.execute("ALTER TABLE journal ADD COLUMN sketch_data TEXT")
            c.execute("ALTER TABLE journal ADD COLUMN image_blob BLOB")
        except: pass
    conn.commit()

init_db()

# =========================================================
# 2. UTILITY FUNCTIONS (Media & Backups)
# =========================================================

def get_full_db_binary():
    """Forces the database to solidify all data for a perfect backup."""
    conn.execute("PRAGMA wal_checkpoint(FULL);") 
    with open(DB_NAME, "rb") as f:
        return f.read()

def multimodal_input(key):
    """Reusable UI for writing, sketching, and uploading."""
    text = st.text_area("Write Details/Notes", key=f"txt_{key}", height=100)
    c1, c2 = st.columns(2)
    with c1:
        st.caption("🎨 Technical Sketchpad")
        canvas = st_canvas(fill_color="rgba(0,212,255,0.1)", stroke_width=2, stroke_color="#00d4ff",
                           background_color="#0e1117", height=200, key=f"can_{key}")
    with c2:
        st.caption("🖼️ Upload Image/Reference")
        img = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], key=f"img_{key}")
    
    # Process Sketch to Base64
    s_b64 = None
    if canvas.image_data is not None:
        raw_img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
        buf = io.BytesIO()
        raw_img.save(buf, format="PNG")
        s_b64 = base64.b64encode(buf.getvalue()).decode()
    
    i_blob = img.read() if img else None
    return text, s_b64, i_blob

# =========================================================
# 3. SIDEBAR & NAVIGATION
# =========================================================
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)

menu = st.sidebar.radio("Navigation", 
    ["Dashboard", "Courses", "Add Course", "Manage Courses", "Journal", "Exercises", "Professional CV", "System Recovery"])

st.sidebar.divider()
if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=150)

# =========================================================
# 4. TAB LOGIC
# =========================================================

if menu == "Dashboard":
    st.title("⚙️ AIMecha Engineering Dashboard")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    total = len(df)
    done = df["completed"].sum() if total > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Modules", total)
    c2.metric("Completed", done)
    c3.metric("OS Mastery", f"{(done/total*100) if total > 0 else 0:.1f}%")
    st.progress((done/total) if total > 0 else 0)

elif menu == "Courses":
    st.title("📚 Study Modules & Technical Notes")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    if courses.empty:
        st.info("No courses yet. Head to 'Add Course'.")
    else:
        for _, row in courses.iterrows():
            with st.expander(f"📖 {row['course_name']} ({row['category']})"):
                is_comp = st.checkbox("Mark Module Completed", value=bool(row['completed']), key=f"comp_{row['id']}")
                conn.execute("UPDATE courses SET completed=? WHERE id=?", (int(is_comp), row['id']))
                conn.commit()
                
                txt, sk, im = multimodal_input(f"course_{row['id']}")
                if st.button("Save Multimodal Note", key=f"btn_{row['id']}"):
                    conn.execute("INSERT INTO notes (course_id, note, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                                 (row['id'], txt, sk, im, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("Synchronized!")
                    st.rerun()
                
                # Show History
                notes = pd.read_sql_query(f"SELECT * FROM notes WHERE course_id={row['id']} ORDER BY id DESC", conn)
                for _, n in notes.iterrows():
                    with st.container(border=True):
                        st.caption(f"📅 {n['created_at']}")
                        if n['note']: st.write(n['note'])
                        hc1, hc2 = st.columns(2)
                        if n['sketch_data']: hc1.image(base64.b64decode(n['sketch_data']), caption="Sketch")
                        if n['image_blob']: hc2.image(n['image_blob'], caption="Reference")

elif menu == "Journal":
    st.title("📓 Engineering Journal")
    j_title = st.text_input("Entry Title", "Daily Log")
    txt, sk, im = multimodal_input("journal")
    if st.button("Commit to Journal"):
        conn.execute("INSERT INTO journal (title, entry, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                     (j_title, txt, sk, im, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        st.success("Entry Saved.")
        st.rerun()

elif menu == "Exercises":
    st.title("📤 Exercise & Assignment Vault")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    with st.form("ex_upload"):
        c_sel = st.selectbox("Link to Course", courses["course_name"] if not courses.empty else ["None"])
        t_name = st.text_input("Assignment/Task Name")
        f_up = st.file_uploader("Select Assignment File")
        if st.form_submit_button("Store Assignment") and f_up and not courses.empty:
            c_id = courses[courses["course_name"] == c_sel]["id"].values[0]
            conn.execute("INSERT INTO exercises (course_id, course_name, file_name, file_blob, created_at) VALUES (?,?,?,?,?)",
                         (int(c_id), c_sel, f_up.name, f_up.read(), datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            st.success("File stored safely.")
            st.rerun()
    
    # Display Tasks
    tasks = pd.read_sql_query("SELECT * FROM exercises ORDER BY id DESC", conn)
    for _, t in tasks.iterrows():
        tcol1, tcol2 = st.columns([4, 1])
        tcol1.write(f"📁 **{t['file_name']}** ({t['course_name']})")
        tcol2.download_button("Download", t['file_blob'], file_name=t['file_name'], key=f"tdl_{t['id']}")

elif menu == "Professional CV":
    st.title("📄 Professional Portfolio")
    st.markdown("""<style>.cv-card { background: rgba(255, 255, 255, 0.05); border-left: 5px solid #00d4ff; padding: 20px; border-radius: 10px; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)
    comp = pd.read_sql_query("SELECT * FROM courses WHERE completed = 1", conn)
    if comp.empty:
        st.warning("Finish modules to unlock your portfolio.")
    else:
        for _, row in comp.iterrows():
            st.markdown(f'<div class="cv-card"><h3>✅ {row["course_name"]}</h3><p>Verified Mastery in {row["category"]}</p></div>', unsafe_allow_html=True)

elif menu == "System Recovery":
    st.title("💾 Absolute System Backup")
    st.info("Includes all notes, sketches, and assignment files.")
    
    # SAFE DOWNLOAD
    db_bin = get_full_db_binary()
    st.download_button("📥 Download Full System Backup (.db)", db_bin, 
                       file_name=f"AIMecha_Backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db", use_container_width=True)
    
    st.divider()
    st.subheader("⚠️ Safe Restore")
    res_file = st.file_uploader("Upload Backup File", type=["db"])
    if res_file:
        lock = st.text_input("Type 'OVERWRITE' to confirm")
        if lock == "OVERWRITE":
            if st.button("🚀 Restore System", type="primary"):
                conn.close()
                with open(DB_NAME, "wb") as f: f.write(res_file.getbuffer())
                st.cache_resource.clear()
                st.success("Success! Reloading...")
                st.rerun()

elif menu == "Add Course":
    st.title("➕ Add Course")
    with st.form("add_c"):
        cat = st.selectbox("Category", ["Programming", "AI", "Mechatronics", "Electronics"])
        name = st.text_input("Course Name")
        if st.form_submit_button("Add"):
            conn.execute("INSERT INTO courses (category, course_name) VALUES (?, ?)", (cat, name))
            conn.commit()
            st.success("Added!")

elif menu == "Manage Courses":
    st.title("🗑️ Delete Courses")
    m_df = pd.read_sql_query("SELECT * FROM courses", conn)
    for _, mr in m_df.iterrows():
        mc1, mc2 = st.columns([4, 1])
        mc1.write(f"**{mr['course_name']}**")
        if mc2.button("Delete", key=f"mdel_{mr['id']}", type="primary"):
            conn.execute("DELETE FROM courses WHERE id=?", (mr['id'],))
            conn.execute("DELETE FROM notes WHERE course_id=?", (mr['id'],))
            conn.commit()
            st.rerun()
