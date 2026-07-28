"""
Quiz repository -- persistence layer connecting Agent 1's in-memory quiz
generation output to real database rows, and connecting those rows back
to a per-student "what's assigned to me" view.

This module exists because quiz generation previously lived entirely in
st.session_state (per-browser, per-user, invisible across sessions), so
a teacher generating a quiz had no way to actually hand it to a specific
student -- there was no shared row either side could reference. Every
function here operates on real Quiz/Question/Assignment/Response rows so
that "assign this quiz to these students" is a real, queryable fact.
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from database.db import get_db_session
from database.models import Quiz, Question, Assignment, Response, User


# ----------------------------------------------------------------------
# Persisting a generated quiz
# ----------------------------------------------------------------------
def save_generated_quiz(course_id: int, quiz_dict: Dict) -> int:
    """
    Persists Agent 1's generate_quiz() output dict as real Quiz + Question
    rows. Returns the new quiz_id.

    quiz_dict shape: {course_id, topic, difficulty, bloom_level, questions: [...]}
    Each question dict: {type, question, options, answer, explanation, difficulty, concept_tag}
    """
    import random
    import string
    with get_db_session() as db:
        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            existing = db.query(Quiz).filter_by(code=code).first()
            if not existing:
                break

        quiz = Quiz(
            course_id=course_id,
            topic=quiz_dict["topic"],
            difficulty=quiz_dict.get("difficulty", "medium"),
            bloom_level=quiz_dict.get("bloom_level", "understand"),
            code=code,
        )
        db.add(quiz)
        db.flush()  # assigns quiz.id

        for q in quiz_dict.get("questions", []):
            question = Question(
                quiz_id=quiz.id,
                question_type=q.get("type", "mcq"),
                question=q.get("question", ""),
                options=q.get("options", []),
                answer=q.get("answer", ""),
                explanation=q.get("explanation", ""),
                difficulty=q.get("difficulty", quiz_dict.get("difficulty", "medium")),
                concept_tag=q.get("concept_tag", quiz_dict.get("topic", "general")),
                time_limit=q.get("time_limit", 30),
            )
            db.add(question)

        db.flush()
        quiz_id = quiz.id
        quiz_dict["code"] = code
    return quiz_id


def load_quiz_as_dict(quiz_id: int) -> Optional[Dict]:
    """
    Loads a persisted Quiz + its Questions back into the same dict shape
    ContentQuizAgent.generate_quiz() produces, so the rest of the
    pipeline (rendering, EvaluationAgent, orchestration) doesn't need to
    know whether a quiz came fresh from the agent or from the database.
    """
    with get_db_session() as db:
        quiz = db.query(Quiz).filter_by(id=quiz_id).first()
        if not quiz:
            return None
        questions = (
            db.query(Question)
            .filter_by(quiz_id=quiz_id)
            .order_by(Question.id)
            .all()
        )
        return {
            "quiz_id": quiz.id,
            "course_id": quiz.course_id,
            "topic": quiz.topic,
            "difficulty": quiz.difficulty,
            "bloom_level": quiz.bloom_level,
            "code": quiz.code,
            "questions": [
                {
                    "id": q.id,
                    "type": q.question_type,
                    "question": q.question,
                    "options": q.options or [],
                    "answer": q.answer,
                    "explanation": q.explanation,
                    "difficulty": q.difficulty,
                    "concept_tag": q.concept_tag,
                    "time_limit": q.time_limit or 30,
                }
                for q in questions
            ],
        }


def access_quiz_by_code(code: str, student_name: str, roll_no: str) -> tuple[Optional[Dict], Optional[User], Optional[str]]:
    """
    Checks if a quiz with the given code exists, gets or creates a guest student user,
    assigns the quiz to them on the fly if needed, and returns (quiz_dict, student_user, error_message).
    """
    code = code.strip().upper()
    student_name = student_name.strip()
    roll_no = roll_no.strip()
    if not code:
        return None, None, "Please enter a quiz code."
    if not student_name:
        return None, None, "Please enter your name."
    if not roll_no:
        return None, None, "Please enter your roll number."

    with get_db_session() as db:
        quiz = db.query(Quiz).filter_by(code=code).first()
        if not quiz:
            return None, None, f"No quiz found with code '{code}'."

        # Query first by roll number for student users
        student = db.query(User).filter_by(roll_no=roll_no, role="student").first()

        if not student:
            # Attempt to create the user without email/password_hash (PostgreSQL / new DBs)
            try:
                with db.begin_nested():
                    student = User(
                        name=student_name,
                        email=None,
                        roll_no=roll_no,
                        password_hash=None,
                        role="student"
                    )
                    db.add(student)
            except Exception:
                # Fallback for legacy SQLite databases with NOT NULL constraints
                import re
                slug = re.sub(r'[^a-zA-Z0-9]', '_', roll_no.lower())
                email = f"guest_roll_{slug}@quizify.guest"

                student = db.query(User).filter_by(email=email).first()

                if not student:
                    from utils.auth_utils import hash_password
                    student = User(
                        name=student_name,
                        email=email,
                        roll_no=roll_no,
                        password_hash=hash_password("guest_session"),
                        role="student"
                    )
                    db.add(student)
                else:
                    # Update existing mock user with name and roll number
                    student.roll_no = roll_no
                    student.name = student_name
                    db.add(student)
            db.flush()
        else:
            # Keep name updated
            student.name = student_name
            db.add(student)
            db.flush()

        # Check/create assignment dynamically so completion tracking works
        existing_assignment = db.query(Assignment).filter_by(quiz_id=quiz.id, student_id=student.id).first()
        if not existing_assignment:
            assigned_by_id = quiz.course.owner_id if (quiz.course and quiz.course.owner_id) else 1
            db.add(
                Assignment(
                    quiz_id=quiz.id,
                    student_id=student.id,
                    assigned_by_id=assigned_by_id,
                )
            )
            db.flush()

        quiz_dict = {
            "quiz_id": quiz.id,
            "course_id": quiz.course_id,
            "topic": quiz.topic,
            "difficulty": quiz.difficulty,
            "bloom_level": quiz.bloom_level,
            "code": quiz.code,
            "questions": [
                {
                    "id": q.id,
                    "type": q.question_type,
                    "question": q.question,
                    "options": q.options or [],
                    "answer": q.answer,
                    "explanation": q.explanation,
                    "difficulty": q.difficulty,
                    "concept_tag": q.concept_tag,
                    "time_limit": q.time_limit or 30,
                }
                for q in db.query(Question).filter_by(quiz_id=quiz.id).order_by(Question.id).all()
            ],
        }

        return quiz_dict, student, None


# ----------------------------------------------------------------------
# Assignment
# ----------------------------------------------------------------------
def assign_quiz(
    quiz_id: int,
    student_ids: List[int],
    assigned_by_id: int,
    due_date: Optional[datetime] = None,
) -> int:
    """
    Creates one Assignment row per student -- this is what actually makes
    "assign to whole class" or "assign to these 3 students" a real,
    independently-trackable fact instead of just UI copy. Skips students
    who already have this exact quiz assigned (idempotent: clicking
    "Assign" twice for the same roster doesn't create duplicate rows).
    Returns the number of new assignment rows created.
    """
    if not student_ids:
        return 0
    with get_db_session() as db:
        existing = {
            row.student_id
            for row in db.query(Assignment.student_id).filter_by(quiz_id=quiz_id).all()
        }
        new_count = 0
        for sid in student_ids:
            if sid in existing:
                continue
            db.add(
                Assignment(
                    quiz_id=quiz_id,
                    student_id=sid,
                    assigned_by_id=assigned_by_id,
                    due_date=due_date,
                )
            )
            new_count += 1
        db.flush()
    return new_count


def get_students_for_teacher(teacher_id: int) -> List[Dict]:
    """
    All students available to assign a quiz to. Quizify doesn't currently
    model class rosters/enrollment, so every student account in the
    system is assignable by every teacher -- documented here as the
    current behavior (a natural extension point: add a Roster/Enrollment
    table to scope this to a teacher's actual class).
    """
    with get_db_session() as db:
        students = db.query(User).filter_by(role="student").order_by(User.roll_no).all()
        return [{"id": s.id, "name": s.name, "email": s.email, "roll_no": s.roll_no} for s in students]


def get_assigned_quizzes_for_student(student_id: int, only_pending: bool = True) -> List[Dict]:
    """
    Returns assignments for a student, most recently assigned first.
    With only_pending=True (default), excludes assignments already
    completed -- this is what the student-facing Quiz page uses to show
    "what's actually waiting for me to take", instead of the old behavior
    of reading st.session_state (which a teacher's browser session could
    never write into on the student's behalf).
    """
    with get_db_session() as db:
        query = db.query(Assignment).filter_by(student_id=student_id)
        if only_pending:
            query = query.filter_by(completed=False)
        assignments = query.order_by(Assignment.assigned_at.desc()).all()

        results = []
        for a in assignments:
            quiz = a.quiz
            results.append(
                {
                    "assignment_id": a.id,
                    "quiz_id": a.quiz_id,
                    "topic": quiz.topic if quiz else "Unknown",
                    "difficulty": quiz.difficulty if quiz else "medium",
                    "bloom_level": quiz.bloom_level if quiz else "understand",
                    "course_id": quiz.course_id if quiz else None,
                    "assigned_at": a.assigned_at,
                    "due_date": a.due_date,
                    "completed": a.completed,
                    "num_questions": len(quiz.questions) if quiz else 0,
                }
            )
        return results


def mark_assignment_completed(quiz_id: int, student_id: int) -> None:
    """Marks the (quiz_id, student_id) assignment as completed, if one exists.
    Self-generated quizzes (the fallback practice-quiz path) have no
    matching assignment row, which is fine -- this is a no-op for those."""
    with get_db_session() as db:
        assignment = (
            db.query(Assignment)
            .filter_by(quiz_id=quiz_id, student_id=student_id)
            .first()
        )
        if assignment:
            assignment.completed = True
            assignment.completed_at = datetime.utcnow()
            db.add(assignment)


# ----------------------------------------------------------------------
# Responses (per-question grading detail, persisted)
# ----------------------------------------------------------------------
def save_responses(
    student_id: int,
    quiz_id: int,
    graded_questions: List[Dict],
) -> None:
    """
    Persists one Response row per graded question. graded_questions is
    EvaluationAgent.evaluate_quiz()'s "graded_questions" list, where each
    entry has question_index (position within the quiz) plus score/
    is_correct/feedback/student_answer. question_index is mapped back to
    a real question_id by position, since that's how the quiz was
    rendered to the student in the first place.
    """
    with get_db_session() as db:
        questions = (
            db.query(Question)
            .filter_by(quiz_id=quiz_id)
            .order_by(Question.id)
            .all()
        )
        for g in graded_questions:
            idx = g.get("question_index")
            if idx is None or idx >= len(questions):
                continue
            question = questions[idx]
            db.add(
                Response(
                    student_id=student_id,
                    question_id=question.id,
                    quiz_id=quiz_id,
                    response=str(g.get("student_answer", "")),
                    is_correct=bool(g.get("is_correct", False)),
                    score=float(g.get("score", 0.0)),
                    ai_feedback=g.get("feedback", ""),
                )
            )
