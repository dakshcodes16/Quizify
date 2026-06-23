"""
Smoke test - verifies the full stack (DB, vector store, auth, all 4
agents, LangGraph orchestration) wires together correctly WITHOUT
requiring a live GEMINI_API_KEY, by mocking the LLM calls. Useful to
confirm a fresh install works before plugging in a real key.

Run with: python scripts/smoke_test.py
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parent.parent))

from database.db import init_db, get_db_session
from database.models import User


def main():
    print("1. Initializing database...")
    init_db()
    print("   OK")

    print("2. Creating a test user...")
    with get_db_session() as db:
        existing = db.query(User).filter_by(email="smoketest@gmail.com").first()
        if existing:
            db.delete(existing)
            db.flush()
        user = User(name="Smoke Test", email="smoketest@gmail.com", password_hash="x", role="student")
        db.add(user)
        db.flush()
        student_id = user.id
    print(f"   OK (user_id={student_id})")

    print("3. Testing vector store...")
    from vectorstore.chroma_client import get_vector_store
    vs = get_vector_store()
    vs.add_course_chunks(999, ["Test chunk about the water cycle and evaporation."])
    results = vs.query_course_content(999, "water cycle", n_results=1)
    assert results, "Vector store query returned nothing"
    print("   OK")

    print("4. Testing orchestration graph (mocked Gemini)...")
    from utils import gemini_client as gc_module

    class FakeGroq:
        def generate(self, prompt, system_instruction=None, temperature=0.7, max_retries=3):
            return "Mock feedback text."

        def generate_json(self, prompt, system_instruction=None, temperature=0.5, max_retries=3):
            return {"score": 1.0, "is_correct": True, "feedback": "Correct.", "missing_points": []}

    with patch.object(gc_module, "get_gemini_client", return_value=FakeGroq()):
        import backend.orchestration as orch
        orch._content_agent = orch._eval_agent = orch._adaptive_agent = orch._analytics_agent = None

        state = {
            "student_id": student_id,
            "topic": "Water Cycle",
            "difficulty": "medium",
            "quiz_id": 1,
            "existing_topic_mastery": {},
            "generated_quiz": {
                "questions": [
                    {"type": "mcq", "question": "What causes rain?", "options": ["A", "B", "C", "D"],
                     "answer": "A", "explanation": "Condensation", "concept_tag": "precipitation", "difficulty": "easy"},
                ]
            },
            "student_responses": [{"question_index": 0, "response": "A"}],
        }
        result = orch.run_evaluation_cycle(state)
        assert result.get("error") is None, f"Orchestration error: {result.get('error')}"
        assert result["evaluation_result"]["accuracy"] == 100.0
        assert result["adaptive_result"]["decision"] == "advance"
        assert result["analytics_result"]["quizzes_taken"] >= 1
    print("   OK - evaluate -> adapt -> analytics ran end-to-end")

    print("5. Testing PDF export...")
    from agents.analytics_agent import AnalyticsAgent
    aa = AnalyticsAgent()
    # tempfile.gettempdir() resolves correctly on every OS (Windows: %TEMP%,
    # macOS/Linux: /tmp) -- a hardcoded "/tmp/..." path here previously
    # crashed this step on Windows with FileNotFoundError, since Windows
    # has no /tmp directory.
    report_path = str(Path(tempfile.gettempdir()) / "quizify_smoke_test_report.pdf")
    path = aa.export_pdf_report(student_id, report_path)
    assert Path(path).exists() and Path(path).stat().st_size > 0
    Path(path).unlink(missing_ok=True)  # clean up the test artifact
    print("   OK")

    print("\nAll smoke tests passed. The stack is wired correctly.")
    print("Add a real GROQ_API_KEY to .env to enable live AI generation. Free key at https://console.groq.com")


if __name__ == "__main__":
    main()
