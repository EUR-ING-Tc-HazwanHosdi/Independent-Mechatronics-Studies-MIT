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
# 1. CORE ENGINE & DATABASE INITIALIZATION
# =========================================================
st.set_page_config(page_title="AIMecha Study OS", layout="wide", page_icon="⚙️")

DB_NAME = "aimecha_study_os.db"

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;") 
    return conn

conn = get_conn()

def init_db():
    c = conn.cursor()
    # Core Tables
    c.execute("CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, category TEXT, course_name TEXT, completed INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, course_id INTEGER, note TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, title TEXT, entry TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS exercises (id INTEGER PRIMARY KEY, course_id INTEGER, course_name TEXT, file_name TEXT, file_blob BLOB, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, name TEXT, bio TEXT, title TEXT, profile_img BLOB)")
    
    # Initialize Profile if empty
    c.execute("INSERT OR IGNORE INTO profile (id, name, bio, title) VALUES (1, 'Arjun Singh', 'Mechatronics & AI Engineer passionate about robotics.', 'Lead Engineer')")
    
    # Auto-Migration for older schemas
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
# 2. UTILITIES (Compression & Input)
# =========================================================

def compress_img(image_file):
    """Reduces database bloat by compressing uploads."""
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail((1000, 1000))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()

def multimodal_input(key):
    """Unified UI for text, sketches, and images."""
    text = st.text_area("Observations/Details", key=f"txt_{key}", height=100)
    c1, c2 = st.columns(2)
    with c1:
        st.caption("🎨 Technical Sketchpad")
        canvas = st_canvas(fill_color="rgba(0,212,255,0.1)", stroke_width=2, stroke_color="#00d4ff",
                           background_color="#0e1117", height=200, key=f"can_{key}")
    with c2:
        st.caption("🖼️ Upload Reference")
        img = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], key=f"img_{key}")
    
    s_b64 = None
    if canvas.image_data is not None:
        raw_img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
        buf = io.BytesIO()
        raw_img.save(buf, format="PNG")
        s_b64 = base64.b64encode(buf.getvalue()).decode()
    
    i_blob = compress_img(img) if img else None
    return text, s_b64, i_blob

# =========================================================
# 3. SIDEBAR NAVIGATION
# =========================================================
st.sidebar.title("AIMECHA OS")
menu = st.sidebar.radio("Navigation", 
    ["Dashboard", "Courses", "Journal", "Add Course", "Professional CV", "Exercises", "System Recovery"])

# =========================================================
# 4. DASHBOARD
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

