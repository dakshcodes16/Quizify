"""
SQLAlchemy ORM models for Quizify.

Tables map to the spec (Users, Courses, Quizzes, Questions, Responses,
Analytics) plus supporting tables needed to make the features in the
spec (badges, leaderboard, quiz attempts, learning gaps) actually work.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default="student")  # "student" | "teacher"
    roll_no = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    courses = relationship("Course", back_populates="owner", cascade="all, delete-orphan")
    responses = relationship("Response", back_populates="student", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="student", uselist=False, cascade="all, delete-orphan")
    badges = relationship("Badge", back_populates="student", cascade="all, delete-orphan")
    assignments_received = relationship(
        "Assignment", back_populates="student", foreign_keys="Assignment.student_id", cascade="all, delete-orphan"
    )


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    uploaded_material = Column(String(500))  # path to original file
    owner_id = Column(Integer, ForeignKey("users.id"))
    extracted_concepts = Column(JSON, default=list)  # list of {topic, concepts, objectives}
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="courses")
    quizzes = relationship("Quiz", back_populates="course")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    topic = Column(String(255), nullable=False)
    difficulty = Column(String(20), default="medium")  # easy | medium | hard
    bloom_level = Column(String(30), default="understand")
    created_for_student_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    code = Column(String(50), unique=True, index=True, nullable=True)

    course = relationship("Course", back_populates="quizzes")
    questions = relationship("Question", back_populates="quiz")
    assignments = relationship("Assignment", back_populates="quiz")


class Assignment(Base):
    """
    Links a Quiz to the student(s) it was assigned to. A teacher can assign
    one generated quiz to multiple students (or the whole class) -- this is
    a proper many-rows-per-quiz join table rather than overloading a single
    nullable FK on Quiz, since "assign to the whole class" needs N rows,
    one per student, each independently trackable as completed or not.
    """
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    quiz = relationship("Quiz", back_populates="assignments")
    student = relationship("User", foreign_keys=[student_id], back_populates="assignments_received")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    question_type = Column(String(20), default="mcq")  # mcq | true_false | short_answer
    question = Column(Text, nullable=False)
    options = Column(JSON, default=list)  # for MCQ
    answer = Column(Text, nullable=False)
    explanation = Column(Text)
    difficulty = Column(String(20), default="medium")
    concept_tag = Column(String(255))
    time_limit = Column(Integer, default=30)

    quiz = relationship("Quiz", back_populates="questions")
    responses = relationship("Response", back_populates="question")


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    response = Column(Text)
    is_correct = Column(Boolean, default=False)
    score = Column(Float, default=0.0)  # supports partial scoring 0-1
    ai_feedback = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="responses")
    question = relationship("Question", back_populates="responses")


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id"), unique=True)
    mastery_score = Column(Float, default=0.0)  # 0-100 overall
    weak_topics = Column(JSON, default=list)
    strong_topics = Column(JSON, default=list)
    topic_mastery = Column(JSON, default=dict)  # {topic: 0-100}
    quizzes_taken = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    last_active_date = Column(DateTime, default=datetime.utcnow)
    history = Column(JSON, default=list)  # [{date, score, topic}]

    student = relationship("User", back_populates="analytics")


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(120))
    description = Column(String(255))
    icon = Column(String(10), default="🏆")
    earned_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="badges")
