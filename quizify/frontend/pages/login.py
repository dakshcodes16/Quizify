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
                <p style="color:var(--text-secondary);">Faculty Portal — Sign in or create an account to manage courses.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register, tab_join = st.tabs(["Sign in", "Create account", "Join Quiz (Students)"])

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
                submitted = st.form_submit_button("Create account", use_container_width=True)

            if submitted:
                if not name or not reg_email or not reg_password:
                    st.error("Fill in every field to create your account.")
                elif len(reg_password) < 6:
                    st.error("Password needs at least 6 characters.")
                else:
                    # Default role to teacher for registration
                    data, err = auth_client.safe_call(auth_client.register, name, reg_email, reg_password, "teacher")
                    if err:
                        st.error(err)
                    else:
                        st.session_state["auth_token"] = data["access_token"]
                        st.session_state["user_id"] = data["user_id"]
                        st.session_state["user_name"] = data["name"]
                        st.session_state["user_role"] = data["role"]
                        st.session_state["page"] = "teacher_upload" if data["role"] == "teacher" else "quiz_interface"
                        st.rerun()

        with tab_join:
            with st.form("login_join_quiz_form"):
                code = st.text_input("Quiz Code", placeholder="e.g. K9B8JD", key="login_join_code")
                name = st.text_input("Your Name", placeholder="e.g. Jane Doe", key="login_student_name")
                roll_no = st.text_input("Roll Number", placeholder="e.g. 101 or CS-21", key="login_student_roll")
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

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("\u2190 Back to home", use_container_width=True):
            st.session_state["page"] = "landing"
            st.rerun()
