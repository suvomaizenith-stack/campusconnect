"""Login state, role guard and logout for Streamlit pages."""
import streamlit as st

from logic import assignment

USER_KEY = "user"


def current_user() -> dict | None:
    """Return the logged-in user dict or None. Students: id, name, roll. Staff: id, name, department, username, is_admin (admin department is 'admin' and sees every department)."""
    return st.session_state.get(USER_KEY)


def login_student(student: dict) -> None:
    st.session_state[USER_KEY] = {"role": "student", **student}


def login_staff(staff: dict) -> None:
    st.session_state[USER_KEY] = {"role": "staff", **staff}


def logout() -> None:
    """Clear the session; staff are set offline first so new tickets do not go to them."""
    user = current_user()
    if user and user["role"] == "staff":
        try:
            assignment.go_offline(user)
        except Exception:
            pass
    st.session_state.clear()


def require_role(*roles: str) -> dict:
    """Stop the page unless the user has one of the given roles."""
    user = current_user()
    if not user or user["role"] not in roles:
        st.warning("Please log in from the Home page to see this.")
        st.stop()
    return user
