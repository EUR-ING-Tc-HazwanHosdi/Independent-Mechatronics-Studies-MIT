import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
DB_NAME = "study_tracker.db"

st.set_page_config(
    page_title="Industrial AI Mechatronics Tracker",
    layout="wide"
)

st.title("⚙️ Industrial AI Mechatronics Study Tracker")

# -----------------------------
# DATABASE
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        course_name TEXT,
        completed INTEGER DEFAULT 0,
        notes TEXT DEFAULT ''
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def get_data():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM courses", conn)
    conn.close()
    return df


def add_course(category, course_name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO courses (category, course_name) VALUES (?, ?)",
        (category, course_name)
    )
    conn.commit()
    conn.close()


def update_course(course_id, completed, notes):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "UPDATE courses SET completed=?, notes=? WHERE id=?",
        (completed, notes, course_id)
    )
    conn.commit()
    conn.close()


def add_journal(entry):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO journal (entry, created_at) VALUES (?, ?)",
        (entry, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


# -----------------------------
# INIT
# -----------------------------
init_db()

# -----------------------------
# NAVIGATION
# -----------------------------
menu = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Courses", "Add Course", "Journal", "Analytics", "Export"]
)

# -----------------------------
# DASHBOARD
# -----------------------------
if menu == "Dashboard":
    st.subheader("📊 Progress Overview")

    df = get_data()

    if df.empty:
        st.warning("No courses added yet.")
    else:
        progress = df["completed"].mean()
        st.progress(float(progress))
        st.metric("Overall Completion", f"{progress*100:.1f}%")

        st.write("### Category Breakdown")
        st.dataframe(df.groupby("category")["completed"].mean())

# -----------------------------
# COURSES
# -----------------------------
elif menu == "Courses":
    st.subheader("📚 Course Tracker")

    df = get_data()

    if df.empty:
        st.info("No courses yet.")
    else:
        for _, row in df.iterrows():
            col1, col2, col3 = st.columns([3, 1, 3])

            with col1:
                st.write(f"**{row['course_name']}** ({row['category']})")

            with col2:
                status = st.checkbox(
                    "Done",
                    value=bool(row["completed"]),
                    key=row["id"]
                )

            with col3:
                notes = st.text_input(
                    "Notes",
                    value=row["notes"],
                    key=f"n{row['id']}"
                )

            update_course(row["id"], int(status), notes)

# -----------------------------
# ADD COURSE
# -----------------------------
elif menu == "Add Course":
    st.subheader("➕ Add New Course")

    category = st.selectbox(
        "Category",
        [
            "Mathematics", "Physics", "Programming", "Electronics",
            "Control Systems", "Robotics", "Computer Vision",
            "Machine Learning", "Embedded Systems", "Projects"
        ]
    )

    course_name = st.text_input("Course Name")

    if st.button("Add"):
        if course_name.strip():
            add_course(category, course_name)
            st.success("Course added.")
        else:
            st.error("Course name cannot be empty.")

# -----------------------------
# JOURNAL
# -----------------------------
elif menu == "Journal":
    st.subheader("📝 Engineering Journal")

    entry = st.text_area("Write your study reflection / ideas")

    if st.button("Save Entry"):
        if entry.strip():
            add_journal(entry)
            st.success("Saved")
        else:
            st.error("Entry cannot be empty.")

# -----------------------------
# ANALYTICS
# -----------------------------
elif menu == "Analytics":
    st.subheader("📈 Learning Analytics")

    df = get_data()

    if not df.empty:
        st.bar_chart(df.groupby("category")["completed"].mean())
        st.dataframe(df)

# -----------------------------
# EXPORT
# -----------------------------
elif menu == "Export":
    st.subheader("📤 Export Data")

    df = get_data()
    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download CSV",
        csv,
        "study_tracker.csv",
        "text/csv"
    )

    st.info("Use this for GitHub portfolio or LinkedIn evidence of self-study.")
