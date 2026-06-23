"""Centralized Streamlit session_state helpers for auth and navigation."""


def init_session_state(st):
    defaults = {
        "page": "landing",
        "auth_token": None,
        "user_id": None,
        "user_name": None,
        "user_role": None,
        "active_course_id": None,
        "active_quiz": None,
        "quiz_start_time": None,
        "quiz_answers": {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def is_authenticated(st) -> bool:
    return st.session_state.get("auth_token") is not None


def logout(st):
    for key in ["auth_token", "user_id", "user_name", "user_role", "active_course_id", "active_quiz", "quiz_answers"]:
        st.session_state[key] = None if key not in ("quiz_answers",) else {}
    st.session_state["page"] = "landing"


def navigate(st, page: str):
    st.session_state["page"] = page
