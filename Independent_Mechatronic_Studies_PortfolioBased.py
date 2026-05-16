# =========================================================
# AIMecha Study OS
# Full Corrected Production Version
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
# FILES
# =========================================================

DB_NAME = "aimecha_study_os.db"
LOGO_PATH = "AIMECHA.png"
MIT_LOGO_PATH = "MIT-OCW.png"

# =========================================================
# CUSTOM CSS
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
    background: rgba(255,255,255,0.03);
    border-radius: 15px;
    padding: 20px;
    border: 1px solid #1e293b;
    margin-bottom: 15px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE CONNECTION
# =========================================================

@st.cache_resource
def get_conn():

    conn = sqlite3.connect(
        DB_NAME,
        check_same_thread=False
    )

    conn.execute(
        "PRAGMA journal_mode=WAL;"
    )

    return conn

conn = get_conn()

# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    c = conn.cursor()

    # =====================================================
    # COURSES
    # =====================================================

    c.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY,
        category TEXT,
        course_name TEXT,
        completed INTEGER DEFAULT 0
    )
    """)

    # =====================================================
    # NOTES
    # =====================================================

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

    # =====================================================
    # JOURNAL
    # =====================================================

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

    # =====================================================
    # PROFILE
    # =====================================================

    c.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY,
        name TEXT,
        bio TEXT,
        title TEXT,
        profile_img BLOB
    )
    """)

    # =====================================================
    # SAFE MIGRATIONS
    # =====================================================

    try:
        c.execute(
            "ALTER TABLE notes ADD COLUMN updated_at TEXT"
        )
    except sqlite3.OperationalError:
        pass

    try:
        c.execute(
            "ALTER TABLE journal ADD COLUMN updated_at TEXT"
        )
    except sqlite3.OperationalError:
        pass

    # =====================================================
    # DEFAULT PROFILE
    # =====================================================

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
# UTILITIES
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

    c1, c2 = st.columns(2)

    with c1:

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

    with c2:

        st.caption("🖼️ Upload Reference")

        img = st.file_uploader(
            "Upload Image",
            type=["png", "jpg", "jpeg"],
            key=f"img_{key}"
        )

    sketch_b64 = None

    # =====================================================
    # FIXED SKETCH DETECTION
    # =====================================================

    if canvas.image_data is not None:

        arr = canvas.image_data.astype("uint8")

        if np.any(arr[:, :, 3] > 0):

            raw_img = Image.fromarray(
                arr,
                'RGBA'
            )

            buf = io.BytesIO()

            raw_img.save(
                buf,
                format="PNG"
            )

            sketch_b64 = base64.b64encode(
                buf.getvalue()
            ).decode()

    img_blob = compress_img(img) if img else None

    return text, sketch_b64, img_blob

# =========================================================
# SIDEBAR
# =========================================================

if os.path.exists(LOGO_PATH):

    st.sidebar.image(
        LOGO_PATH,
        use_container_width=True
    )

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
        "Management Center",
        "Add Course",
        "System Recovery"
    ]
)

st.sidebar.divider()

# =========================================================
# MIT LOGO
# =========================================================

if os.path.exists(MIT_LOGO_PATH):

    st.sidebar.image(
        MIT_LOGO_PATH,
        width=180
    )

# =========================================================
# MIT QUICK ACCESS
# =========================================================

st.sidebar.subheader(
    "🎓 MIT OCW Quick Launch"
)

