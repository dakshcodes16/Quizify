"""Landing page -- hero with signature orb, agent-attributed feature grid, dual audience cards."""
from frontend.components.ui import feature_card, signature_orb, card_container


def render(st):
    # Top hero section wrapped in a nice container layout
    with card_container(st):
        hero_left, hero_right = st.columns([3, 2], gap="large")

        with hero_left:
            st.markdown(
                """
                <div style="padding: 1rem 0;">
                    <div class="hero-eyebrow">FOUR AGENTS \u00b7 ONE LEARNING LOOP</div>
                    <div class="hero-title" style="margin-top: 0.5rem;">
                        Learning that<br><span class="gradient-text">adapts to you</span>
                    </div>
                    <div class="hero-subtitle" style="margin-top: 1rem; margin-bottom: 2rem;">
                        Quizify reads your course material, writes the quiz, grades it,
                        finds what you don\'t know yet, and changes what comes next &mdash;
                        four AI agents handing off to each other in one continuous loop.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Faculty Portal", use_container_width=True, type="secondary"):
                st.session_state["page"] = "login"
                st.rerun()

        with hero_right:
            st.markdown('<div style="display:flex; justify-content:center; align-items:center; margin-bottom:1rem;">', unsafe_allow_html=True)
            signature_orb(st, size=150)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown(
                '<div style="text-align:center; margin-bottom:1rem;">'
                '<h4 style="margin:0; color:var(--violet); font-size:1.15rem;">🎯 Join Quiz</h4>'
                '<p style="color:var(--text-secondary); font-size:0.85rem; margin-top:0.25rem;">Enter code, name & roll no to start</p>'
                '</div>',
                unsafe_allow_html=True
            )
            with st.form("join_quiz_form", clear_on_submit=False):
                code = st.text_input("Quiz Code", placeholder="e.g. K9B8JD")
                name = st.text_input("Your Name", placeholder="e.g. Jane Doe")
                roll_no = st.text_input("Roll Number", placeholder="e.g. 101 or CS-21")
                submit = st.form_submit_button("Start Quiz", use_container_width=True)

                if submit:
                    if not code or not name or not roll_no:
                        st.error("Please enter Quiz Code, Name, and Roll Number.")
                    else:
                        from database.quiz_repo import access_quiz_by_code
                        quiz, student, err = access_quiz_by_code(code, name, roll_no)
                        if err:
                            st.error(err)
                        else:
                            st.session_state["auth_token"] = "guest_token"
                            st.session_state["user_id"] = student.id
                            st.session_state["user_name"] = student.name
                            st.session_state["user_role"] = "student"
                            st.session_state["active_quiz"] = quiz
                            st.session_state["active_course_id"] = quiz["course_id"]
                            st.session_state["page"] = "quiz_interface"
                            
                            # Clean/reset quiz session state so it starts fresh!
                            st.session_state["quiz_answers"] = {}
                            st.session_state["quiz_start_time"] = None
                            st.session_state["quiz_submitted"] = False
                            st.session_state["pending_evaluation"] = False
                            st.session_state["current_question_idx"] = 0
                            st.session_state["question_start_time"] = None
                            st.session_state["last_question_idx"] = 0
                            st.session_state.pop("last_evaluation", None)
                            st.session_state.pop("last_adaptive", None)
                            st.session_state.pop("last_analytics", None)
                            
                            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-eyebrow" style="color:var(--text-muted); font-size: 0.8rem;">THE LOOP</div>'
        '<h2 class="gradient-text" style="margin-top:0;">Four agents, one handoff chain</h2>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="agent-tag"><span class="dot"></span>AGENT 01 \u00b7 CONTENT</div>', unsafe_allow_html=True)
        with card_container(st):
            feature_card(
                st, "\U0001F4DA", "Reads, then writes",
                "Pulls topics and learning objectives out of your PDFs and notes, "
                "then writes MCQ, true/false, and short-answer questions grounded in that material."
            )
    with c2:
        st.markdown('<div class="agent-tag tag-eval"><span class="dot"></span>AGENT 02 \u00b7 EVALUATION</div>', unsafe_allow_html=True)
        with card_container(st):
            feature_card(
                st, "\u2705", "Grades like a person",
                "Marks objective questions instantly and reads short answers for meaning, "
                "not exact wording, with partial credit and a hint when you miss one."
            )
    with c3:
        st.markdown('<div class="agent-tag tag-adapt"><span class="dot"></span>AGENT 03 \u00b7 ADAPTIVE</div>', unsafe_allow_html=True)
        with card_container(st):
            feature_card(
                st, "\U0001F3AF", "Finds the gap",
                "Tracks mastery per concept, not just per quiz, and decides whether "
                "you\'re ready to move on or need another pass at what\'s shaky."
            )
    with c4:
        st.markdown('<div class="agent-tag tag-analytics"><span class="dot"></span>AGENT 04 \u00b7 ANALYTICS</div>', unsafe_allow_html=True)
        with card_container(st):
            feature_card(
                st, "\U0001F4CA", "Remembers everything",
                "Turns every attempt into a streak, a badge, or a line on a mastery "
                "curve &mdash; and rolls it all up into one view for faculty."
            )

    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown(
            """
            <div class="glass-card" style="height: 100%;">
                <div class="agent-tag" style="margin-bottom:1rem;"><span class="dot"></span>FOR TEACHERS</div>
                <h3 style="margin-top:0; font-size: 1.4rem;">Upload once, adapt forever</h3>
                <p style="color:var(--text-secondary); line-height:1.6; font-size: 0.95rem;">
                    Drop in a syllabus or lecture notes. Quizify extracts the concepts,
                    writes the first quiz, and keeps adjusting difficulty per student
                    from there &mdash; while you watch class-wide mastery in one dashboard.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="glass-card" style="height: 100%;">
                <div class="agent-tag tag-adapt" style="margin-bottom:1rem;"><span class="dot"></span>FOR STUDENTS</div>
                <h3 style="margin-top:0; font-size: 1.4rem;">A quiz that meets you where you are</h3>
                <p style="color:var(--text-secondary); line-height:1.6; font-size: 0.95rem;">
                    Get harder when you\'re ready, ease off when you\'re not. Every
                    attempt comes back with real feedback, a hint if you need one,
                    and a clear picture of what to study next.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br><br>", unsafe_allow_html=True)
    _, center, _ = st.columns([1, 1, 1])
    with center:
        if st.button("Go to Faculty Portal", use_container_width=True, type="secondary"):
            st.session_state["page"] = "login"
            st.rerun()
