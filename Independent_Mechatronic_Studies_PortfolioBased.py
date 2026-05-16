import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import base64
import io
import os
import numpy as np
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="AIMecha Study OS",
    layout="wide",
    page_icon="⚙️"
)

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"
MIT_LOGO_PATH = "MIT-OCW.png"

# =========================================================
# GLOBAL STYLING
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
    width: 100%;
}

div[data-baseweb="input"] {
    border-radius: 12px;
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
}

.course-card {
    background: rgba(255,255,255,0.02);
    padding: 15px;
    border-radius: 15px;
    border: 1px solid #1e293b;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE CONNECTION
# =========================================================

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

conn = get_conn()

# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY,
        category TEXT,
        course_name TEXT,
        completed INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY,
        course_id INTEGER,
        note TEXT,
        sketch_data TEXT,
        image_blob BLOB,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS journal (
        id INTEGER PRIMARY KEY,
        title TEXT,
        entry TEXT,
        sketch_data TEXT,
        image_blob BLOB,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY,
        name TEXT,
        bio TEXT,
        title TEXT,
        profile_img BLOB
    )
    """)

    c.execute("""
    INSERT OR IGNORE INTO profile 
    (id, name, bio, title)
    VALUES
    (
        1,
        'Your Name',
        'Industrial AI & Mechatronics Engineer',
        'Engineering Systems Developer'
    )
    """)

    conn.commit()

init_db()

# =========================================================
# UTILITY FUNCTIONS
# =========================================================

def compress_img(image_file):

    if image_file is None:
        return None

    img = Image.open(image_file)

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    img.thumbnail((1000, 1000))

    buf = io.BytesIO()

    img.save(
        buf,
        format="JPEG",
        quality=80
    )

    return buf.getvalue()

# =========================================================
# MULTIMODAL INPUT
# =========================================================

def multimodal_input(key):

    text = st.text_area(
        "Technical Notes / Observations",
        key=f"text_{key}",
        height=120
    )

    col1, col2 = st.columns(2)

    with col1:

        st.caption("🎨 Engineering Sketchpad")

        canvas = st_canvas(
            fill_color="rgba(0,212,255,0.1)",
            stroke_width=3,
            stroke_color="#00d4ff",
            background_color="#0e1117",
            height=250,
            width=500,
            drawing_mode="freedraw",
            key=f"canvas_{key}"
        )

    with col2:

        st.caption("🖼️ Upload Reference Image")

        img = st.file_uploader(
            "Upload Reference",
            type=["png", "jpg", "jpeg"],
            key=f"img_{key}"
        )

    # =====================================================
    # FIXED SKETCH SAVING
    # =====================================================

    sketch_b64 = None

    if canvas.image_data is not None:

        arr = canvas.image_data.astype("uint8")

        # Detect actual drawing
        if np.any(arr[:, :, 3] > 0):

            raw_img = Image.fromarray(arr, 'RGBA')

            buf = io.BytesIO()

            raw_img.save(buf, format="PNG")

            sketch_b64 = base64.b64encode(
                buf.getvalue()
            ).decode()

    img_blob = compress_img(img) if img else None

    return text, sketch_b64, img_blob

# =========================================================
# SIDEBAR
# =========================================================

if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.title("⚙️ AIMecha OS")

menu = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Courses",
        "Journal",
        "Professional CV",
        "MIT Learning Hub",
        "Add Course",
        "System Recovery"
    ]
)

st.sidebar.divider()

# =========================================================
# MIT QUICK ACCESS HUB
# =========================================================

if os.path.exists(MIT_LOGO_PATH):
    st.sidebar.image(MIT_LOGO_PATH, width=180)

st.sidebar.subheader("🎓 MIT OCW Quick Launch")

mit_courses = {
    "Python Programming":
    "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/",

    "Linear Algebra":
    "https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/",

    "Single Variable Calculus":
    "https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/",

    "Signals & Systems":
    "https://ocw.mit.edu/courses/res-6-007-signals-and-systems-spring-2011/",

    "Feedback Control":
    "https://ocw.mit.edu/courses/6-302-feedback-systems-spring-2007/",

    "Circuits & Electronics":
    "https://ocw.mit.edu/courses/6-002-circuits-and-electronics-spring-2007/",

    "Engineering Dynamics":
    "https://ocw.mit.edu/courses/2-003sc-engineering-dynamics-fall-2011/",

    "Robotics":
    "https://ocw.mit.edu/courses/2-12-introduction-to-robotics-fall-2005/",

    "Underactuated Robotics":
    "https://ocw.mit.edu/courses/6-832-underactuated-robotics-spring-2009/",

    "Deep Learning":
    "https://introtodeeplearning.com/"
}

for course, url in mit_courses.items():

    st.sidebar.markdown(
        f'<a href="{url}" target="_blank">{course}</a>',
        unsafe_allow_html=True
    )

# =========================================================
# DASHBOARD
# =========================================================

if menu == "Dashboard":

    st.title("⚙️ AIMecha Engineering Dashboard")

    df = pd.read_sql_query(
        "SELECT * FROM courses",
        conn
    )

    total_notes = pd.read_sql_query(
        "SELECT COUNT(*) FROM notes",
        conn
    ).iloc[0,0]

    total_journal = pd.read_sql_query(
        "SELECT COUNT(*) FROM journal",
        conn
    ).iloc[0,0]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Modules", len(df))

    completion = (
        df['completed'].mean()*100
        if not df.empty else 0
    )

    c2.metric(
        "Completion Rate",
        f"{completion:.1f}%"
    )

    c3.metric("Technical Notes", total_notes)

    c4.metric("Engineering Logs", total_journal)

    st.divider()

    st.subheader("🚀 AIMecha OS Overview")

    st.info("""
    AIMecha OS is a multimodal engineering knowledge
    management system designed for Industrial AI,
    Robotics, Automation, Embedded Systems,
    and Mechatronics Engineering studies.
    """)

# =========================================================
# COURSES
# =========================================================

elif menu == "Courses":

    st.title("📚 Engineering Study Modules")

    courses = pd.read_sql_query(
        "SELECT * FROM courses",
        conn
    )

    if courses.empty:

        st.warning(
            "No modules added yet."
        )

    else:

        search_note = st.text_input(
            "🔍 Search Notes"
        )

        for _, row in courses.iterrows():

            with st.expander(
                f"📖 {row['course_name']} ({row['category']})",
                expanded=False
            ):

                completed = st.checkbox(
                    "Mark Completed",
                    value=bool(row['completed']),
                    key=f"comp_{row['id']}"
                )

                if completed != bool(row['completed']):

                    conn.execute(
                        """
                        UPDATE courses
                        SET completed=?
                        WHERE id=?
                        """,
                        (
                            int(completed),
                            row['id']
                        )
                    )

                    conn.commit()

                    st.rerun()

                txt, sk, im = multimodal_input(
                    f"course_{row['id']}"
                )

                if st.button(
                    "💾 Save Technical Note",
                    key=f"save_{row['id']}"
                ):

                    conn.execute(
                        """
                        INSERT INTO notes
                        (
                            course_id,
                            note,
                            sketch_data,
                            image_blob,
                            created_at
                        )
                        VALUES (?,?,?,?,?)
                        """,
                        (
                            row['id'],
                            txt,
                            sk,
                            im,
                            datetime.now().strftime(
                                "%Y-%m-%d %H:%M"
                            )
                        )
                    )

                    conn.commit()

                    st.success(
                        "Technical Note Saved!"
                    )

                    st.rerun()

                st.divider()

                notes_df = pd.read_sql_query(
                    """
                    SELECT * FROM notes
                    WHERE course_id=?
                    AND note LIKE ?
                    ORDER BY id DESC
                    """,
                    conn,
                    params=(
                        row['id'],
                        f"%{search_note}%"
                    )
                )

                for _, note in notes_df.iterrows():

                    with st.container(border=True):

                        st.caption(
                            f"📅 {note['created_at']}"
                        )

                        if note['note']:
                            st.write(note['note'])

                        n1, n2 = st.columns(2)

                        if note['sketch_data']:

                            n1.image(
                                base64.b64decode(
                                    note['sketch_data']
                                ),
                                caption="Sketch"
                            )

                        if note['image_blob']:

                            n2.image(
                                note['image_blob'],
                                caption="Reference"
                            )

# =========================================================
# JOURNAL
# =========================================================

elif menu == "Journal":

    st.title("📓 Engineering Journal")

    with st.expander(
        "➕ New Journal Entry",
        expanded=True
    ):

        j_title = st.text_input(
            "Entry Title",
            "Daily Engineering Progress"
        )

        txt, sk, im = multimodal_input(
            "journal_main"
        )

        if st.button("🚀 Commit to Journal"):

            conn.execute(
                """
                INSERT INTO journal
                (
                    title,
                    entry,
                    sketch_data,
                    image_blob,
                    created_at
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    j_title,
                    txt,
                    sk,
                    im,
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M"
                    )
                )
            )

            conn.commit()

            st.success(
                "Journal Entry Saved!"
            )

            st.rerun()

    st.divider()

    search_j = st.text_input(
        "🔍 Search Journal"
    )

    journal_df = pd.read_sql_query(
        """
        SELECT * FROM journal
        WHERE title LIKE ?
        OR entry LIKE ?
        ORDER BY id DESC
        """,
        conn,
        params=(
            f"%{search_j}%",
            f"%{search_j}%"
        )
    )

    for _, j in journal_df.iterrows():

        with st.container(border=True):

            st.subheader(j['title'])

            st.caption(
                f"🕒 {j['created_at']}"
            )

            if j['entry']:
                st.write(j['entry'])

            j1, j2 = st.columns(2)

            if j['sketch_data']:

                j1.image(
                    base64.b64decode(
                        j['sketch_data']
                    ),
                    caption="Engineering Sketch"
                )

            if j['image_blob']:

                j2.image(
                    j['image_blob'],
                    caption="Reference"
                )

