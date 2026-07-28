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
            st.session_state["quiz_submitted"] = False
            st.session_state["quiz_answers"] = {}
            st.session_state["quiz_start_time"] = None
            st.session_state["current_question_idx"] = 0
            st.session_state["question_start_time"] = None
            st.session_state["last_question_idx"] = 0
        _render_quiz_picker(st)
        return

    questions = active_quiz["questions"]

    if st.session_state.get("quiz_submitted"):
        st.info("This quiz has been submitted. View results on the Feedback page, or pick another quiz below.")
        if st.button("Back to my quizzes"):
            st.session_state["active_quiz"] = None
            st.session_state["quiz_answers"] = {}
            st.session_state["quiz_submitted"] = False
            st.session_state["current_question_idx"] = 0
            st.session_state["question_start_time"] = None
            st.session_state["last_question_idx"] = 0
            st.rerun()
        return

    # Initialize session state variables if they are missing
    if "current_question_idx" not in st.session_state:
        st.session_state["current_question_idx"] = 0
    
    current_idx = st.session_state["current_question_idx"]

    # If somehow index is out of bounds, submit the quiz
    if current_idx >= len(questions):
        st.session_state["quiz_submitted"] = True
        st.session_state["pending_evaluation"] = True
        st.session_state["page"] = "feedback_dashboard"
        st.rerun()
        return

    # Keep track of when we transition to a new question
    if (
        "question_start_time" not in st.session_state
        or st.session_state.get("last_question_idx") != current_idx
        or st.session_state.get("question_start_time") is None
    ):
        st.session_state["question_start_time"] = time.time()
        st.session_state["last_question_idx"] = current_idx

    q = questions[current_idx]
    
    # Calculate initial time left
    time_limit = q.get("time_limit", 30) or 30
    elapsed = time.time() - st.session_state["question_start_time"]
    time_left = max(0, int(time_limit - elapsed))

    # Progress bar and page headers
    progress = current_idx / len(questions) if questions else 0

    # Placeholder for the visual progress bar and timer
    header_placeholder = st.empty()

    def update_header(time_val):
        is_critical = (time_val <= 10)
        color = "var(--coral)" if is_critical else "var(--violet)"
        extra_class = "timer-pulse-critical" if is_critical else ""
        percentage = int(((current_idx + 1) / len(questions)) * 100) if len(questions) > 0 else 0
        header_placeholder.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; width: 100%;">
                <span style="font-weight: 600; color: var(--text-primary);">Question {current_idx + 1} of {len(questions)}</span>
                <div class="pill {extra_class}" style="font-weight: 700; color: {color}; border-color: {color}; margin-left: auto;">
                    ⏳ {time_val}s left
                </div>
            </div>
            <div style="width: 100%; height: 8px; background: rgba(255, 255, 255, 0.12); border-radius: 4px; overflow: hidden; margin-bottom: 1.5rem;">
                <div style="width: {percentage}%; height: 100%; background: linear-gradient(90deg, var(--violet), var(--blue)); border-radius: 4px; transition: width 0.3s ease;"></div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Render initial header
    update_header(time_left)

    st.markdown(
        f'<p style="color:var(--text-secondary);">Topic: <b style="color:var(--text-primary);">{active_quiz["topic"]}</b> &nbsp; '
        f'{difficulty_pill(active_quiz["difficulty"])} &nbsp; {pill(active_quiz["bloom_level"].title())}</p>',
        unsafe_allow_html=True,
    )

    # Render current question card
    st.markdown(
        f'<div class="question-card"><span class="question-number">{current_idx+1}</span><b>{q["question"]}</b></div>',
        unsafe_allow_html=True,
    )

    answers = st.session_state.get("quiz_answers", {})
    current_ans = answers.get(current_idx)

    # Render inputs (labels are empty to avoid duplicate display in UI)
    response = None
    if q["type"] == "mcq":
        options = q.get("options", [])
        index = options.index(current_ans) if current_ans in options else None
        response = st.radio(
            " ", options, key=f"q_{active_quiz.get('quiz_id','x')}_{current_idx}",
            index=index, label_visibility="collapsed",
        )
    elif q["type"] == "true_false":
        options = ["True", "False"]
        index = options.index(current_ans) if current_ans in options else None
        response = st.radio(
            " ", options, key=f"q_{active_quiz.get('quiz_id','x')}_{current_idx}",
            index=index, label_visibility="collapsed",
        )
    else:
        response = st.text_area(
            " ", key=f"q_{active_quiz.get('quiz_id','x')}_{current_idx}",
            value=current_ans or "", label_visibility="collapsed", height=80,
        )

    # Save response to session state as soon as it is selected/entered
    if response:
        answers[current_idx] = response
        st.session_state["quiz_answers"] = answers

    st.markdown("<br>", unsafe_allow_html=True)

    is_last = (current_idx == len(questions) - 1)
    button_label = "Submit quiz" if is_last else "Next Question"

    # Action layout
    col_prev, col_next = st.columns([1, 1])
    with col_next:
        if st.button(button_label, use_container_width=True, type="primary"):
            if is_last:
                st.session_state["quiz_submitted"] = True
                st.session_state["pending_evaluation"] = True
                st.session_state["page"] = "feedback_dashboard"
                st.rerun()
            else:
                st.session_state["current_question_idx"] += 1
                st.session_state["question_start_time"] = None
                st.rerun()

    # Countdown loop in python
    if time_left > 0:
        last_displayed_time = -1
        while time_left > 0:
            if time_left != last_displayed_time:
                update_header(time_left)
                last_displayed_time = time_left
            time.sleep(0.1)
            elapsed = time.time() - st.session_state["question_start_time"]
            time_left = max(0, int(time_limit - elapsed))

    # Time has run out
    if time_left <= 0:
        if current_idx not in st.session_state["quiz_answers"]:
            st.session_state["quiz_answers"][current_idx] = ""
        st.toast("⏰ Time's up for this question!")
        time.sleep(1.0)
        if is_last:
            st.session_state["quiz_submitted"] = True
            st.session_state["pending_evaluation"] = True
            st.session_state["page"] = "feedback_dashboard"
            st.rerun()
        else:
            st.session_state["current_question_idx"] += 1
            st.session_state["question_start_time"] = None
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
                        st.session_state["current_question_idx"] = 0
                        st.session_state["question_start_time"] = None
                        st.session_state["last_question_idx"] = 0
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
                st.session_state["current_question_idx"] = 0
                st.session_state["question_start_time"] = None
                st.session_state["last_question_idx"] = 0
                st.rerun()
            except Exception as e:
                st.error(f"Quiz generation failed: {e}")
