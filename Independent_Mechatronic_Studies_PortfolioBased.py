# AIMecha Study Tracker v2 (Multi-Notes + Multi-Journal System)

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os

# -----------------------------
# CONFIG (MUST BE FIRST)
# -----------------------------
st.set_page_config(
    page_title="AIMecha Study OS",
    layout="wide"
)

DB_NAME = "study_tracker.db"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.title("⚙️ AIMecha Study OS — AI Mechatronics Tracker")

# -----------------------------
# DATABASE
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

    # MULTI NOTES TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        note TEXT,
        created_at TEXT
    )
    """)

    # MULTI JOURNAL TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        entry TEXT,
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
# NOTES SYSTEM (MULTI ENTRY)
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

# -----------------------------
# JOURNAL SYSTEM (MULTI ENTRY)
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

# -----------------------------
# NAVIGATION
# -----------------------------
menu = st.sidebar.radio(
    "Navigation",
    ["Courses", "Add Course", "Journal", "Analytics"]
)

# =========================================================
# COURSES + NOTES (MULTI BAR SYSTEM)
# =========================================================
if menu == "Courses":
    st.subheader("📚 Courses + Notes System")

    df = get_courses()

    if df.empty:
        st.warning("No courses yet.")
    else:
        for _, row in df.iterrows():

            st.markdown("---")
            st.write(f"## {row['course_name']} ({row['category']})")

            # completion
            done = st.checkbox(
                "Completed",
                value=bool(row["completed"]),
                key=f"done_{row['id']}"
            )
            update_course(row["id"], int(done))

            # -------------------------
            # MULTI NOTE INPUT BAR
            # -------------------------
            st.write("### 📝 Add Notes (multi-paragraph supported)")

            note_input = st.text_area(
                "Write new note",
                key=f"note_{row['id']}",
                height=120
            )

            if st.button("➕ Save Note", key=f"save_note_{row['id']}"):
                if note_input.strip():
                    add_note(row["id"], note_input)
                    st.success("Note saved")

            # -------------------------
            # DISPLAY ALL NOTES
            # -------------------------
            notes = get_notes(row["id"])

            st.write("### 📒 Saved Notes")

            if notes.empty:
                st.info("No notes yet.")
            else:
                for _, n in notes.iterrows():
                    st.markdown(
                        f"""
                        <div style="
                            padding:12px;
                            border-radius:12px;
                            background:#111;
                            margin-bottom:10px;
                            border:1px solid #333;
                        ">
                        <b>Note:</b><br>
                        {n['note'].replace('\n','<br>')}
                        <br><br>
                        <small>{n['created_at']}</small>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

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
# JOURNAL (MULTI ENTRY SYSTEM UPGRADED)
# =========================================================
elif menu == "Journal":
    st.subheader("🧠 Engineering Journal (Multi Entry System)")

    # -------------------------
    # NEW JOURNAL INPUT BAR
    # -------------------------
    title = st.text_input("Journal Title")

    entry = st.text_area(
        "Write your journal entry (multi-paragraph supported)",
        height=150
    )

    if st.button("➕ Save Journal Entry"):
        if entry.strip():
            add_journal(title if title else "Untitled", entry)
            st.success("Journal saved")

    st.divider()

    # -------------------------
    # DISPLAY JOURNAL HISTORY
    # -------------------------
    df = get_journal()

    st.write("## 📖 Journal History")

    if df.empty:
        st.info("No journal entries yet.")
    else:
        for _, j in df.iterrows():
            st.markdown(
                f"""
                <div style="
                    padding:12px;
                    border-radius:12px;
                    background:#0f0f0f;
                    margin-bottom:10px;
                    border:1px solid #333;
                ">
                <h4>{j['title']}</h4>
                <p>{j['entry'].replace('\n','<br>')}</p>
                <small>{j['created_at']}</small>
                </div>
                """,
                unsafe_allow_html=True
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
