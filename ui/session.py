"""Login state, role guard and logout for Streamlit pages."""
import streamlit as st

from logic import remember

USER_KEY = "user"
COOKIE_KEY = "device_cookie"  # what the browser should do with the cookie: {"action": "set"|"clear", "token": ...}

_COOKIE_JS = """\
export default function (component) {
  const { action, token, name, days } = component.data || {}
  if (!action) return
  const secure = location.protocol === "https:" ? "; Secure" : ""
  const life = action === "set" ? `; Max-Age=${days * 86400}` : "; Max-Age=0"
  document.cookie = `${name}=${action === "set" ? token : ""}; Path=/; SameSite=Lax${secure}${life}`
}
"""
_COOKIE = st.components.v2.component("device_cookie", html="<span></span>", js=_COOKIE_JS)


def render_device_cookie() -> None:
    """Apply the pending cookie change in the browser. Idempotent, so it is safe to call on every run."""
    action = st.session_state.get(COOKIE_KEY)
    if action:
        _COOKIE(key="device_cookie_c", data={**action, "name": remember.COOKIE, "days": remember.DAYS})


def restore_device() -> None:
    """If nobody is signed in and this browser holds a valid device cookie, sign that student in."""
    if current_user():
        return
    token = st.context.cookies.get(remember.COOKIE)
    try:
        student = remember.restore(token)
    except Exception:  # database hiccup: fall back to the normal login form
        return
    if student:
        st.session_state[USER_KEY] = {"role": "student", **student}
        st.session_state["device_token"] = token


def current_user() -> dict | None:
    """Return the logged-in user dict or None. Students: id, name, roll. Staff: id, name, department, username, is_admin (admin department is 'admin' and sees every department)."""
    return st.session_state.get(USER_KEY)


def login_student(student: dict, remember_me: bool = False) -> None:
    """Sign a student in. With remember_me, this device stays signed in for 30 days."""
    st.session_state[USER_KEY] = {"role": "student", **student}
    if remember_me:
        try:
            token = remember.issue(student["id"])
        except Exception:  # not remembering is better than failing the login
            return
        st.session_state["device_token"] = token
        st.session_state[COOKIE_KEY] = {"action": "set", "token": token}


def login_staff(staff: dict) -> None:
    st.session_state[USER_KEY] = {"role": "staff", **staff}


def logout() -> None:
    """Sign out and forget this device."""
    theme = st.session_state.get("theme")
    token = st.session_state.get("device_token") or st.context.cookies.get(remember.COOKIE)
    try:
        remember.forget(token)
    except Exception:
        pass
    st.session_state.clear()
    st.session_state[COOKIE_KEY] = {"action": "clear"}
    if theme:
        st.session_state["theme"] = theme


def require_role(*roles: str) -> dict:
    """Stop the page unless the user has one of the given roles."""
    user = current_user()
    if not user or user["role"] not in roles:
        st.warning("Please log in from the Home page to see this.")
        st.stop()
    return user
