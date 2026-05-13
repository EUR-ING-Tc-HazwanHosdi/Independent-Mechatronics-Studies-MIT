# Industrial AI Mechatronics Study Tracker
# Streamlit Production-Ready Version (With Upload Function)

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os

# -----------------------------
# CONFIG
# -----------------------------
DB_NAME = "study_tracker.db"
UPLOAD_FOLDER = "uploads"
LOGO_PATH = "AIMECHA.png"  # <-- Put your AIMecha logo image here

st.sidebar.image(LOGO_PATH, width=500)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="Independent Studies / OpenCourseWare (Non-Degree), Mechatronics Engineering, Artificial Intelligence & Automation",
    layout="wide"
)

st.title("⚙️ Independent Studies (Non-Degree) — Mechatronics Engineering, Artificial Intelligence & Automation (MIT OpenCourseWare-based) Study Tracker")

# -----------------------------
# DATABASE
# -----------------------------

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
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

    c.execute("""
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT,
        file_name TEXT,
        file_path TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def get_data():
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM courses", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame(columns=["id","category","course_name","completed","notes"])


def add_course(category, course_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO courses (category, course_name) VALUES (?, ?)", (category, course_name))
    conn.commit()
    conn.close()


def update_course(course_id, completed, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE courses SET completed=?, notes=? WHERE id=?", (completed, notes, course_id))
    conn.commit()
    conn.close()


def add_journal(entry):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO journal (entry, created_at) VALUES (?, ?)", (entry, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def save_exercise(course_name, uploaded_file):
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO exercises (course_name, file_name, file_path, created_at)
        VALUES (?, ?, ?, ?)
    """, (course_name, uploaded_file.name, file_path, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def get_exercises():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM exercises", conn)
    conn.close()
    return df

# -----------------------------
# INIT
# -----------------------------
init_db()

# -----------------------------
# NAVIGATION
# -----------------------------
menu = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Courses", "Add Course", "Upload Exercise", "Journal", "Analytics", "Export"]
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
        progress = float(df["completed"].mean())
        st.progress(progress)
        st.metric("Overall Completion", f"{progress*100:.1f}%")

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
            col1, col2, col3 = st.columns([3,1,3])

            with col1:
                st.write(f"**{row['course_name']}** ({row['category']})")

            with col2:
                status = st.checkbox("Done", value=bool(row["completed"]), key=row["id"])

            with col3:
                notes = st.text_input("Notes", value=row["notes"], key=f"n{row['id']}")

            update_course(row["id"], int(status), notes)

# -----------------------------
# ADD COURSE
# -----------------------------
elif menu == "Add Course":
    st.subheader("➕ Add New Course")

    category = st.selectbox(
        "Category",
        ["Mathematics","Physics","Programming","Electronics","Control Systems","Robotics","Computer Vision","Machine Learning","Embedded Systems","Projects"]
    )

    course_name = st.text_input("Course Name")

    if st.button("Add Course"):
        if course_name.strip():
            add_course(category, course_name.strip())
            st.success("Course added.")

# -----------------------------
# UPLOAD EXERCISE
# -----------------------------
elif menu == "Upload Exercise":
    st.subheader("📤 Upload Completed Exercise / Assignment")

    df = get_data()

    if df.empty:
        st.warning("Add courses first.")
    else:
        course_name = st.selectbox("Select Course", df["course_name"].tolist())

        uploaded_file = st.file_uploader("Upload file (PDF, image, code, etc.)")

        if uploaded_file is not None:
            if st.button("Save Exercise"):
                save_exercise(course_name, uploaded_file)
                st.success("Exercise uploaded and saved.")

    st.divider()
    st.subheader("📁 Uploaded Exercises")

    ex = get_exercises()

    if ex.empty:
        st.info("No exercises uploaded yet.")
    else:
        st.dataframe(ex)

# -----------------------------
# JOURNAL
# -----------------------------
elif menu == "Journal":
    st.subheader("📝 Engineering Journal")

    entry = st.text_area("Write your reflections / ideas")

    if st.button("Save Entry"):
        if entry.strip():
            add_journal(entry)
            st.success("Saved successfully.")

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

    st.info("Use this export for portfolio or LinkedIn proof of learning.")
