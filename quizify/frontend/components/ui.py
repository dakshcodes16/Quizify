"""Reusable glassmorphism UI components for Streamlit pages."""


def metric_card(st, label: str, value, suffix: str = ""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value">{value}{suffix}</div>
            <div class="metric-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pill(text: str, variant: str = "default") -> str:
    cls = {"success": "pill-success", "warning": "pill-warning", "danger": "pill-danger"}.get(variant, "")
    return f'<span class="pill {cls}">{text}</span>'


def difficulty_pill(difficulty: str) -> str:
    variant = {"easy": "success", "medium": "warning", "hard": "danger"}.get(difficulty, "default")
    return pill(difficulty.title(), variant)


def feature_card(st, icon: str, title: str, desc: str):
    st.markdown(
        f"""
        <div class="feature-card">
            <div class="feature-icon">{icon}</div>
            <div class="feature-title">{title}</div>
            <div class="feature-desc">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_container(st):
    """
    Returns a real Streamlit container that visually renders as a glass
    card (see styles.py's stVerticalBlockBorderWrapper styling).

    Use as a context manager so widgets are *actually* nested inside the
    card -- unlike the old open/close `st.markdown('<div class="glass-card">')`
    pattern, which never worked because each st.markdown() call is its own
    isolated DOM node and doesn't wrap subsequently-rendered widgets.

    Usage:
        with card_container(st):
            name = st.text_input("Name")
            st.button("Submit")
    """
    return st.container(border=True)

def signature_orb(st, size: int = 220):
    """The recurring gradient-mesh orb -- calm/breathing motion, reused
    across hero and loading contexts as the product's one signature
    visual motif (see styles.py for the animation itself)."""
    st.markdown(
        f"""
        <div style="width:{size}px; height:{size}px; position:relative;">
            <div class="signature-orb"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(st, icon: str, title: str, body: str, cta_label: str = None):
    """An empty screen as an invitation to act, per design guidance --
    explains what's missing and what to do about it, not just 'no data'."""
    st.markdown(
        f"""
        <div class="glass-card" style="text-align:center; padding:3rem 2rem;">
            <div style="font-size:2.2rem; margin-bottom:0.75rem;">{icon}</div>
            <div style="font-family:var(--font-display); font-weight:600; font-size:1.15rem; margin-bottom:0.5rem;">{title}</div>
            <div style="color:var(--text-secondary); max-width:420px; margin:0 auto; line-height:1.55;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_row(st, items):
    """items: list of (label, value, suffix) tuples, rendered as a row of metric cards."""
    cols = st.columns(len(items))
    for col, (label, value, suffix) in zip(cols, items):
        with col:
            metric_card(st, label, value, suffix)
