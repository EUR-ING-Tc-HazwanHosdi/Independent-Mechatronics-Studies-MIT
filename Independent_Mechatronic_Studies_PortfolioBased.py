# AIMecha Study OS v4 — Notes + Journal + Exercise + DELETE SYSTEM

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="AIMecha Study OS",
    layout="wide"
)

DB_NAME = "study_tracker.db"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.title("⚙️ AIMecha Study OS — Full Learning Management System")

# -----------------------------
# DB CONNECTION
# -----------------------------
def conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    c = conn().cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        course_name TEXT,
        completed INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        note TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        entry TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        course_name TEXT,
        file_name TEXT,
        file_path TEXT,
        file_type TEXT,
        created_at TEXT
    )
    """)

    conn().commit()


init_db()

# -----------------------------
# COURSES
# -----------------------------
def get_courses():
    return pd.read_sql_query("SELECT * FROM courses", conn())


def add_course(cat, name):
    c = conn().cursor()
    c.execute("INSERT INTO courses (category, course_name) VALUES (?,?)", (cat, name))
    conn().commit()


def update_course(cid, done):
    c = conn().cursor()
    c.execute("UPDATE courses SET completed=? WHERE id=?", (done, cid))
    conn().commit()

# -----------------------------
# NOTES
# -----------------------------
def add_note(course_id, note):
    c = conn().cursor()
    c.execute(
        "INSERT INTO notes (course_id, note, created_at) VALUES (?,?,?)",
        (course_id, note, datetime.now().isoformat())
    )
    conn().commit()


def get_notes(course_id):
    return pd.read_sql_query(
        "SELECT * FROM notes WHERE course_id=? ORDER BY created_at DESC",
        conn(),
        params=(course_id,)
    )


def delete_note(note_id):
    c = conn().cursor()
    c.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn().commit()

# -----------------------------
# JOURNAL
# -----------------------------
def add_journal(title, entry):
    c = conn().cursor()
    c.execute(
        "INSERT INTO journal (title, entry, created_at) VALUES (?,?,?)",
        (title, entry, datetime.now().isoformat())
    )
    conn().commit()


def get_journal():
    return pd.read_sql_query(
        "SELECT * FROM journal ORDER BY created_at DESC",
        conn()
    )


def delete_journal(journal_id):
    c = conn().cursor()
    c.execute("DELETE FROM journal WHERE id=?", (journal_id,))
    conn().commit()

# -----------------------------
# EXERCISES
# -----------------------------
def save_exercise(course_id, course_name, uploaded_file):
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    c = conn().cursor()
    c.execute("""
        INSERT INTO exercises 
        (course_id, course_name, file_name, file_path, file_type, created_at)
        VALUES (?,?,?,?,?,?)
    """, (
        course_id,
        course_name,
        uploaded_file.name,
        file_path,
        uploaded_file.type,
        datetime.now().isoformat()
    ))

    conn().commit()


def get_exercises():
    return pd.read_sql_query("SELECT * FROM exercises ORDER BY created_at DESC", conn())

# -----------------------------
# NAVIGATION
# -----------------------------
menu = st.sidebar.radio(
    "Navigation",
    ["Courses", "Add Course", "Journal", "Exercises", "Analytics"]
)

# =========================================================
# COURSES + NOTES (WITH DELETE)
# =========================================================
if menu == "Courses":
    st.subheader("📚 Courses + Notes Management")

    df = get_courses()

    if df.empty:
        st.warning("No courses yet.")
    else:
        for _, row in df.iterrows():

            st.markdown("---")
            st.write(f"## {row['course_name']} ({row['category']})")

            done = st.checkbox(
                "Completed",
                value=bool(row["completed"]),
                key=f"done_{row['id']}"
            )
            update_course(row["id"], int(done))

            # -------------------------
            # ADD NOTE
            # -------------------------
            st.write("### 📝 Add Notes")
            note = st.text_area(
                "Write note (multi-paragraph supported)",
                key=f"note_{row['id']}",
                height=120
            )

            if st.button("Save Note", key=f"save_note_{row['id']}"):
                if note.strip():
                    add_note(row["id"], note)
                    st.success("Saved")

            # -------------------------
            # NOTES HISTORY + DELETE
            # -------------------------
            notes = get_notes(row["id"])

            st.write("### 📒 Notes History")

            for _, n in notes.iterrows():
                col1, col2 = st.columns([6, 1])

                with col1:
                    st.markdown(
                        f"""
                        <div style="
                            padding:10px;
                            border-radius:10px;
                            background:#111;
                            margin-bottom:8px;
                            border:1px solid #333;
                        ">
                        {n['note'].replace('\n','<br>')}
                        <br><small>{n['created_at']}</small>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with col2:
                    if st.button("🗑 Delete", key=f"del_note_{n['id']}"):
                        delete_note(n["id"])
                        st.rerun()

