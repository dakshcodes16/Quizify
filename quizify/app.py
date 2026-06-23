"""
Quizify — main Streamlit entrypoint.

Run with: streamlit run app.py

Routes between pages using st.session_state["page"]. Auth (login/register)
goes over HTTP to the FastAPI service (run separately with
`uvicorn api.main:app --reload`); the core adaptive-learning loop calls
the agents/orchestration layer in-process for speed and simplicity.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

import streamlit as st

from config import settings
from database.db import init_db
from frontend.components.styles import inject_css
from frontend.components.session import init_session_state, is_authenticated, logout
from frontend.pages import (
    landing, login, teacher_upload, quiz_interface,
    feedback_dashboard, learning_gap_dashboard, faculty_dashboard,
)

st.set_page_config(
    page_title="Quizify — Adaptive Learning",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="auto",
)

inject_css(st)
init_session_state(st)
init_db()


def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div style="display:flex; align-items:center; gap:0.6rem; padding: 0.5rem 0 1.4rem 0;">'
            '<div style="width:34px; height:34px; border-radius:9px; '
            'background:linear-gradient(135deg, var(--violet), var(--blue)); '
            'display:flex; align-items:center; justify-content:center; font-size:1.05rem;">Q</div>'
            '<span class="gradient-text" style="font-size:1.25rem; font-weight:700; font-family:var(--font-display);">Quizify</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        if not is_authenticated(st):
            st.caption("Sign in to access your dashboard.")
            if not settings.groq_api_key:
                st.warning("GROQ_API_KEY not set in .env — quiz generation will fail until configured.")
            return

        st.markdown(
            f'<div style="background:var(--surface); border:1px solid var(--border); '
            f'border-radius:12px; padding:0.7rem 0.9rem; margin-bottom:1.2rem;">'
            f'<div style="font-weight:600;">{st.session_state["user_name"]}</div>'
            f'<div style="font-size:0.78rem; color:var(--text-muted); text-transform:uppercase; '
            f'letter-spacing:0.05em; font-family:var(--font-mono);">{st.session_state["user_role"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        role = st.session_state["user_role"]
        current_page = st.session_state.get("page")

        if role == "teacher":
            nav_items = [
                ("Upload material", "teacher_upload"),
                ("Faculty dashboard", "faculty_dashboard"),
            ]
        else:
            nav_items = [
                ("Take a quiz", "quiz_interface"),
                ("Feedback", "feedback_dashboard"),
                ("Learning gaps", "learning_gap_dashboard"),
            ]

        for label, page_key in nav_items:
            is_active = current_page == page_key
            if st.button(
                label, use_container_width=True, key=f"nav_{page_key}",
                type="primary" if is_active else "secondary",
            ):
                st.session_state["page"] = page_key
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if not settings.groq_api_key:
            st.warning("GROQ_API_KEY not set — AI features will fail until configured in .env")

        if st.button("Log out", use_container_width=True):
            logout(st)
            st.rerun()


def render_page():
    page = st.session_state["page"]

    # Auth gate: everything except landing/login requires a token
    if page not in ("landing", "login") and not is_authenticated(st):
        st.session_state["page"] = "login"
        page = "login"

    pages = {
        "landing": landing.render,
        "login": login.render,
        "teacher_upload": teacher_upload.render,
        "quiz_interface": quiz_interface.render,
        "feedback_dashboard": feedback_dashboard.render,
        "learning_gap_dashboard": learning_gap_dashboard.render,
        "faculty_dashboard": faculty_dashboard.render,
    }

    # Role gating: students can't see the faculty dashboard, teachers don't take quizzes
    if is_authenticated(st):
        role = st.session_state["user_role"]
        student_only = {"quiz_interface", "feedback_dashboard", "learning_gap_dashboard"}
        teacher_only = {"teacher_upload", "faculty_dashboard"}
        if role == "teacher" and page in student_only:
            page = "teacher_upload"
        if role == "student" and page in teacher_only:
            page = "quiz_interface"

    render_fn = pages.get(page, landing.render)
    render_fn(st)


render_sidebar()
render_page()
