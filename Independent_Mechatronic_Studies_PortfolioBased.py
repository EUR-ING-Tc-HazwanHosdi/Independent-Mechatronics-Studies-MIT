import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Charts
import plotly.express as px
import plotly.graph_objects as go

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="AIMecha Study OS",
    layout="wide"
)

DB_NAME = "study_tracker.db"
UPLOAD_FOLDER = "uploads"
LOGO_PATH = "AIMECHA.png"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================================================
# LOGO
# =========================================================
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, width=250)
else:
    st.sidebar.warning("Logo not found: AIMECHA.png")

st.title("⚙️ AIMecha Study OS — Mechatronics AI Tracker")

# =========================================================
# DATABASE CONNECTION
# =========================================================
@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

conn = get_conn()

# =========================================================
# INITIALIZE DATABASE
# =========================================================
def init_db():

    c = conn.cursor()

    # COURSES
    c.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        course_name TEXT,
        completed INTEGER DEFAULT 0
    )
    """)

    # NOTES
    c.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        note TEXT,
        created_at TEXT
    )
    """)

    # JOURNAL
    c.execute("""
    CREATE TABLE IF NOT EXISTS journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        entry TEXT,
        created_at TEXT
    )
    """)

    # EXERCISES
    c.execute("""
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        course_name TEXT,
        file_name TEXT,
        file_path TEXT,
        created_at TEXT
    )
    """)

    conn.commit()

init_db()

# =========================================================
# COURSES FUNCTIONS
# =========================================================
def get_courses():
    return pd.read_sql_query(
        "SELECT * FROM courses",
        conn
    )

def add_course(category, name):

    conn.execute(
        "INSERT INTO courses (category, course_name) VALUES (?, ?)",
        (category, name)
    )

    conn.commit()

def update_course(course_id, completed):

    conn.execute(
        "UPDATE courses SET completed=? WHERE id=?",
        (completed, course_id)
    )

    conn.commit()

# =========================================================
# NOTES FUNCTIONS
# =========================================================
def add_note(course_id, note):

    conn.execute(
        """
        INSERT INTO notes (course_id, note, created_at)
        VALUES (?, ?, ?)
        """,
        (course_id, note, datetime.now().isoformat())
    )

    conn.commit()

def get_notes(course_id):

    return pd.read_sql_query(
        """
        SELECT * FROM notes
        WHERE course_id=?
        ORDER BY created_at DESC
        """,
        conn,
        params=(course_id,)
    )

def delete_note(note_id):

    conn.execute(
        "DELETE FROM notes WHERE id=?",
        (note_id,)
    )

    conn.commit()

# =========================================================
# JOURNAL FUNCTIONS
# =========================================================
def add_journal(title, entry):

    conn.execute(
        """
        INSERT INTO journal (title, entry, created_at)
        VALUES (?, ?, ?)
        """,
        (title, entry, datetime.now().isoformat())
    )

    conn.commit()

def get_journal():

    return pd.read_sql_query(
        "SELECT * FROM journal ORDER BY created_at DESC",
        conn
    )

def delete_journal(journal_id):

    conn.execute(
        "DELETE FROM journal WHERE id=?",
        (journal_id,)
    )

    conn.commit()

