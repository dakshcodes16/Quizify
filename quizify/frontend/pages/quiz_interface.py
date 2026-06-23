"""Quiz Interface -- student-facing quiz taking experience with timer and progress.

A student lands here in one of three states:
  1. They have assigned quizzes waiting (teacher assigned them, via
     database/quiz_repo.py) -- shown as a picker, most recent first.
  2. They have no assignments but courses exist -- a self-practice
     generator lets them build their own quiz (e.g. for review), which
     also gets persisted so it behaves identically to an assigned one.
  3. They're mid-quiz (answers in progress, tracked in session state for
     the scratchpad only -- the quiz itself always comes from the DB).
"""
import sys
from pathlib import Path
import time

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from database.db import get_db_session
from database.models import Course, Analytics
from database.quiz_repo import (
    get_assigned_quizzes_for_student, load_quiz_as_dict, save_generated_quiz,
)
from agents.content_quiz_agent import ContentQuizAgent
from frontend.components.ui import difficulty_pill, pill, empty_state, card_container
from frontend.components.styles import agent_tag


def render(st):
    st.markdown(agent_tag("AGENT 01 \u00b7 CONTENT & QUIZ"), unsafe_allow_html=True)
    st.markdown('<h2 class="gradient-text" style="margin-top:0;">Quiz time</h2>', unsafe_allow_html=True)

    active_quiz = st.session_state.get("active_quiz")

    if not active_quiz:
        if st.session_state.get("quiz_submitted"):
            # just finished one -- reset before showing the picker again
            st.session_state["quiz_submitted"] = False
            st.session_state["quiz_answers"] = {}
            st.session_state["quiz_start_time"] = None
        _render_quiz_picker(st)
        return

    questions = active_quiz["questions"]

    if st.session_state.get("quiz_submitted"):
        st.info("This quiz has been submitted. View results on the Feedback page, or pick another quiz below.")
        if st.button("Back to my quizzes"):
            st.session_state["active_quiz"] = None
            st.session_state["quiz_answers"] = {}
            st.session_state["quiz_submitted"] = False
            st.rerun()
        return

    if st.session_state.get("quiz_start_time") is None:
        st.session_state["quiz_start_time"] = time.time()

    elapsed = int(time.time() - st.session_state["quiz_start_time"])
    answered = len(st.session_state.get("quiz_answers", {}))
    progress = answered / len(questions) if questions else 0

    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.progress(progress, text=f"{answered} of {len(questions)} answered")
    with col_b:
        mins, secs = divmod(elapsed, 60)
        st.markdown(f'<div class="pill">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<p style="color:var(--text-secondary);">Topic: <b style="color:var(--text-primary);">{active_quiz["topic"]}</b> &nbsp; '
        f'{difficulty_pill(active_quiz["difficulty"])} &nbsp; {pill(active_quiz["bloom_level"].title())}</p>',
        unsafe_allow_html=True,
    )

    answers = st.session_state.get("quiz_answers", {})

    for i, q in enumerate(questions):
        st.markdown(
            f'<div class="question-card"><span class="question-number">{i+1}</span><b>{q["question"]}</b></div>',
            unsafe_allow_html=True,
        )

        if q["type"] == "mcq":
            options = q.get("options", [])
            response = st.radio(
                "Select an answer", options, key=f"q_{active_quiz.get('quiz_id','x')}_{i}",
                index=None, label_visibility="collapsed",
            )
        elif q["type"] == "true_false":
            response = st.radio(
                "True or False", ["True", "False"], key=f"q_{active_quiz.get('quiz_id','x')}_{i}",
                index=None, label_visibility="collapsed",
            )
        else:
            response = st.text_area(
                "Your answer", key=f"q_{active_quiz.get('quiz_id','x')}_{i}",
                label_visibility="collapsed", height=80,
            )

        if response:
            answers[i] = response
        st.session_state["quiz_answers"] = answers
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    submit_disabled = len(answers) < len(questions)
    if submit_disabled:
        st.caption(f"Answer all {len(questions)} questions to submit ({len(answers)} done).")

    if st.button("Submit quiz", disabled=submit_disabled, use_container_width=True):
        st.session_state["quiz_submitted"] = True
        st.session_state["pending_evaluation"] = True
        st.session_state["page"] = "feedback_dashboard"
        st.rerun()


