"""Teacher Upload Page -- upload PDF/DOCX, extract concepts, preview topics, generate quizzes."""
import sys
from pathlib import Path
from datetime import datetime
import tempfile

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from database.db import get_db_session
from database.models import Course
from database.quiz_repo import save_generated_quiz, assign_quiz, get_students_for_teacher
from agents.content_quiz_agent import ContentQuizAgent
from frontend.components.ui import pill, difficulty_pill, empty_state, card_container
from frontend.components.styles import agent_tag


def render(st):
    st.markdown(agent_tag("AGENT 01 \u00b7 CONTENT & QUIZ"), unsafe_allow_html=True)
    st.markdown('<h2 class="gradient-text" style="margin-top:0;">Upload course material</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:var(--text-secondary); margin-bottom:1.5rem;">'
        'Extracts topics, concepts, and learning objectives, then grounds every quiz it writes in your material.</p>',
        unsafe_allow_html=True,
    )

    with card_container(st):
        course_title = st.text_input("Course or module title", placeholder="e.g. Introduction to Cell Biology")
        uploaded_file = st.file_uploader("Upload PDF, DOCX, or TXT notes", type=["pdf", "docx", "txt", "md"])
        process_clicked = st.button("Extract concepts", disabled=not (course_title and uploaded_file))

    if process_clicked and uploaded_file and course_title:
        with st.spinner("Reading your material and extracting concepts..."):
            try:
                suffix = Path(uploaded_file.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                with get_db_session() as db:
                    course = Course(
                        title=course_title,
                        uploaded_material=uploaded_file.name,
                        owner_id=st.session_state["user_id"],
                    )
                    db.add(course)
                    db.flush()
                    course_id = course.id

                agent = ContentQuizAgent()
                result = agent.ingest_material(tmp_path, course_id)

                with get_db_session() as db:
                    course = db.query(Course).filter_by(id=course_id).first()
                    course.extracted_concepts = result["concepts"]
                    db.add(course)

                st.session_state["active_course_id"] = course_id
                st.session_state["last_extraction"] = result
                num_concepts = len(result['concepts'])
                num_chunks = result['num_chunks']
                st.success(f"Extracted {num_concepts} topics from {num_chunks} content chunks.")
            except Exception as e:
                st.error(f"Extraction failed: {e}")

    extraction = st.session_state.get("last_extraction")
    if not extraction:
        st.markdown("<br>", unsafe_allow_html=True)
        empty_state(
            st, "\U0001F4C4", "No material extracted yet",
            "Upload a PDF or DOCX above and click Extract concepts to see topics, "
            "key concepts, and learning objectives appear here.",
        )
        return

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<h3 class="gradient-text">Extracted topics</h3>', unsafe_allow_html=True)

    for topic in extraction["concepts"]:
        concepts_html = "".join(
            f'<span class="concept-badge">{c}</span>'
            for c in topic.get('key_concepts', [])
        )
        objectives_html = "".join(
            f'<li style="color:var(--text-secondary); margin-bottom:0.35rem; font-size:0.9rem;">{o}</li>'
            for o in topic.get('learning_objectives', [])
        )
        st.markdown(
            f"""
            <div class="glass-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 1rem;">
                    <h4 style="margin:0; font-size:1.15rem; font-family:var(--font-display);">{topic.get('topic', 'Untitled topic')}</h4>
                    <div>{difficulty_pill(topic.get('suggested_difficulty','medium'))}</div>
                </div>
                <div style="margin-bottom: 1rem;">
                    <div style="font-weight:600; font-size:0.78rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.4rem;">Key Concepts</div>
                    <div style="display:flex; flex-wrap:wrap; gap:0.2rem;">
                        {concepts_html}
                    </div>
                </div>
                <div>
                    <div style="font-weight:600; font-size:0.78rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.4rem;">Learning Objectives</div>
                    <ul style="padding-left:1.2rem; margin:0;">
                        {objectives_html}
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<h3 class="gradient-text">Generate a quiz from this material</h3>', unsafe_allow_html=True)

    topics_list = [t["topic"] for t in extraction["concepts"]]
    with card_container(st):
        col1, col2, col3 = st.columns(3)
        with col1:
            quiz_topic = st.selectbox("Topic", topics_list)
        with col2:
            difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)
        with col3:
            num_q = st.slider("Number of questions", 3, 10, 5)

        bloom = st.selectbox(
            "Bloom's taxonomy level",
            ["remember", "understand", "apply", "analyze", "evaluate", "create"],
            index=1,
        )
        qtypes = st.multiselect(
            "Question types", ["mcq", "true_false", "short_answer"],
            default=["mcq", "true_false", "short_answer"],
        )
        generate_clicked = st.button("Generate quiz")

    if generate_clicked:
        with st.spinner("Writing questions grounded in your material..."):
            try:
                agent = ContentQuizAgent()
                quiz = agent.generate_quiz(
                    course_id=st.session_state["active_course_id"],
                    topic=quiz_topic,
                    difficulty=difficulty,
                    bloom_level=bloom,
                    num_questions=num_q,
                    question_types=qtypes or ["mcq"],
                )
                # Persist to real Quiz/Question rows immediately -- this is
                # what makes the quiz assignable. Previously the quiz only
                # ever lived in this teacher's own session state, which a
                # student's browser session could never see, so "assign"
                # had nothing real to point to.
                quiz_id = save_generated_quiz(st.session_state["active_course_id"], quiz)
                quiz["quiz_id"] = quiz_id
                st.session_state["active_quiz"] = quiz
                st.session_state["quiz_answers"] = {}
                num_questions_generated = len(quiz["questions"])
                st.success(f"Generated {num_questions_generated} questions on {quiz_topic} and saved it. Access code: {quiz['code']}")
            except Exception as e:
                st.error(f"Quiz generation failed: {e}")

    active_quiz = st.session_state.get("active_quiz")
    if active_quiz:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<h3 class="gradient-text">Quiz preview</h3>', unsafe_allow_html=True)
        for i, q in enumerate(active_quiz["questions"]):
            st.markdown(
                f"""
                <div class="question-card">
                    <span class="question-number">{i+1}</span>
                    <b>{q['question']}</b> {pill(q['type'].replace('_',' ').title())} {difficulty_pill(q.get('difficulty','medium'))}
                    <p style="color:var(--text-muted); margin-top:0.5rem; font-style:italic;">Concept: {q.get('concept_tag','')}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<h3 class="gradient-text">Share Quiz Code</h3>', unsafe_allow_html=True)

        if not active_quiz.get("code"):
            st.warning("No access code found for this quiz.")
        else:
            with card_container(st):
                st.markdown(
                    "<p style='color:var(--text-secondary); margin-bottom: 1rem;'>"
                    "Students do not need an account to take this quiz. "
                    "Share the code below with your students. They can access the quiz by "
                    "entering it and their name on the home page."
                    "</p>",
                    unsafe_allow_html=True
                )
                st.code(active_quiz["code"], language="text")
