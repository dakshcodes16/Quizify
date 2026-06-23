"""
FastAPI data routes — REST surface over courses, quizzes, and analytics.
Streamlit calls the agent layer directly for the core learning loop, but
these routes exist so the platform has a genuine API surface (for
external integrations, mobile clients, etc.) beyond just auth.
"""
import sys
from pathlib import Path
from typing import List, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Course, Quiz, User
from api.auth_routes import get_current_user
from agents.analytics_agent import AnalyticsAgent

router = APIRouter(prefix="/api", tags=["data"])
analytics_agent = AnalyticsAgent()


@router.get("/courses")
def list_courses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "teacher":
        courses = db.query(Course).filter(Course.owner_id == current_user.id).all()
    else:
        courses = db.query(Course).all()
    return [
        {"id": c.id, "title": c.title, "owner_id": c.owner_id, "created_at": c.created_at}
        for c in courses
    ]


@router.get("/courses/{course_id}/quizzes")
def list_quizzes(course_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quizzes = db.query(Quiz).filter(Quiz.course_id == course_id).all()
    return [
        {"id": q.id, "topic": q.topic, "difficulty": q.difficulty, "bloom_level": q.bloom_level}
        for q in quizzes
    ]


@router.get("/students/{student_id}/dashboard")
def student_dashboard(student_id: int, current_user: User = Depends(get_current_user)):
    if current_user.role == "student" and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Cannot view another student's dashboard.")
    return analytics_agent.get_student_dashboard(student_id)


@router.get("/faculty/dashboard")
def faculty_dashboard(current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Faculty access only.")
    return analytics_agent.get_faculty_dashboard()