mit_courses = {

    "Python Programming":
    "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/",

    "Linear Algebra":
    "https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/",

    "Signals & Systems":
    "https://ocw.mit.edu/courses/res-6-007-signals-and-systems-spring-2011/",

    "Feedback Control":
    "https://ocw.mit.edu/courses/6-302-feedback-systems-spring-2007/",

    "Robotics":
    "https://ocw.mit.edu/courses/2-12-introduction-to-robotics-fall-2005/",

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

    st.title(
        "⚙️ AIMecha Engineering Dashboard"
    )

    df = pd.read_sql_query(
        "SELECT * FROM courses",
        conn
    )

    notes_count = pd.read_sql_query(
        "SELECT COUNT(*) FROM notes",
        conn
    ).iloc[0,0]

    journal_count = pd.read_sql_query(
        "SELECT COUNT(*) FROM journal",
        conn
    ).iloc[0,0]

    c1,c2,c3,c4 = st.columns(4)

    c1.metric(
        "Modules",
        len(df)
    )

    completion = (
        df['completed'].mean()*100
        if not df.empty else 0
    )

    c2.metric(
        "Completion",
        f"{completion:.1f}%"
    )

    c3.metric(
        "Technical Notes",
        notes_count
    )

    c4.metric(
        "Journal Logs",
        journal_count
    )

    st.divider()

    st.info("""
    AIMecha OS is a multimodal engineering
    knowledge management system for Industrial AI,
    Robotics, Automation, and Mechatronics studies.
    """)

# =========================================================
# COURSES
# =========================================================

elif menu == "Courses":

    st.title(
        "📚 Engineering Study Modules"
    )

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

                # =========================================
                # EDIT COURSE
                # =========================================

                m1, m2 = st.columns(2)

                with m1:

                    with st.popover("✏️ Edit Module"):

                        new_name = st.text_input(
                            "Module Name",
                            value=row['course_name'],
                            key=f"edit_course_name_{row['id']}"
                        )

                        categories = [
                            "Programming",
                            "Artificial Intelligence",
                            "Mechatronics",
                            "Electronics",
                            "Control Systems",
                            "Robotics",
                            "Computer Vision",
                            "Embedded Systems"
                        ]

                        new_cat = st.selectbox(
                            "Category",
                            categories,
                            index=categories.index(
                                row['category']
                            ) if row['category'] in categories else 0,
                            key=f"edit_course_cat_{row['id']}"
                        )

                        if st.button(
                            "💾 Save Changes",
                            key=f"save_course_{row['id']}"
                        ):

                            conn.execute(
                                """
                                UPDATE courses
                                SET
                                course_name=?,
                                category=?
                                WHERE id=?
                                """,
                                (
                                    new_name,
                                    new_cat,
                                    row['id']
                                )
                            )

                            conn.commit()

                            st.success(
                                "Module Updated!"
                            )

                            st.rerun()

                # =========================================
                # DELETE COURSE
                # =========================================

                with m2:

                    with st.popover("🗑️ Delete Module"):

                        st.warning("""
                        This deletes:
                        - module
                        - notes
                        """)

                        if st.button(
                            "🚨 Confirm Delete",
                            key=f"delete_course_{row['id']}"
                        ):

                            conn.execute(
                                """
                                DELETE FROM notes
                                WHERE course_id=?
                                """,
                                (row['id'],)
                            )

                            conn.execute(
                                """
                                DELETE FROM courses
                                WHERE id=?
                                """,
                                (row['id'],)
                            )

                            conn.commit()

                            st.success(
                                "Module Deleted!"
                            )

                            st.rerun()

                # =========================================
                # COMPLETE MODULE
                # =========================================

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

                st.divider()

                # =========================================
                # ADD NOTE
                # =========================================

                txt, sk, im = multimodal_input(
                    f"course_{row['id']}"
                )

                if st.button(
                    "💾 Save Technical Note",
                    key=f"save_note_{row['id']}"
                ):

                    conn.execute(
                        """
                        INSERT INTO notes
                        (
                            course_id,
                            note,
                            sketch_data,
                            image_blob,
                            created_at,
                            updated_at
                        )
                        VALUES (?,?,?,?,?,?)
                        """,
                        (
                            row['id'],
                            txt,
                            sk,
                            im,
                            datetime.now().strftime(
                                "%Y-%m-%d %H:%M"
                            ),
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

                # =========================================
                # LOAD NOTES
                # =========================================

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

                        top1, top2, top3 = st.columns([6,1,1])

                        top1.caption(
                            f"""
                            📅 Created:
                            {note['created_at']}
                            """
                        )

                        # =================================
                        # EDIT NOTE
                        # =================================

                        with top2:

                            with st.popover("✏️"):

                                edit_note = st.text_area(
                                    "Edit Note",
                                    value=note['note'],
                                    key=f"edit_note_{note['id']}"
                                )

                                if st.button(
                                    "💾 Update",
                                    key=f"update_note_{note['id']}"
                                ):

                                    conn.execute(
                                        """
                                        UPDATE notes
                                        SET
                                        note=?,
                                        updated_at=?
                                        WHERE id=?
                                        """,
                                        (
                                            edit_note,
                                            datetime.now().strftime(
                                                "%Y-%m-%d %H:%M"
                                            ),
                                            note['id']
                                        )
                                    )

                                    conn.commit()

                                    st.success(
                                        "Note Updated!"
                                    )

                                    st.rerun()

                        # =================================
                        # DELETE NOTE
                        # =================================

                        with top3:

                            if st.button(
                                "🗑️",
                                key=f"delete_note_{note['id']}"
                            ):

                                conn.execute(
                                    """
                                    DELETE FROM notes
                                    WHERE id=?
                                    """,
                                    (note['id'],)
                                )

                                conn.commit()

                                st.success(
                                    "Note Deleted!"
                                )

                                st.rerun()

                        if note['note']:

                            st.write(
                                note['note']
                            )

                        n1, n2 = st.columns(2)

                        if note['sketch_data']:

                            n1.image(
                                base64.b64decode(
                                    note['sketch_data']
                                ),
                                caption="Engineering Sketch"
                            )

                        if note['image_blob']:

                            n2.image(
                                note['image_blob'],
                                caption="Reference Image"
                            )

# =========================================================
# JOURNAL
# =========================================================

elif menu == "Journal":

    st.title(
        "📓 Engineering Journal"
    )

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

        if st.button(
            "🚀 Commit to Journal"
        ):

            conn.execute(
                """
                INSERT INTO journal
                (
                    title,
                    entry,
                    sketch_data,
                    image_blob,
                    created_at,
                    updated_at
                )
                VALUES (?,?,?,?,?,?)
                """,
                (
                    j_title,
                    txt,
                    sk,
                    im,
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M"
                    )
                )
            )

            conn.commit()

            st.success(
                "Journal Saved!"
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

            jh1, jh2, jh3 = st.columns([6,1,1])

            jh1.subheader(
                j['title']
            )

            # =========================================
            # EDIT JOURNAL
            # =========================================

            with jh2:

                with st.popover("✏️"):

                    edit_title = st.text_input(
                        "Title",
                        value=j['title'],
                        key=f"edit_j_title_{j['id']}"
                    )

                    edit_entry = st.text_area(
                        "Entry",
                        value=j['entry'],
                        key=f"edit_j_entry_{j['id']}"
                    )

                    if st.button(
                        "💾 Save Journal",
                        key=f"save_journal_{j['id']}"
                    ):

                        conn.execute(
                            """
                            UPDATE journal
                            SET
                            title=?,
                            entry=?,
                            updated_at=?
                            WHERE id=?
                            """,
                            (
                                edit_title,
                                edit_entry,
                                datetime.now().strftime(
                                    "%Y-%m-%d %H:%M"
                                ),
                                j['id']
                            )
                        )

                        conn.commit()

                        st.success(
                            "Journal Updated!"
                        )

                        st.rerun()

            # =========================================
            # DELETE JOURNAL
            # =========================================

            with jh3:

                if st.button(
                    "🗑️",
                    key=f"delete_journal_{j['id']}"
                ):

                    conn.execute(
                        """
                        DELETE FROM journal
                        WHERE id=?
                        """,
                        (j['id'],)
                    )

                    conn.commit()

                    st.success(
                        "Journal Deleted!"
                    )

                    st.rerun()

            st.caption(
                f"""
                🕒 Created:
                {j['created_at']}
                """
            )

            if j['entry']:

                st.write(
                    j['entry']
                )

            jc1, jc2 = st.columns(2)

            if j['sketch_data']:

                jc1.image(
                    base64.b64decode(
                        j['sketch_data']
                    ),
                    caption="Engineering Sketch"
                )

            if j['image_blob']:

                jc2.image(
                    j['image_blob'],
                    caption="Reference"
                )

# =========================================================
# PROFESSIONAL CV
# =========================================================

elif menu == "Professional CV":

    st.title(
        "👤 Professional Engineering Portfolio"
    )

    st.info("""
    CV section can be extended later with:
    - PDF export
    - certifications
    - recruiter portfolio
    - project showcase
    """)

# =========================================================
# MIT HUB
# =========================================================

elif menu == "MIT Learning Hub":

    st.title(
        "🎓 MIT Learning Hub"
    )

    for course, url in mit_courses.items():

        st.markdown(f"""
        <div class="course-card">
        <h3>{course}</h3>
        <a href="{url}" target="_blank">
        🚀 Launch Course
        </a>
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# MANAGEMENT CENTER
# =========================================================

elif menu == "Management Center":

    st.title(
        "🛠️ AIMecha Management Center"
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "Courses",
            "Notes",
            "Journal"
        ]
    )

    with tab1:

        all_courses = pd.read_sql_query(
            "SELECT * FROM courses",
            conn
        )

        st.dataframe(
            all_courses,
            use_container_width=True
        )

    with tab2:

        all_notes = pd.read_sql_query(
            """
            SELECT
            notes.id,
            courses.course_name,
            notes.note,
            notes.created_at

            FROM notes

            LEFT JOIN courses
            ON notes.course_id = courses.id

            ORDER BY notes.id DESC
            """,
            conn
        )

        st.dataframe(
            all_notes,
            use_container_width=True
        )

    with tab3:

        all_journal = pd.read_sql_query(
            """
            SELECT *
            FROM journal
            ORDER BY id DESC
            """,
            conn
        )

        st.dataframe(
            all_journal,
            use_container_width=True
        )

# =========================================================
# ADD COURSE
# =========================================================

elif menu == "Add Course":

    st.title(
        "➕ Add Engineering Module"
    )

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
                "Module Added!"
            )

# =========================================================
# SYSTEM RECOVERY
# =========================================================

elif menu == "System Recovery":

    st.title(
        "💾 System Recovery"
    )

    conn.execute(
        "PRAGMA wal_checkpoint(FULL);"
    )

    with open(DB_NAME, "rb") as f:

        st.download_button(
            label="📥 Download Backup",
            data=f,
            file_name=f"AIMecha_Backup_{datetime.now().strftime('%Y%m%d')}.db",
            mime="application/x-sqlite3"
        )

    st.divider()

    restore_file = st.file_uploader(
        "Upload Backup File",
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