def _render_quiz_picker(st):
    """Shows quizzes a teacher has assigned to this student (real DB-backed
    assignments), plus a self-practice generator as a fallback/extra option."""
    student_id = st.session_state["user_id"]
    assigned = get_assigned_quizzes_for_student(student_id, only_pending=True)

    if assigned:
        st.markdown('<h3 class="gradient-text">Assigned to you</h3>', unsafe_allow_html=True)
        for a in assigned:
            due_text = f" &middot; due {a['due_date'].strftime('%b %d, %Y')}" if a.get("due_date") else ""
            question_count_label = f"{a['num_questions']} questions"
            with card_container(st):
                st.markdown(
                    f'<b style="font-size:1.05rem;">{a["topic"]}</b> &nbsp; '
                    f'{difficulty_pill(a["difficulty"])} &nbsp; {pill(question_count_label)}'
                    f'<p style="color:var(--text-muted); margin:0.3rem 0 0.8rem;">'
                    f'Assigned {a["assigned_at"].strftime("%b %d, %Y")}{due_text}</p>',
                    unsafe_allow_html=True,
                )
                if st.button("Start quiz", key=f"start_{a['assignment_id']}"):
                    quiz = load_quiz_as_dict(a["quiz_id"])
                    if not quiz:
                        st.error("This quiz could not be loaded -- it may have been removed.")
                    else:
                        st.session_state["active_quiz"] = quiz
                        st.session_state["active_course_id"] = quiz["course_id"]
                        st.session_state["quiz_answers"] = {}
                        st.session_state["quiz_start_time"] = None
                        st.session_state["quiz_submitted"] = False
                        st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<h3 class="gradient-text">Or practice on your own</h3>', unsafe_allow_html=True)
    else:
        empty_state(
            st, "\U0001F4DD", "No quizzes assigned yet",
            "Your teacher hasn't assigned you a quiz yet. You can generate your "
            "own practice quiz below in the meantime.",
        )

    _render_quiz_generator(st)


def _render_quiz_generator(st):
    """Self-practice generator for students -- builds and persists a quiz the
    same way an assigned one is stored, just without a teacher-created
    Assignment row, so it behaves identically once started."""
    with get_db_session() as db:
        courses = db.query(Course).all()

    if not courses:
        st.warning("No courses available yet. Ask your teacher to upload material first.")
        return

    with card_container(st):
        course_map = {c.title: c.id for c in courses}
        course_title = st.selectbox("Course", list(course_map.keys()))
        course_id = course_map[course_title]

        with get_db_session() as db:
            course = db.query(Course).filter_by(id=course_id).first()
            topics = [t["topic"] for t in (course.extracted_concepts or [])]

        if not topics:
            st.warning("This course has no extracted topics yet.")
            return

        topic = st.selectbox("Topic", topics)
        difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)
        num_q = st.slider("Number of questions", 3, 10, 5)
        generate_clicked = st.button("Generate my quiz")

    if generate_clicked:
        with st.spinner("Writing your adaptive quiz..."):
            try:
                weak_concepts = None
                with get_db_session() as db:
                    analytics = db.query(Analytics).filter_by(student_id=st.session_state["user_id"]).first()
                    if analytics and analytics.weak_topics:
                        weak_concepts = analytics.weak_topics

                agent = ContentQuizAgent()
                quiz = agent.generate_quiz(
                    course_id=course_id,
                    topic=topic,
                    difficulty=difficulty,
                    num_questions=num_q,
                    weak_concepts=weak_concepts,
                )
                quiz_id = save_generated_quiz(course_id, quiz)
                quiz["quiz_id"] = quiz_id
                st.session_state["active_quiz"] = quiz
                st.session_state["active_course_id"] = course_id
                st.session_state["quiz_answers"] = {}
                st.session_state["quiz_start_time"] = None
                st.session_state["quiz_submitted"] = False
                st.rerun()
            except Exception as e:
                st.error(f"Quiz generation failed: {e}")
