"""
Feedback Dashboard -- runs the evaluation cycle (Agent 2 -> Agent 3 -> Agent 4
via LangGraph orchestration) on quiz submission, then displays scores,
mistakes, explanations, and AI suggestions.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from database.db import get_db_session
from database.models import Analytics
from database.quiz_repo import save_responses, mark_assignment_completed
from backend.orchestration import run_evaluation_cycle
from frontend.components.ui import pill, difficulty_pill, metric_card, empty_state
from frontend.components.styles import agent_tag


def render(st):
    st.markdown(agent_tag("AGENT 02 \u00b7 EVALUATION", variant="eval"), unsafe_allow_html=True)
    st.markdown('<h2 class="gradient-text" style="margin-top:0;">Feedback</h2>', unsafe_allow_html=True)

    active_quiz = st.session_state.get("active_quiz")
    if not active_quiz:
        empty_state(
            st, "\U0001F4CB", "No results yet",
            "Take a quiz first -- your score, mistakes, and AI feedback will show up here.",
        )
        return

    if st.session_state.get("pending_evaluation"):
        with st.spinner("Grading your answers, finding gaps, and updating your analytics..."):
            try:
                answers = st.session_state.get("quiz_answers", {})
                student_responses = [{"question_index": i, "response": r} for i, r in answers.items()]
                quiz_id = active_quiz.get("quiz_id")
                student_id = st.session_state["user_id"]

                with get_db_session() as db:
                    analytics = db.query(Analytics).filter_by(student_id=student_id).first()
                    existing_mastery = analytics.topic_mastery if analytics else {}

                state = {
                    "student_id": student_id,
                    "topic": active_quiz["topic"],
                    "difficulty": active_quiz["difficulty"],
                    # Real quiz_id when this quiz was persisted via
                    # quiz_repo.save_generated_quiz/load_quiz_as_dict (the
                    # normal path now). Falls back to 0 only for any quiz
                    # still living purely in session state (legacy/edge
                    # case), so analytics history is never silently lost.
                    "quiz_id": quiz_id or 0,
                    "existing_topic_mastery": existing_mastery or {},
                    "generated_quiz": active_quiz,
                    "student_responses": student_responses,
                }

                result = run_evaluation_cycle(state)
                if result.get("error"):
                    st.error(result["error"])
                else:
                    st.session_state["last_evaluation"] = result["evaluation_result"]
                    st.session_state["last_adaptive"] = result["adaptive_result"]
                    st.session_state["last_analytics"] = result["analytics_result"]

                    if quiz_id:
                        # Persist per-question grading detail as real
                        # Response rows, and mark this student's assignment
                        # (if any -- self-practice quizzes have none) as
                        # completed so it drops off their pending list.
                        save_responses(student_id, quiz_id, result["evaluation_result"]["graded_questions"])
                        mark_assignment_completed(quiz_id, student_id)
                st.session_state["pending_evaluation"] = False
            except Exception as e:
                st.error(f"Evaluation failed: {e}")
                st.session_state["pending_evaluation"] = False

    evaluation = st.session_state.get("last_evaluation")
    adaptive = st.session_state.get("last_adaptive")
    analytics_result = st.session_state.get("last_analytics")

    if not evaluation:
        st.info("Submit a quiz to see your results here.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(st, "Accuracy", evaluation["accuracy"], "%")
    with c2:
        metric_card(st, "Score", f"{evaluation['total_score']}/{evaluation['max_score']}")
    with c3:
        metric_card(st, "Mistakes", len(evaluation["mistakes"]))
    with c4:
        if analytics_result:
            metric_card(st, "Streak", analytics_result["current_streak"], " days")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="glass-card"><h4 style="margin-top:0;">Feedback</h4>'
        f'<p style="color:var(--text-secondary); line-height:1.6;">{evaluation["ai_feedback_report"]}</p></div>',
        unsafe_allow_html=True,
    )

    if analytics_result and analytics_result.get("new_badges"):
        for badge in analytics_result["new_badges"]:
            st.success(f"New badge earned: {badge['icon']} {badge['name']} -- {badge['description']}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<h3 class="gradient-text">Question by question</h3>', unsafe_allow_html=True)

    questions = active_quiz["questions"]
    for g in evaluation["graded_questions"]:
        q = questions[g["question_index"]]
        status_pill = pill("Correct", "success") if g["is_correct"] else pill("Incorrect", "danger")
        score_pct = int(g["score"] * 100)

        hint_html = ""
        if g.get("hint"):
            hint_html = f'<p style="color:var(--amber); margin-top:0.6rem;"><b>Hint</b> {g["hint"]}</p>'

        st.markdown(
            f"""
            <div class="question-card">
                <span class="question-number">{g['question_index']+1}</span>
                <b>{q['question']}</b> &nbsp; {status_pill} &nbsp; {pill(f"{score_pct}%")}
                <p style="color:var(--text-secondary); margin-top:0.6rem;">
                    <b style="color:var(--text-primary);">Your answer</b> {g.get('student_answer','') or '<i>no answer</i>'}<br>
                    <b style="color:var(--text-primary);">Correct answer</b> {g.get('correct_answer','')}
                </p>
                <p style="color:var(--text-secondary);"><b style="color:var(--text-primary);">Feedback</b> {g.get('feedback','')}</p>
                {hint_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if adaptive:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(agent_tag("AGENT 03 \u00b7 ADAPTIVE", variant="adapt"), unsafe_allow_html=True)
        decision_label = "Advancing to harder material" if adaptive["decision"] == "advance" else "Reinforcing weak concepts"
        st.markdown(
            f"""
            <div class="glass-card">
                <h4 style="margin-top:0;">{decision_label}</h4>
                <p style="color:var(--text-secondary); line-height:1.6;">{adaptive['learning_path_note']}</p>
                <p style="color:var(--text-secondary);">Next difficulty: {difficulty_pill(adaptive['next_difficulty'])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("View full learning gap dashboard"):
            st.session_state["page"] = "learning_gap_dashboard"
            st.rerun()
