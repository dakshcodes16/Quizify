"""Login / Register page -- calls the FastAPI auth API for real JWT auth."""
from frontend.components import auth_client
from frontend.components.ui import signature_orb


def render(st):
    _, center, _ = st.columns([1, 2, 1])

    with center:
        st.markdown('<div style="display:flex; justify-content:center; margin: 1rem 0;">', unsafe_allow_html=True)
        signature_orb(st, size=88)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            """
            <div style="text-align:center; margin-bottom: 1.75rem;">
                <h2 class="gradient-text" style="margin-bottom:0.3rem;">Welcome to Quizify</h2>
                <p style="color:var(--text-secondary);">Sign in or create an account to continue</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["Sign in", "Create account"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", key="login_email", placeholder="you@example.com")
                password = st.text_input("Password", type="password", key="login_password", placeholder="\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022")
                submitted = st.form_submit_button("Sign in", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Enter both your email and password to continue.")
                else:
                    data, err = auth_client.safe_call(auth_client.login, email, password)
                    if err:
                        st.error(err)
                    else:
                        st.session_state["auth_token"] = data["access_token"]
                        st.session_state["user_id"] = data["user_id"]
                        st.session_state["user_name"] = data["name"]
                        st.session_state["user_role"] = data["role"]
                        st.session_state["page"] = "teacher_upload" if data["role"] == "teacher" else "quiz_interface"
                        st.rerun()

        with tab_register:
            with st.form("register_form"):
                name = st.text_input("Full name", key="reg_name", placeholder="Ada Lovelace")
                reg_email = st.text_input("Email", key="reg_email", placeholder="you@example.com")
                reg_password = st.text_input(
                    "Password", type="password", key="reg_password",
                    placeholder="At least 6 characters",
                )
                role = st.selectbox("I am a...", ["student", "teacher"], key="reg_role")
                submitted = st.form_submit_button("Create account", use_container_width=True)

            if submitted:
                if not name or not reg_email or not reg_password:
                    st.error("Fill in every field to create your account.")
                elif len(reg_password) < 6:
                    st.error("Password needs at least 6 characters.")
                else:
                    data, err = auth_client.safe_call(auth_client.register, name, reg_email, reg_password, role)
                    if err:
                        st.error(err)
                    else:
                        st.session_state["auth_token"] = data["access_token"]
                        st.session_state["user_id"] = data["user_id"]
                        st.session_state["user_name"] = data["name"]
                        st.session_state["user_role"] = data["role"]
                        st.session_state["page"] = "teacher_upload" if data["role"] == "teacher" else "quiz_interface"
                        st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("\u2190 Back to home", use_container_width=True):
            st.session_state["page"] = "landing"
            st.rerun()
