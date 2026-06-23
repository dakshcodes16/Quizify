"""
AGENT 2 — Evaluation & Feedback Agent

Responsibilities:
  - Grade MCQ/True-False deterministically
  - Grade short-answer questions via semantic/LLM-based evaluation
    with partial credit
  - Generate personalized AI feedback, hints, and improvement
    suggestions per question and per quiz attempt
"""
import sys
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils.gemini_client import get_gemini_client

MAX_PARALLEL_GRADING_CALLS = 6


class EvaluationAgent:
    """Agent 2: scores responses and produces feedback."""

    def __init__(self):
        self.llm = get_gemini_client()

    def evaluate_quiz(self, questions: List[Dict], student_responses: List[Dict]) -> Dict:
        """
        questions: [{type, question, options, answer, explanation, concept_tag, difficulty}, ...]
        student_responses: [{question_index, response}, ...] (aligned by index)

        Returns a full evaluation report with per-question grading and
        an overall AI feedback summary.

        Each question's grading (and any hint it needs) is an independent
        LLM call, so they're dispatched concurrently via a thread pool
        rather than one-by-one -- on a 10-question quiz with several
        short-answer/incorrect questions this is the difference between
        ~1 round-trip and ~15-20 sequential round-trips.
        """
        def grade_one(i: int, q: Dict) -> Dict:
            student_answer = next(
                (r["response"] for r in student_responses if r.get("question_index") == i), ""
            )
            if q["type"] in ("mcq", "true_false"):
                result = self._grade_objective(q, student_answer)
            else:
                result = self._grade_subjective(q, student_answer)
            result["question_index"] = i
            result["concept_tag"] = q.get("concept_tag", q.get("topic", "general"))
            result["difficulty"] = q.get("difficulty", "medium")
            return result

        if len(questions) <= 1:
            graded = [grade_one(i, q) for i, q in enumerate(questions)]
        else:
            with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_GRADING_CALLS, len(questions))) as pool:
                graded = list(pool.map(lambda iq: grade_one(*iq), enumerate(questions)))
            graded.sort(key=lambda g: g["question_index"])

        total_score = sum(g["score"] for g in graded)
        max_score = len(graded) if graded else 1
        accuracy = round((total_score / max_score) * 100, 1) if max_score else 0.0

        mistakes = [g for g in graded if g["score"] < 1.0]
        overall_feedback = self._generate_overall_feedback(graded, accuracy)

        return {
            "graded_questions": graded,
            "total_score": round(total_score, 2),
            "max_score": max_score,
            "accuracy": accuracy,
            "mistakes": mistakes,
            "ai_feedback_report": overall_feedback,
        }

    # ------------------------------------------------------------------
    def _grade_objective(self, question: Dict, student_answer: str) -> Dict:
        """Deterministic exact-match grading for MCQ / True-False, with a hint on failure."""
        correct_answer = str(question.get("answer", "")).strip().lower()
        given = str(student_answer or "").strip().lower()
        is_correct = given == correct_answer and given != ""

        feedback = question.get("explanation", "")
        hint = None
        if not is_correct:
            hint = self._generate_hint(question)

        return {
            "is_correct": is_correct,
            "score": 1.0 if is_correct else 0.0,
            "student_answer": student_answer,
            "correct_answer": question.get("answer", ""),
            "feedback": feedback,
            "hint": hint,
        }

    def _grade_subjective(self, question: Dict, student_answer: str) -> Dict:
        """LLM-based semantic evaluation with partial credit for short-answer questions."""
        if not student_answer or not student_answer.strip():
            return {
                "is_correct": False,
                "score": 0.0,
                "student_answer": student_answer,
                "correct_answer": question.get("answer", ""),
                "feedback": "No answer was provided.",
                "hint": self._generate_hint(question),
            }

        prompt = f"""You are grading a short-answer exam question. Evaluate the student's answer
for semantic correctness against the model answer — do not require exact wording, only
correct meaning and key facts.

QUESTION: {question.get('question')}
MODEL ANSWER: {question.get('answer')}
STUDENT ANSWER: {student_answer}

Return JSON:
{{
  "score": <float 0.0 to 1.0, where 1.0 is fully correct, 0.5 is partially correct, 0.0 is incorrect>,
  "is_correct": <true if score >= 0.7>,
  "feedback": "specific, encouraging feedback on what was right/wrong, 1-3 sentences",
  "missing_points": ["key point the student missed", "..."] 
}}"""

        try:
            result = self.llm.generate_json(
                prompt,
                system_instruction="You are a fair, consistent exam grader. Always return valid JSON.",
                temperature=0.2,
            )
            score = float(result.get("score", 0.0))
            score = max(0.0, min(1.0, score))
            return {
                "is_correct": bool(result.get("is_correct", score >= 0.7)),
                "score": score,
                "student_answer": student_answer,
                "correct_answer": question.get("answer", ""),
                "feedback": result.get("feedback", ""),
                "missing_points": result.get("missing_points", []),
                "hint": self._generate_hint(question) if score < 0.7 else None,
            }
        except Exception:
            # graceful fallback if the LLM call fails
            return {
                "is_correct": False,
                "score": 0.0,
                "student_answer": student_answer,
                "correct_answer": question.get("answer", ""),
                "feedback": "Could not auto-grade this answer; please review manually.",
                "hint": None,
            }

    def _generate_hint(self, question: Dict) -> str:
        """Short, non-revealing hint for an incorrectly answered question."""
        prompt = f"""Give a brief, helpful hint (1 sentence, do NOT reveal the answer) for this question
to help the student understand it better next time:

QUESTION: {question.get('question')}
CONCEPT: {question.get('concept_tag', 'general')}

Return only the hint text, no JSON, no quotes."""
        try:
            return self.llm.generate(prompt, temperature=0.5).strip()
        except Exception:
            return "Review the related concept in your course material and try again."

    def _generate_overall_feedback(self, graded: List[Dict], accuracy: float) -> str:
        """Holistic, encouraging feedback summary for the whole quiz attempt."""
        weak_concepts = list({g["concept_tag"] for g in graded if g["score"] < 0.7})
        strong_concepts = list({g["concept_tag"] for g in graded if g["score"] >= 0.7})

        prompt = f"""A student just completed a quiz with {accuracy}% accuracy.
Concepts they struggled with: {weak_concepts or 'none'}
Concepts they handled well: {strong_concepts or 'none'}

Write a short (2-4 sentence), encouraging but honest feedback summary. Be specific about
what to focus on next. Avoid generic platitudes."""
        try:
            return self.llm.generate(prompt, temperature=0.6).strip()
        except Exception:
            return f"You scored {accuracy}%. Focus on reviewing: {', '.join(weak_concepts) or 'your recent topics'}."
