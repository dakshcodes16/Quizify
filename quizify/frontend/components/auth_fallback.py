"""
In-process auth fallback, used only when the FastAPI service is
unreachable (e.g. Streamlit Community Cloud, which can only run a
single `streamlit run` process and has no separate place to host
api/main.py).

This mirrors api/auth_routes.py's logic exactly (same password
hashing, same JWT signing) but calls the database directly instead of
over HTTP, so behavior is identical whether or not FastAPI is running
alongside it. frontend/components/auth_client.py tries the real HTTP
API first and only falls back to this module on a connection error.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from database.db import get_db_session
from database.models import User
from utils.auth_utils import hash_password, verify_password, create_access_token


class AuthError(Exception):
    pass


def register(name: str, email: str, password: str, role: str) -> dict:
    with get_db_session() as db:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise AuthError("Email already registered.")
        user = User(name=name, email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        db.flush()
        token = create_access_token({"sub": str(user.id), "role": user.role})
        return {
            "access_token": token, "token_type": "bearer",
            "user_id": user.id, "name": user.name, "role": user.role,
        }


def login(email: str, password: str) -> dict:
    with get_db_session() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password.")
        token = create_access_token({"sub": str(user.id), "role": user.role})
        return {
            "access_token": token, "token_type": "bearer",
            "user_id": user.id, "name": user.name, "role": user.role,
        }