# =========================================================
# ADD COURSE
# =========================================================
elif menu == "Add Course":
    st.subheader("➕ Add Course")

    cat = st.selectbox(
        "Category",
        ["Math","Physics","Programming","AI","Robotics","Electronics"]
    )

    name = st.text_input("Course Name")

    if st.button("Add"):
        if name.strip():
            add_course(cat, name)
            st.success("Added")

# =========================================================
# JOURNAL (WITH DELETE)
# =========================================================
elif menu == "Journal":
    st.subheader("🧠 Engineering Journal")

    title = st.text_input("Title")

    entry = st.text_area(
        "Write journal entry (multi-paragraph supported)",
        height=150
    )

    if st.button("Save Journal"):
        if entry.strip():
            add_journal(title if title else "Untitled", entry)
            st.success("Saved")

    st.divider()

    df = get_journal()

    st.write("## 📖 Journal History")

    for _, j in df.iterrows():

        col1, col2 = st.columns([6,1])

        with col1:
            st.markdown(
                f"""
                <div style="
                    padding:10px;
                    border-radius:10px;
                    background:#0f0f0f;
                    margin-bottom:8px;
                    border:1px solid #333;
                ">
                <h4>{j['title']}</h4>
                <p>{j['entry'].replace('\n','<br>')}</p>
                <small>{j['created_at']}</small>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            if st.button("🗑 Delete", key=f"del_j_{j['id']}"):
                delete_journal(j["id"])
                st.rerun()

# =========================================================
# EXERCISES
# =========================================================
elif menu == "Exercises":
    st.subheader("📤 Exercise / Assignment / Quiz Uploads")

    df = get_courses()

    if df.empty:
        st.warning("Add courses first.")
    else:
        course_name = st.selectbox("Select Course", df["course_name"].tolist())
        course_id = df[df["course_name"] == course_name]["id"].values[0]

        uploaded_file = st.file_uploader(
            "Upload file",
            type=["pdf","png","jpg","jpeg","py","ipynb","docx"]
        )

        if uploaded_file:
            if st.button("Save File"):
                save_exercise(course_id, course_name, uploaded_file)
                st.success("Saved")

    st.divider()

    st.write("## 📁 Uploaded Files")

    ex = get_exercises()

    for _, row in ex.iterrows():

        st.markdown(
            f"""
            <div style="
                padding:10px;
                border-radius:10px;
                background:#111;
                margin-bottom:8px;
                border:1px solid #333;
            ">
            <b>{row['course_name']}</b><br>
            {row['file_name']}<br>
            <small>{row['created_at']}</small>
            </div>
            """,
            unsafe_allow_html=True
        )

        with open(row["file_path"], "rb") as f:
            st.download_button(
                "Download",
                f,
                file_name=row["file_name"],
                key=f"dl_{row['id']}"
            )

# =========================================================
# ANALYTICS
# =========================================================
elif menu == "Analytics":
    st.subheader("📊 Analytics")

    df = get_courses()

    if not df.empty:
        st.bar_chart(df.groupby("category")["completed"].mean() * 100)
        st.dataframe(df)