# =========================================================
# EXERCISE FUNCTIONS
# =========================================================
def save_exercise(course_id, course_name, uploaded_file):

    file_path = os.path.join(
        UPLOAD_FOLDER,
        uploaded_file.name
    )

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    conn.execute(
        """
        INSERT INTO exercises
        (course_id, course_name, file_name, file_path, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            course_id,
            course_name,
            uploaded_file.name,
            file_path,
            datetime.now().isoformat()
        )
    )

    conn.commit()

def get_exercises():

    return pd.read_sql_query(
        "SELECT * FROM exercises ORDER BY created_at DESC",
        conn
    )

def delete_exercise(ex_id, file_path):

    conn.execute(
        "DELETE FROM exercises WHERE id=?",
        (ex_id,)
    )

    if os.path.exists(file_path):
        os.remove(file_path)

    conn.commit()

# =========================================================
# PDF EXPORT
# =========================================================
def generate_pdf():

    filename = "AIMecha_Portfolio.pdf"

    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    content = []

    # TITLE
    content.append(
        Paragraph(
            "AIMecha Engineering Portfolio",
            styles["Title"]
        )
    )

    content.append(Spacer(1, 12))

    # COURSES
    courses = get_courses()

    content.append(
        Paragraph(
            "Courses",
            styles["Heading2"]
        )
    )

    for _, row in courses.iterrows():

        text = f"""
        {row['course_name']}
        ({row['category']})
        - Completed: {row['completed']}
        """

        content.append(
            Paragraph(text, styles["Normal"])
        )

    content.append(Spacer(1, 12))

    # NOTES
    notes = pd.read_sql_query(
        "SELECT * FROM notes",
        conn
    )

    content.append(
        Paragraph(
            "Engineering Notes",
            styles["Heading2"]
        )
    )

    for _, row in notes.iterrows():

        content.append(
            Paragraph(
                row["note"][:300],
                styles["Normal"]
            )
        )

    doc.build(content)

    return filename

# =========================================================
# NAVIGATION
# =========================================================
menu = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Courses",
        "Add Course",
        "Journal",
        "Exercises",
        "Competency Matrix",
        "Analytics",
        "Export PDF"
    ]
)

# =========================================================
# DASHBOARD
# =========================================================
if menu == "Dashboard":

    st.subheader("🚀 AIMecha Engineering Dashboard")

    courses_df = get_courses()
    exercises_df = get_exercises()
    journal_df = get_journal()

    total_courses = len(courses_df)

    completed_courses = 0

    if not courses_df.empty:
        completed_courses = int(
            courses_df["completed"].sum()
        )

    total_exercises = len(exercises_df)
    total_journal = len(journal_df)

    progress = 0

    if total_courses > 0:
        progress = (
            completed_courses / total_courses
        ) * 100

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("📚 Courses", total_courses)
    col2.metric("✅ Completed", completed_courses)
    col3.metric("📤 Exercises", total_exercises)
    col4.metric("📝 Journal Entries", total_journal)

    st.progress(progress / 100)

    st.write(f"Overall Progress: {progress:.1f}%")

# =========================================================
# COURSES
# =========================================================
elif menu == "Courses":

    st.subheader("📚 Courses + Notes")

    df = get_courses()

    if df.empty:
        st.warning("No courses added yet.")

    else:

        for _, row in df.iterrows():

            st.markdown("---")

            st.write(
                f"## {row['course_name']} ({row['category']})"
            )

            completed = st.checkbox(
                "Completed",
                value=bool(row["completed"]),
                key=f"c_{row['id']}"
            )

            update_course(
                row["id"],
                int(completed)
            )

            note = st.text_area(
                "Write Notes",
                key=f"n_{row['id']}",
                height=150
            )

            if st.button(
                "Save Note",
                key=f"s_{row['id']}"
            ):

                if note.strip():

                    add_note(
                        row["id"],
                        note
                    )

                    st.success("Note saved.")
                    st.rerun()

            notes = get_notes(row["id"])

            st.write("### 📒 Notes History")

            for _, n in notes.iterrows():

                col1, col2 = st.columns([6,1])

                with col1:

                    st.markdown(
                        f"""
                        <div style="
                            padding:10px;
                            border-radius:10px;
                            background:#111;
                            border:1px solid #333;
                            margin-bottom:10px;
                        ">
                        {n['note'].replace(chr(10), '<br>')}
                        <br><br>
                        <small>{n['created_at']}</small>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with col2:

                    if st.button(
                        "🗑",
                        key=f"dn_{n['id']}"
                    ):

                        delete_note(n["id"])
                        st.rerun()

# =========================================================
# ADD COURSE
# =========================================================
elif menu == "Add Course":

    st.subheader("➕ Add Course")

    category = st.selectbox(
        "Category",
        [
            "AI",
            "Robotics",
            "Programming",
            "Control Systems",
            "Mathematics",
            "Electronics",
            "Embedded Systems",
            "Machine Learning",
            "Computer Vision"
        ]
    )

    course_name = st.text_input("Course Name")

    if st.button("Add Course"):

        if course_name.strip():

            add_course(
                category,
                course_name
            )

            st.success("Course Added.")
            st.rerun()

# =========================================================
# JOURNAL
# =========================================================
elif menu == "Journal":

    st.subheader("🧠 Engineering Journal")

    title = st.text_input("Journal Title")

    entry = st.text_area(
        "Write Reflection / Learning Notes",
        height=200
    )

    if st.button("Save Journal"):

        if entry.strip():

            add_journal(
                title if title else "Untitled",
                entry
            )

            st.success("Journal Saved.")
            st.rerun()

    st.divider()

    journals = get_journal()

    for _, j in journals.iterrows():

        col1, col2 = st.columns([6,1])

        with col1:

            st.markdown(
                f"""
                <div style="
                    padding:10px;
                    border-radius:10px;
                    background:#111;
                    border:1px solid #333;
                    margin-bottom:10px;
                ">
                <h4>{j['title']}</h4>
                {j['entry'].replace(chr(10), '<br>')}
                <br><br>
                <small>{j['created_at']}</small>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:

            if st.button(
                "🗑",
                key=f"j_{j['id']}"
            ):

                delete_journal(j["id"])
                st.rerun()

# =========================================================
# EXERCISES
# =========================================================
elif menu == "Exercises":

    st.subheader("📤 Exercise Uploads")

    courses = get_courses()

    if not courses.empty:

        course = st.selectbox(
            "Select Course",
            courses["course_name"]
        )

        course_id = courses[
            courses["course_name"] == course
        ]["id"].values[0]

        uploaded_file = st.file_uploader(
            "Upload Exercise / Assignment",
            type=[
                "pdf",
                "png",
                "jpg",
                "jpeg",
                "py",
                "ipynb",
                "docx"
            ]
        )

        if uploaded_file:

            if st.button("Save Exercise"):

                save_exercise(
                    course_id,
                    course,
                    uploaded_file
                )

                st.success("Exercise Uploaded.")
                st.rerun()

    st.divider()

    exercises = get_exercises()

    for _, ex in exercises.iterrows():

        col1, col2 = st.columns([6,1])

        with col1:

            st.write(
                f"📘 {ex['course_name']} - {ex['file_name']}"
            )

            with open(ex["file_path"], "rb") as f:

                st.download_button(
                    "Download",
                    f,
                    file_name=ex["file_name"],
                    key=f"d_{ex['id']}"
                )

        with col2:

            if st.button(
                "🗑",
                key=f"e_{ex['id']}"
            ):

                delete_exercise(
                    ex["id"],
                    ex["file_path"]
                )

                st.rerun()

# =========================================================
# COMPETENCY MATRIX
# =========================================================
elif menu == "Competency Matrix":

    st.subheader("🧠 AIMecha Competency Matrix")

    competencies = {
        "Domain": [
            "Python Programming",
            "Machine Learning",
            "Computer Vision",
            "Robotics",
            "Control Systems",
            "Mathematics",
            "Embedded Systems",
            "Electronics",
            "Automation",
            "Data Science"
        ],
        "Level": [
            80,
            65,
            60,
            55,
            70,
            75,
            50,
            55,
            70,
            60
        ],
        "Status": [
            "Strong",
            "Developing",
            "Developing",
            "Intermediate",
            "Strong",
            "Strong",
            "Intermediate",
            "Intermediate",
            "Strong",
            "Developing"
        ]
    }

    skills_df = pd.DataFrame(competencies)

    selected = st.multiselect(
        "Select Competencies",
        skills_df["Domain"],
        default=skills_df["Domain"].tolist()
    )

    filtered_df = skills_df[
        skills_df["Domain"].isin(selected)
    ]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Skills",
        len(filtered_df)
    )

    col2.metric(
        "Average Skill",
        f"{filtered_df['Level'].mean():.1f}%"
    )

    strong = len(
        filtered_df[
            filtered_df["Level"] >= 70
        ]
    )

    col3.metric(
        "Strong Areas",
        strong
    )

    st.divider()

    # RADAR CHART
    radar = go.Figure()

    radar.add_trace(
        go.Scatterpolar(
            r=filtered_df["Level"],
            theta=filtered_df["Domain"],
            fill='toself'
        )
    )

    radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0,100]
            )
        ),
        showlegend=False,
        height=600
    )

    st.plotly_chart(
        radar,
        use_container_width=True
    )

    st.divider()

    # BAR CHART
    bar = px.bar(
        filtered_df,
        x="Domain",
        y="Level",
        color="Status",
        text="Level"
    )

    st.plotly_chart(
        bar,
        use_container_width=True
    )

    st.divider()

    st.dataframe(
        filtered_df,
        use_container_width=True
    )

# =========================================================
# ANALYTICS
# =========================================================
elif menu == "Analytics":

    st.subheader("📊 Learning Analytics")

    df = get_courses()

    if not df.empty:

        analytics = (
            df.groupby("category")["completed"]
            .mean()
            * 100
        )

        st.bar_chart(analytics)

        st.dataframe(df)

# =========================================================
# EXPORT PDF
# =========================================================
elif menu == "Export PDF":

    st.subheader("📄 Portfolio Export")

    if st.button("Generate PDF"):

        file = generate_pdf()

        with open(file, "rb") as f:

            st.download_button(
                "Download PDF",
                f,
                file_name=file
            )