# =========================================================
# PROFESSIONAL CV
# =========================================================

elif menu == "Professional CV":

    prof = pd.read_sql_query(
        """
        SELECT * FROM profile
        WHERE id=1
        """,
        conn
    ).iloc[0]

    with st.sidebar.expander(
        "👤 Customize Profile"
    ):

        u_name = st.text_input(
            "Full Name",
            prof['name']
        )

        u_title = st.text_input(
            "Professional Title",
            prof['title']
        )

        u_bio = st.text_area(
            "Professional Summary",
            prof['bio']
        )

        u_img = st.file_uploader(
            "Upload Profile Picture",
            type=['jpg','jpeg','png']
        )

        if st.button("💾 Update Profile"):

            img_v = prof['profile_img']

            if u_img is not None:
                img_v = compress_img(u_img)

            conn.execute(
                """
                UPDATE profile
                SET
                name=?,
                title=?,
                bio=?,
                profile_img=?
                WHERE id=1
                """,
                (
                    u_name,
                    u_title,
                    u_bio,
                    img_v
                )
            )

            conn.commit()

            st.success(
                "Profile Updated!"
            )

            st.rerun()

    # =====================================================
    # HERO SECTION
    # =====================================================

    st.markdown(
        f"""
        <div class="header-card">

        <h1 style="
        font-size:48px;
        color:white;
        margin-bottom:0;
        ">
        {prof['name']}
        </h1>

        <h3 style="
        color:#00d4ff;
        ">
        {prof['title']}
        </h3>

        <p style="
        font-size:18px;
        color:#cbd5e1;
        ">
        {prof['bio']}
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    # =====================================================
    # PROFILE IMAGE
    # =====================================================

    p1, p2 = st.columns([1,3])

    with p1:

        if prof['profile_img'] is not None:

            st.image(
                prof['profile_img'],
                width=250
            )

        else:

            st.markdown("""
            <div style="
            width:250px;
            height:250px;
            border-radius:50%;
            background:#1e293b;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:100px;
            ">
            👤
            </div>
            """,
            unsafe_allow_html=True)

    with p2:

        st.subheader(
            "🎓 MIT OpenCourseWare Studies"
        )

        st.info("""
        Independent Studies in Industrial AI,
        Automation, Robotics, Control Systems,
        Computer Vision, and Mechatronics
        Engineering via MIT OpenCourseWare.
        """)

        st.subheader(
            "⚡ Engineering Focus Areas"
        )

        st.markdown("""
        - Industrial Artificial Intelligence
        - Robotics & Automation
        - Embedded Systems
        - Computer Vision
        - Control Systems
        - Smart Infrastructure
        """)

    st.divider()

    # =====================================================
    # METRICS
    # =====================================================

    courses_df = pd.read_sql_query(
        "SELECT * FROM courses",
        conn
    )

    total_courses = len(courses_df)

    completed_courses = len(
        courses_df[
            courses_df['completed'] == 1
        ]
    )

    notes_count = pd.read_sql_query(
        "SELECT COUNT(*) FROM notes",
        conn
    ).iloc[0,0]

    journal_count = pd.read_sql_query(
        "SELECT COUNT(*) FROM journal",
        conn
    ).iloc[0,0]

    s1,s2,s3,s4 = st.columns(4)

    s1.metric(
        "Modules",
        total_courses
    )

    s2.metric(
        "Completed",
        completed_courses
    )

    s3.metric(
        "Technical Notes",
        notes_count
    )

    s4.metric(
        "Engineering Logs",
        journal_count
    )

    st.divider()

    # =====================================================
    # COMPETENCY MATRIX
    # =====================================================

    st.subheader(
        "🛠️ Engineering Competency Matrix"
    )

    if not courses_df.empty:

        stats = (
            courses_df
            .groupby('category')['completed']
            .mean() * 100
        )

        for cat, val in stats.items():

            st.write(f"### {cat}")

            st.progress(val/100)

            st.caption(
                f"{val:.0f}% competency progression"
            )

    st.divider()

    # =====================================================
    # EXPORT
    # =====================================================

    cv_export = f"""
AIMecha Engineering Portfolio

Name:
{prof['name']}

Title:
{prof['title']}

Professional Summary:
{prof['bio']}

Modules Completed:
{completed_courses}/{total_courses}

Technical Notes:
{notes_count}

Engineering Logs:
{journal_count}
"""

    st.download_button(
        "📄 Download Engineering Portfolio",
        data=cv_export,
        file_name="AIMecha_Engineering_Portfolio.txt"
    )

# =========================================================
# MIT LEARNING HUB
# =========================================================

elif menu == "MIT Learning Hub":

    st.title("🎓 MIT Learning Hub")

    st.info("""
    Quick access portal for your MIT OpenCourseWare
    Industrial AI & Mechatronics roadmap.
    """)

    for course, url in mit_courses.items():

        st.markdown(f"""
        <div class="course-card">
        <h3>{course}</h3>
        <a href="{url}" target="_blank">
        🚀 Launch Course
        </a>
        </div>
        <br>
        """, unsafe_allow_html=True)

# =========================================================
# ADD COURSE
# =========================================================

elif menu == "Add Course":

    st.title("➕ Add Engineering Module")

    with st.form("add_course"):

        cat = st.selectbox(
            "Category",
            [
                "Programming",
                "Artificial Intelligence",
                "Mechatronics",
                "Electronics",
                "Control Systems",
                "Robotics",
                "Computer Vision",
                "Embedded Systems"
            ]
        )

        name = st.text_input(
            "Module Name"
        )

        submit = st.form_submit_button(
            "🚀 Add Module"
        )

        if submit:

            conn.execute(
                """
                INSERT INTO courses
                (
                    category,
                    course_name
                )
                VALUES (?,?)
                """,
                (
                    cat,
                    name
                )
            )

            conn.commit()

            st.success(
                "Engineering Module Added!"
            )

# =========================================================
# SYSTEM RECOVERY
# =========================================================

elif menu == "System Recovery":

    st.title("💾 System Recovery")

    st.subheader("📥 Backup Database")

    conn.execute(
        "PRAGMA wal_checkpoint(FULL);"
    )

    with open(DB_NAME, "rb") as f:

        st.download_button(
            label="Download AIMecha Backup",
            data=f,
            file_name=f"""
AIMecha_Backup_
{datetime.now().strftime('%Y%m%d')}
.db
""",
            mime="application/x-sqlite3"
        )

    st.divider()

    st.subheader("⚠️ Restore Database")

    restore_file = st.file_uploader(
        "Upload Backup",
        type=["db"]
    )

    if restore_file:

        confirm = st.text_input(
            "Type RESTORE to confirm"
        )

        if (
            confirm == "RESTORE"
            and st.button("🚀 Restore System")
        ):

            conn.close()

            with open(DB_NAME, "wb") as f:
                f.write(
                    restore_file.getbuffer()
                )

            st.cache_resource.clear()

            st.success(
                "System Restored!"
            )

            st.rerun()
