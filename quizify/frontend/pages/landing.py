"""Landing page -- hero with signature orb, agent-attributed feature grid, dual audience cards."""
from frontend.components.ui import feature_card, signature_orb


def render(st):
    hero_left, hero_right = st.columns([3, 2], gap="large")

    with hero_left:
        st.markdown(
            """
            <div style="padding: 2.5rem 0 0.5rem 0;">
                <div class="hero-eyebrow">FOUR AGENTS \u00b7 ONE LEARNING LOOP</div>
                <div class="hero-title">
                    Learning that<br><span class="gradient-text">adapts to you</span>
                </div>
                <div class="hero-subtitle">
                    Quizify reads your course material, writes the quiz, grades it,
                    finds what you don\'t know yet, and changes what comes next &mdash;
                    four AI agents handing off to each other in one continuous loop.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Get started", use_container_width=True):
                st.session_state["page"] = "login"
                st.rerun()
        with col2:
            if st.button("Sign in", use_container_width=True):
                st.session_state["page"] = "login"
                st.rerun()

    with hero_right:
        st.markdown('<div style="padding-top: 2rem; display:flex; justify-content:center;">', unsafe_allow_html=True)
        signature_orb(st, size=260)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-eyebrow" style="color:var(--text-muted);">THE LOOP</div>'
        '<h3 class="gradient-text" style="margin-top:0;">Four agents, one handoff chain</h3>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="agent-tag"><span class="dot"></span>AGENT 01 \u00b7 CONTENT</div>', unsafe_allow_html=True)
        feature_card(
            st, "\U0001F4DA", "Reads, then writes",
            "Pulls topics and learning objectives out of your PDFs and notes, "
            "then writes MCQ, true/false, and short-answer questions grounded in that material."
        )
    with c2:
        st.markdown('<div class="agent-tag tag-eval"><span class="dot"></span>AGENT 02 \u00b7 EVALUATION</div>', unsafe_allow_html=True)
        feature_card(
            st, "\u2705", "Grades like a person",
            "Marks objective questions instantly and reads short answers for meaning, "
            "not exact wording, with partial credit and a hint when you miss one."
        )
    with c3:
        st.markdown('<div class="agent-tag tag-adapt"><span class="dot"></span>AGENT 03 \u00b7 ADAPTIVE</div>', unsafe_allow_html=True)
        feature_card(
            st, "\U0001F3AF", "Finds the gap",
            "Tracks mastery per concept, not just per quiz, and decides whether "
            "you\'re ready to move on or need another pass at what\'s shaky."
        )
    with c4:
        st.markdown('<div class="agent-tag tag-analytics"><span class="dot"></span>AGENT 04 \u00b7 ANALYTICS</div>', unsafe_allow_html=True)
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
            <div class="glass-card">
                <div class="agent-tag" style="margin-bottom:1rem;"><span class="dot"></span>FOR TEACHERS</div>
                <h4 style="margin-top:0;">Upload once, adapt forever</h4>
                <p style="color:var(--text-secondary); line-height:1.6;">
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
            <div class="glass-card">
                <div class="agent-tag tag-adapt" style="margin-bottom:1rem;"><span class="dot"></span>FOR STUDENTS</div>
                <h4 style="margin-top:0;">A quiz that meets you where you are</h4>
                <p style="color:var(--text-secondary); line-height:1.6;">
                    Get harder when you\'re ready, ease off when you\'re not. Every
                    attempt comes back with real feedback, a hint if you need one,
                    and a clear picture of what to study next.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    _, center, _ = st.columns([1, 1, 1])
    with center:
        if st.button("Start learning now", use_container_width=True):
            st.session_state["page"] = "login"
            st.rerun()
