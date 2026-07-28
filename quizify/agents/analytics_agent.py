"""
AGENT 4 — Analytics & Progress Agent

Responsibilities:
  - Persist analytics after each quiz attempt (mastery, streaks, history)
  - Compute progress curves, heatmap data, and learning streaks
  - Award gamification badges
  - Build faculty-level aggregate insights across all students
  - Generate a PDF progress report
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

sys.path.append(str(Path(__file__).resolve().parent.parent))
from database.db import get_db_session
from database.models import Analytics, Badge, User, Response, Question, Quiz

BADGE_RULES = [
    {"name": "First Steps", "icon": "🎯", "condition": lambda a: a.quizzes_taken == 1,
     "description": "Completed your first quiz"},
    {"name": "On a Roll", "icon": "🔥", "condition": lambda a: a.current_streak >= 3,
     "description": "3-day learning streak"},
    {"name": "Unstoppable", "icon": "⚡", "condition": lambda a: a.current_streak >= 7,
     "description": "7-day learning streak"},
    {"name": "Master Mind", "icon": "🧠", "condition": lambda a: a.mastery_score >= 90,
     "description": "Reached 90+ overall mastery"},
    {"name": "Quiz Veteran", "icon": "🏅", "condition": lambda a: a.quizzes_taken >= 10,
     "description": "Completed 10 quizzes"},
]


class AnalyticsAgent:
    """Agent 4: tracks progress, computes analytics, builds dashboards/reports."""

    # ------------------------------------------------------------------
    def record_attempt(
        self,
        student_id: int,
        quiz_id: int,
        topic: str,
        accuracy: float,
        topic_mastery: Dict[str, float],
        weak_topics: List[str],
        strong_topics: List[str],
    ) -> Dict:
        """Update the student's Analytics row after a graded quiz attempt."""
        with get_db_session() as db:
            analytics = db.query(Analytics).filter_by(student_id=student_id).first()
            is_new = analytics is None
            if is_new:
                analytics = Analytics(
                    student_id=student_id, history=[], topic_mastery={},
                    weak_topics=[], strong_topics=[], current_streak=0, last_active_date=None,
                )
                db.add(analytics)
                db.flush()

            # streak logic: consecutive calendar days with activity.
            # `is_new` is checked explicitly (rather than relying on
            # last_active_date being None) because SQLAlchemy's column
            # `default=` fires on flush even when None was assigned
            # explicitly, which would otherwise mask a brand-new row.
            today = datetime.utcnow().date()
            if is_new:
                analytics.current_streak = 1
            else:
                last_active = analytics.last_active_date.date() if analytics.last_active_date else None
                if last_active == today:
                    pass  # already active today, streak unchanged
                elif last_active == today - timedelta(days=1):
                    analytics.current_streak = (analytics.current_streak or 0) + 1
                else:
                    analytics.current_streak = 1
            analytics.last_active_date = datetime.utcnow()

            analytics.quizzes_taken = (analytics.quizzes_taken or 0) + 1
            analytics.topic_mastery = {**(analytics.topic_mastery or {}), **topic_mastery}
            analytics.weak_topics = weak_topics
            analytics.strong_topics = strong_topics
            analytics.mastery_score = round(
                sum(analytics.topic_mastery.values()) / len(analytics.topic_mastery), 1
            ) if analytics.topic_mastery else accuracy

            history = list(analytics.history or [])
            history.append({
                "date": datetime.utcnow().isoformat(),
                "topic": topic,
                "accuracy": accuracy,
                "quiz_id": quiz_id,
            })
            analytics.history = history

            new_badges = self._check_badges(db, student_id, analytics)

            db.add(analytics)
            db.flush()
            return {
                "mastery_score": analytics.mastery_score,
                "current_streak": analytics.current_streak,
                "quizzes_taken": analytics.quizzes_taken,
                "new_badges": new_badges,
            }

    def _check_badges(self, db, student_id: int, analytics: Analytics) -> List[Dict]:
        existing = {b.name for b in db.query(Badge).filter_by(student_id=student_id).all()}
        newly_earned = []
        for rule in BADGE_RULES:
            if rule["name"] not in existing and rule["condition"](analytics):
                badge = Badge(
                    student_id=student_id,
                    name=rule["name"],
                    description=rule["description"],
                    icon=rule["icon"],
                )
                db.add(badge)
                newly_earned.append({"name": rule["name"], "icon": rule["icon"], "description": rule["description"]})
        return newly_earned

    # ------------------------------------------------------------------
    def get_student_dashboard(self, student_id: int) -> Dict:
        """Aggregate everything needed for the student-facing dashboard."""
        with get_db_session() as db:
            analytics = db.query(Analytics).filter_by(student_id=student_id).first()
            badges = db.query(Badge).filter_by(student_id=student_id).all()
            if not analytics:
                return {
                    "mastery_score": 0, "current_streak": 0, "quizzes_taken": 0,
                    "weak_topics": [], "strong_topics": [], "topic_mastery": {},
                    "history": [], "badges": [],
                }
            return {
                "mastery_score": analytics.mastery_score,
                "current_streak": analytics.current_streak,
                "quizzes_taken": analytics.quizzes_taken,
                "weak_topics": analytics.weak_topics or [],
                "strong_topics": analytics.strong_topics or [],
                "topic_mastery": analytics.topic_mastery or {},
                "history": analytics.history or [],
                "badges": [{"name": b.name, "icon": b.icon, "description": b.description} for b in badges],
            }

    # ------------------------------------------------------------------
    def get_faculty_dashboard(self) -> Dict:
        """Aggregate insights across all students for the faculty dashboard."""
        with get_db_session() as db:
            students = db.query(User).filter_by(role="student").all()
            # Sort by roll_no (handling None values by sorting them at the end/using empty string)
            students = sorted(students, key=lambda s: s.roll_no if s.roll_no is not None else "")
            rows = []
            all_weak_topics: Dict[str, int] = {}
            mastery_values = []

            for s in students:
                analytics = db.query(Analytics).filter_by(student_id=s.id).first()
                mastery = analytics.mastery_score if analytics else 0
                quizzes_taken = analytics.quizzes_taken if analytics else 0
                weak = analytics.weak_topics if analytics else []
                streak = analytics.current_streak if analytics else 0

                for t in weak:
                    all_weak_topics[t] = all_weak_topics.get(t, 0) + 1

                if quizzes_taken > 0:
                    mastery_values.append(mastery)

                rows.append({
                    "student_id": s.id,
                    "name": s.name,
                    "roll_no": s.roll_no,
                    "email": s.email,
                    "mastery_score": mastery,
                    "quizzes_taken": quizzes_taken,
                    "weak_topics": weak,
                    "streak": streak,
                })

            class_avg_mastery = round(sum(mastery_values) / len(mastery_values), 1) if mastery_values else 0
            top_weak_topics = sorted(all_weak_topics.items(), key=lambda x: -x[1])[:5]

            leaderboard = sorted(rows, key=lambda r: -r["mastery_score"])[:10]

            return {
                "students": rows,
                "class_avg_mastery": class_avg_mastery,
                "total_students": len(rows),
                "top_weak_topics": top_weak_topics,
                "leaderboard": leaderboard,
            }

    # ------------------------------------------------------------------
    def export_pdf_report(self, student_id: int, output_path: str) -> str:
        """Generate a PDF progress report for a student using reportlab."""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        dashboard = self.get_student_dashboard(student_id)
        with get_db_session() as db:
            student = db.query(User).filter_by(id=student_id).first()
            student_name = student.name if student else f"Student #{student_id}"
            student_roll = student.roll_no if student else ""

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], textColor=colors.HexColor("#6C5CE7"))

        elements = [
            Paragraph("Quizify — Progress Report", title_style),
            Spacer(1, 12),
            Paragraph(f"Student: {student_name}", styles["Heading2"]),
        ]
        if student_roll:
            elements.append(Paragraph(f"Roll Number: {student_roll}", styles["Heading3"]))
        elements.extend([
            Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
            Spacer(1, 16),
            Paragraph(f"Overall Mastery Score: {dashboard['mastery_score']}%", styles["Heading3"]),
            Paragraph(f"Quizzes Taken: {dashboard['quizzes_taken']}", styles["Normal"]),
            Paragraph(f"Current Streak: {dashboard['current_streak']} days", styles["Normal"]),
            Spacer(1, 16),
        ])

        if dashboard["topic_mastery"]:
            elements.append(Paragraph("Topic Mastery", styles["Heading3"]))
            data = [["Topic", "Mastery %"]] + [[t, f"{m}%"] for t, m in dashboard["topic_mastery"].items()]
            table = Table(data, colWidths=[300, 100])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6C5CE7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 16))

        if dashboard["weak_topics"]:
            elements.append(Paragraph("Areas to Improve", styles["Heading3"]))
            elements.append(Paragraph(", ".join(dashboard["weak_topics"]), styles["Normal"]))
            elements.append(Spacer(1, 12))

        if dashboard["badges"]:
            elements.append(Paragraph("Badges Earned", styles["Heading3"]))
            elements.append(Paragraph(", ".join(f"{b['icon']} {b['name']}" for b in dashboard["badges"]), styles["Normal"]))

        doc.build(elements)
        return output_path
