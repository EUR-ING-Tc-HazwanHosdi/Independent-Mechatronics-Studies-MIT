import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import base64
import io
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# =========================================================
# 1. CORE ENGINE & DATABASE INITIALIZATION
# =========================================================
st.set_page_config(page_title="AIMecha Study OS", layout="wide", page_icon="⚙️")

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"
MIT_LOGO_PATH = "MIT-OCW.png"

@st.cache_resource
def get_conn():
    """Initializes the database with WAL mode for high-performance concurrency."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;") 
    return conn

conn = get_conn()

def init_db():
    """Ensures all tables exist and data persists across reboots."""
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, category TEXT, course_name TEXT, completed INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, course_id INTEGER, note TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, title TEXT, entry TEXT, sketch_data TEXT, image_blob BLOB, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, name TEXT, bio TEXT, title TEXT, profile_img BLOB)")
    
    # Insert default profile if it doesn't exist (INSERT OR IGNORE saves your custom edits)
    c.execute("INSERT OR IGNORE INTO profile (id, name, bio, title) VALUES (1, 'Your Name', 'Mechatronics & AI Engineer', 'Lead Engineer')")
    conn.commit()

init_db()

# =========================================================
# 2. UTILITY FUNCTIONS (Compression & Inputs)
# =========================================================

def compress_img(image_file):
    """Optimizes storage by compressing BLOB data before saving to SQLite."""
    if image_file is None: return None
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((1000, 1000))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()

def multimodal_input(key):
    """Unified UI for text, sketches, and image uploads."""
    text = st.text_area("Technical Details/Observations", key=f"txt_{key}", height=120)
    c1, c2 = st.columns(2)
    with c1:
        st.caption("🎨 Technical Sketchpad")
        canvas = st_canvas(fill_color="rgba(0,212,255,0.1)", stroke_width=2, stroke_color="#00d4ff",
                           background_color="#0e1117", height=200, key=f"can_{key}")
    with c2:
        st.caption("🖼️ Upload Reference/Schematic")
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
# 3. SIDEBAR NAVIGATION & LOGOS
# =========================================================
# Display AIMECHA Logo
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.title("⚙️ AIMECHA OS")

menu = st.sidebar.radio("Navigation", 
    ["Dashboard", "Courses", "Journal", "Professional CV", "Add Course", "System Recovery"])

st.sidebar.divider()

# Display MIT OCW Logo
if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=150)
    st.sidebar.caption("Powered by Open Learning")

# =========================================================
# 4. COURSES & NOTES (WITH DATA RECALL)
# =========================================================
if menu == "Courses":
    st.title("📚 Study Modules & Technical Notes")
    courses = pd.read_sql_query("SELECT * FROM courses", conn)
    
    if courses.empty:
        st.info("No courses yet. Head to 'Add Course' to begin.")
    else:
        search_note = st.text_input("🔍 Search within your notes...", "")
        for _, row in courses.iterrows():
            with st.expander(f"📖 {row['course_name']} ({row['category']})", expanded=not search_note):
                is_comp = st.checkbox("Mark Module Completed", value=bool(row['completed']), key=f"comp_{row['id']}")
                if is_comp != bool(row['completed']):
                    conn.execute("UPDATE courses SET completed=? WHERE id=?", (int(is_comp), row['id']))
                    conn.commit()
                    st.rerun()

                txt, sk, im = multimodal_input(f"c_{row['id']}")
                if st.button("Save Technical Note", key=f"btn_{row['id']}"):
                    conn.execute("INSERT INTO notes (course_id, note, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                                 (row['id'], txt, sk, im, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.rerun()
                
                st.divider()
                # DATA RECALL: Persistence logic pulls history from DB
                n_query = "SELECT * FROM notes WHERE course_id=? AND note LIKE ? ORDER BY id DESC"
                notes_history = pd.read_sql_query(n_query, conn, params=(row['id'], f'%{search_note}%'))
                
                for _, n in notes_history.iterrows():
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
                        if n['image_blob']: nc2.image(n['image_blob'], caption="Reference")

# =========================================================
# 5. JOURNAL (WITH DATA RECALL)
# =========================================================
elif menu == "Journal":
    st.title("📓 Engineering Journal")
    with st.expander("➕ New Daily Log Entry", expanded=False):
        j_title = st.text_input("Entry Title", "Daily Progress Update")
        txt, sk, im = multimodal_input("journal_main")
        if st.button("Commit to Journal"):
            conn.execute("INSERT INTO journal (title, entry, sketch_data, image_blob, created_at) VALUES (?,?,?,?,?)",
                         (j_title, txt, sk, im, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            st.rerun()
    
    st.divider()
    search_j = st.text_input("🔍 Search Journal History", "")
    # DATA RECALL: Fetching stored journal logs
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
            st.caption(f"🕒 {j['created_at']}")
            if j['entry']: st.write(j['entry'])
            mc1, mc2 = st.columns(2)
            if j['sketch_data']: mc1.image(base64.b64decode(j['sketch_data']), caption="Sketch")
            if j['image_blob']: mc2.image(j['image_blob'], caption="Reference")

# =========================================================
# 6. PROFESSIONAL CV (GRAPHICAL DASHBOARD)
# =========================================================
elif menu == "Professional CV":
    prof = pd.read_sql_query("SELECT * FROM profile WHERE id=1", conn).iloc[0]
    
    with st.sidebar.expander("👤 Customize Portfolio"):
        u_name = st.text_input("Full Name", prof['name'])
        u_title = st.text_input("Job Title", prof['title'])
        u_bio = st.text_area("Bio/Summary", prof['bio'])
        u_img = st.file_uploader("Upload Headshot", type=['jpg', 'png'])
        if st.button("Update Profile"):
            img_v = compress_img(u_img) if u_img else prof['profile_img']
            conn.execute("UPDATE profile SET name=?, title=?, bio=?, profile_img=? WHERE id=1", (u_name, u_title, u_bio, img_v))
            conn.commit()
            st.rerun()

    st.markdown("""<style>.header-card { background: rgba(0,212,255,0.05); border-left: 5px solid #00d4ff; border-radius: 15px; padding: 25px; }</style>""", unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="header-card">', unsafe_allow_html=True)
        hcol1, hcol2 = st.columns([1, 4])
        with hcol1:
            if prof['profile_img']: st.image(prof['profile_img'], use_container_width=True)
            else: st.title("👤")
        with hcol2:
            st.title(prof['name'])
            st.subheader(prof['title'])
            st.write(prof['bio'])
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("🛠️ Global Competency Summary")
    courses_df = pd.read_sql_query("SELECT * FROM courses", conn)
    if not courses_df.empty:
        stats = courses_df.groupby('category')['completed'].mean() * 100
        cols = st.columns(3)
        for i, (cat, val) in enumerate(stats.items()):
            with cols[i % 3]:
                st.write(f"**{cat}**")
                st.progress(val/100)
                st.caption(f"{val:.0f}% Mastery")

# =========================================================
# 7. SYSTEM RECOVERY (DOWNLOAD & RESTORE)
# =========================================================
elif menu == "System Recovery":
    st.title("💾 System Recovery & Backup")
    
    st.subheader("📥 Export System Data")
    st.info("Ensures all current cache is recalled to disk for a solid backup.")
    
    # Forced Checkpoint: Merges WAL data into the main .db file
    conn.execute("PRAGMA wal_checkpoint(FULL);")
    
    with open(DB_NAME, "rb") as f:
        st.download_button(
            label="Download System Backup (.db)",
            data=f,
            file_name=f"AIMecha_Full_Backup_{datetime.now().strftime('%Y%m%d')}.db",
            mime="application/x-sqlite3",
            use_container_width=True
        )
    
    st.divider()
    
    st.subheader("⚠️ Restore System Data")
    res_file = st.file_uploader("Upload Backup File (.db)", type=["db"])
    if res_file:
        lock = st.text_input("Type 'RESTORE' to confirm")
        if lock == "RESTORE" and st.button("🚀 Restore and Reboot", type="primary"):
            conn.close()
            with open(DB_NAME, "wb") as f:
                f.write(res_file.getbuffer())
            st.cache_resource.clear()
            st.success("System Restored. Reloading...")
            st.rerun()

# =========================================================
# 8. DASHBOARD & ADD COURSE
# =========================================================
elif menu == "Dashboard":
    st.title("⚙️ Engineering Dashboard")
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Modules", len(df))
    c2.metric("Completion Rate", f"{df['completed'].mean()*100:.1f}%" if not df.empty else "0%")
    c3.metric("Note Count", pd.read_sql_query("SELECT COUNT(*) FROM notes", conn).iloc[0,0])

elif menu == "Add Course":
    st.title("➕ Add Module")
    with st.form("add_c"):
        cat = st.selectbox("Category", ["Programming", "AI", "Mechatronics", "Electronics"])
        name = st.text_input("Module Name")
        if st.form_submit_button("Add"):
            conn.execute("INSERT INTO courses (category, course_name) VALUES (?, ?)", (cat, name))
            conn.commit()
            st.success("Module Added!")