# =========================================================
# 5. COURSES & NOTES (SEARCHABLE)
# =========================================================
elif menu == "Courses":
    st.title("📚 Study Modules & Technical Notes")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    
    if courses.empty:
        st.info("No courses yet. Head to 'Add Course'.")
    else:
        search_note = st.text_input("🔍 Search notes...", "")
        for _, row in courses.iterrows():
            with st.expander(f"📖 {row['course_name']} ({row['category']})", expanded=not search_note):
                is_comp = st.checkbox("Mark Completed", value=bool(row['completed']), key=f"comp_{row['id']}")
                if is_comp != bool(row['completed']):
                    conn.execute("UPDATE courses SET completed=? WHERE id=?", (int(is_comp), row['id']))
                    conn.commit()
                    st.rerun()

                txt, sk, im = multimodal_input(f"course_{row['id']}")
                if st.button("Save Note", key=f"btn_{row['id']}"):
                    conn.execute("INSERT INTO notes (course_id, note, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                                 (row['id'], txt, sk, im, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("Synchronized!")
                    st.rerun()
                
                # Note History with Deletion
                n_query = "SELECT * FROM notes WHERE course_id=? AND note LIKE ? ORDER BY id DESC"
                notes = pd.read_sql_query(n_query, conn, params=(row['id'], f'%{search_note}%'))
                for _, n in notes.iterrows():
                    with st.container(border=True):
                        n_col1, n_col2 = st.columns([0.9, 0.1])
                        n_col1.caption(f"📅 {n['created_at']}")
                        if n_col2.button("🗑️", key=f"del_n_{n['id']}"):
                            conn.execute("DELETE FROM notes WHERE id=?", (n['id'],))
                            conn.commit()
                            st.rerun()
                        if n['note']: st.write(n['note'])
                        nc1, nc2 = st.columns(2)
                        if n['sketch_data']: nc1.image(base64.b64decode(n['sketch_data']), caption="Sketch")
                        if n['image_blob']: nc2.image(n['image_blob'], caption="Ref")

# =========================================================
# 6. JOURNAL (MULTIMODAL)
# =========================================================
elif menu == "Journal":
    st.title("📓 Engineering Journal")
    with st.expander("➕ New Log Entry"):
        j_title = st.text_input("Title", "Daily Log")
        txt, sk, im = multimodal_input("journal")
        if st.button("Save Journal Entry"):
            conn.execute("INSERT INTO journal (title, entry, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                         (j_title, txt, sk, im, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            st.rerun()
    
    search_j = st.text_input("🔍 Search Logs", "")
    j_df = pd.read_sql_query("SELECT * FROM journal WHERE title LIKE ? OR entry LIKE ? ORDER BY id DESC", 
                             conn, params=(f'%{search_j}%', f'%{search_j}%'))
    for _, j in j_df.iterrows():
        with st.container(border=True):
            h1, h2 = st.columns([0.9, 0.1])
            h1.subheader(j['title'])
            if h2.button("🗑️", key=f"del_j_{j['id']}"):
                conn.execute("DELETE FROM journal WHERE id=?", (j['id'],))
                conn.commit()
                st.rerun()
            st.caption(j['created_at'])
            if j['entry']: st.write(j['entry'])
            mc1, mc2 = st.columns(2)
            if j['sketch_data']: mc1.image(base64.b64decode(j['sketch_data']))
            if j['image_blob']: mc2.image(j['image_blob'])

# =========================================================
# 7. PROFESSIONAL PORTFOLIO (THE "READY-TO-USE" CV)
# =========================================================
elif menu == "Professional CV":
    prof = pd.read_sql_query("SELECT * FROM profile WHERE id=1", conn).iloc[0]
    
    with st.sidebar.expander("👤 Edit Bio & Photo"):
        u_name = st.text_input("Name", prof['name'])
        u_title = st.text_input("Title", prof['title'])
        u_bio = st.text_area("Bio", prof['bio'])
        u_img = st.file_uploader("Photo", type=['jpg','png'])
        if st.button("Update"):
            img_v = compress_img(u_img) if u_img else prof['profile_img']
            conn.execute("UPDATE profile SET name=?, title=?, bio=?, profile_img=? WHERE id=1", (u_name, u_title, u_bio, img_v))
            conn.commit()
            st.rerun()

    # CSS for Portfolio
    st.markdown("""<style>
        .header-card { background: rgba(0,212,255,0.05); border: 1px solid #00d4ff; border-radius: 15px; padding: 25px; }
        .skill-bar { background: #1e1e1e; border-radius: 10px; height: 10px; margin-bottom: 10px; }
        .skill-fill { background: #00d4ff; height: 10px; border-radius: 10px; }
    </style>""", unsafe_allow_html=True)

    # Header
    col1, col2 = st.columns([1, 3])
    with col1:
        if prof['profile_img']: st.image(prof['profile_img'], width=180)
        else: st.title("👤")
    with col2:
        st.title(prof['name'])
        st.subheader(prof['title'])
        st.info(prof['bio'])

    st.divider()
    
    # Competency Summary
    st.subheader("📊 Competency Summary")
    c_df = pd.read_sql_query("SELECT * FROM courses", conn)
    if not c_df.empty:
        stats = c_df.groupby('category')['completed'].mean() * 100
        cols = st.columns(3)
        for i, (cat, val) in enumerate(stats.items()):
            with cols[i%3]:
                st.write(f"**{cat}** ({val:.0f}%)")
                st.markdown(f'<div class="skill-bar"><div class="skill-fill" style="width:{val}%"></div></div>', unsafe_allow_html=True)

    st.divider()
    
    # Verified Artifacts
    st.subheader("✅ Verified Technical Artifacts")
    comp = c_df[c_df['completed'] == 1]
    vcols = st.columns(3)
    for i, (_, r) in enumerate(comp.iterrows()):
        with vcols[i%3]:
            with st.container(border=True):
                st.markdown(f"**{r['course_name']}**")
                art = pd.read_sql_query(f"SELECT sketch_data FROM notes WHERE course_id={r['id']} AND sketch_data IS NOT NULL LIMIT 1", conn)
                if not art.empty:
                    with st.expander("View Schematic"):
                        st.image(base64.b64decode(art.iloc[0,0]))
                else: st.caption("No artifacts yet.")

# =========================================================
# 8. OTHER TABS (STUBBED FOR COMPLETION)
# =========================================================
elif menu == "Add Course":
    st.title("➕ Add New Module")
    with st.form("add_c"):
        cat = st.selectbox("Category", ["Programming", "AI", "Mechatronics", "Electronics"])
        name = st.text_input("Course Name")
        if st.form_submit_button("Add"):
            conn.execute("INSERT INTO courses (category, course_name) VALUES (?, ?)", (cat, name))
            conn.commit()
            st.success("Added!")

elif menu == "Exercises":
    st.title("📤 Assignment Vault")
    # Existing Exercise Logic...

elif menu == "System Recovery":
    st.title("💾 System Backup & Optimization")
    if st.button("🧹 Optimize Storage (Vacuum)"):
        conn.execute("VACUUM")
        st.success("Database Shrunk!")
