"""
Thin HTTP client Streamlit uses to talk to the FastAPI auth service.
Auth (register/login/me) goes over real HTTP to api/main.py so JWT
issuance/validation lives in one place; the rest of the app (quiz
generation, evaluation, analytics) calls the agent layer in-process.
"""
import sys
from pathlib import Path
import requests

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import settings
from frontend.components import auth_fallback

BASE_URL = settings.api_base_url


def register(name: str, email: str, password: str, role: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/auth/register",
        json={"name": name, "email": email, "password": password, "role": role},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def login(email: str, password: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_me(token: str) -> dict:
    resp = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


class AuthError(Exception):
    pass


def safe_call(fn, *args, **kwargs):
    """
    Wraps requests calls and converts HTTP errors into readable messages
    for the UI. If the FastAPI service is unreachable (e.g. on Streamlit
    Community Cloud, which only runs a single process and can't also
    host api/main.py), transparently falls back to in-process auth via
    auth_fallback.py so the app still works standalone.
    """
    try:
        return fn(*args, **kwargs), None
    except requests.exceptions.ConnectionError:
        fallback_fn = _FALLBACK_MAP.get(fn)
        if fallback_fn:
            try:
                return fallback_fn(*args, **kwargs), None
            except auth_fallback.AuthError as e:
                return None, str(e)
            except Exception as e:
                return None, f"Local auth fallback failed: {e}"
        return None, "Cannot reach the Quizify API. Is the FastAPI backend running (uvicorn api.main:app)?"
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, detail
    except Exception as e:
        return None, str(e)


_FALLBACK_MAP = {
    register: auth_fallback.register,
    login: auth_fallback.login,
}
