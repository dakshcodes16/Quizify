"""
AGENT 3 — Learning Gap & Adaptive Agent

Responsibilities:
  - Analyze graded quiz results to detect weak concepts / learning gaps
  - Apply the adaptive decision logic (score > 80% -> advance,
    score < 80% -> remediate weak concepts)
  - Maintain a confidence/mastery score per topic over time
  - Recommend the next topic and difficulty level
  - Persist a compact student-context summary to the vector store so
    Agent 1 can ground future quizzes in known weaknesses
"""
import sys
from pathlib import Path
from typing import List, Dict

sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils.gemini_client import get_gemini_client
from vectorstore.chroma_client import get_vector_store

MASTERY_ADVANCE_THRESHOLD = 80.0  # percent, per the spec's decision logic
DIFFICULTY_ORDER = ["easy", "medium", "hard"]


class AdaptiveAgent:
    """Agent 3: detects gaps and decides the next adaptive step."""

    def __init__(self):
        self.llm = get_gemini_client()
        self.vector_store = get_vector_store()

    def analyze(
        self,
        graded_questions: List[Dict],
        accuracy: float,
        current_difficulty: str,
        existing_topic_mastery: Dict[str, float],
    ) -> Dict:
        """
        Pure decision step (no DB/vector-store writes) -- aggregates this
        attempt's per-concept scores, blends with historical mastery,
        and applies the advance/remediate decision rule. Use
        analyze_for_student() instead when you have a real student_id and
        want the gap summary persisted for Agent 1 to ground future quizzes.
        """
        # --- aggregate per-concept performance from this attempt ---
        concept_scores: Dict[str, List[float]] = {}
        for g in graded_questions:
            tag = g.get("concept_tag", "general")
            concept_scores.setdefault(tag, []).append(g["score"])

        attempt_mastery = {
            tag: round((sum(scores) / len(scores)) * 100, 1)
            for tag, scores in concept_scores.items()
        }

        # --- blend with historical mastery (simple exponential update) ---
        updated_mastery = dict(existing_topic_mastery)
        for tag, new_score in attempt_mastery.items():
            prior = updated_mastery.get(tag, new_score)
            updated_mastery[tag] = round(prior * 0.4 + new_score * 0.6, 1)  # weight recent performance higher

        weak_topics = sorted(
            [t for t, score in updated_mastery.items() if score < 70],
            key=lambda t: updated_mastery[t],
        )
        strong_topics = sorted(
            [t for t, score in updated_mastery.items() if score >= 85],
            key=lambda t: -updated_mastery[t],
        )

        # --- apply the spec's decision logic ---
        if accuracy > MASTERY_ADVANCE_THRESHOLD:
            decision = "advance"
            next_difficulty = self._step_difficulty(current_difficulty, up=True)
        else:
            decision = "remediate"
            next_difficulty = self._step_difficulty(current_difficulty, up=False)

        recommended_topics = self._recommend_next_topics(
            weak_topics, strong_topics, decision
        )

        learning_path_note = self._generate_path_narrative(
            decision, accuracy, weak_topics, strong_topics, next_difficulty
        )

        return {
            "decision": decision,
            "accuracy": accuracy,
            "weak_topics": weak_topics,
            "strong_topics": strong_topics,
            "topic_mastery": updated_mastery,
            "next_difficulty": next_difficulty,
            "recommended_topics": recommended_topics,
            "learning_path_note": learning_path_note,
        }

    def analyze_for_student(
        self,
        student_id: int,
        graded_questions: List[Dict],
        accuracy: float,
        current_difficulty: str,
        existing_topic_mastery: Dict[str, float],
    ) -> Dict:
        """Runs analyze() and persists the gap summary under the real student_id
        so Agent 1 can ground future quiz generation in this student's known
        weaknesses. This is the entry point every caller should use."""
        result = self.analyze(graded_questions, accuracy, current_difficulty, existing_topic_mastery)
        if result["weak_topics"]:
            self.vector_store.upsert_student_context(
                student_id=student_id,
                summary=(
                    f"Weak concepts: {', '.join(result['weak_topics'])}. "
                    f"Strong concepts: {', '.join(result['strong_topics'])}. "
                    f"Current mastery: {result['topic_mastery']}."
                ),
            )
        return result

    # ------------------------------------------------------------------
    def _step_difficulty(self, current: str, up: bool) -> str:
        current = current if current in DIFFICULTY_ORDER else "medium"
        idx = DIFFICULTY_ORDER.index(current)
        if up:
            return DIFFICULTY_ORDER[min(idx + 1, len(DIFFICULTY_ORDER) - 1)]
        return DIFFICULTY_ORDER[max(idx - 1, 0)]

    def _recommend_next_topics(
        self, weak_topics: List[str], strong_topics: List[str], decision: str
    ) -> List[str]:
        if decision == "remediate" and weak_topics:
            return weak_topics[:3]
        if decision == "advance" and strong_topics:
            return strong_topics[:2]
        return weak_topics[:2] or strong_topics[:2]

    def _generate_path_narrative(
        self, decision: str, accuracy: float, weak: List[str], strong: List[str], next_difficulty: str
    ) -> str:
        prompt = f"""A student just scored {accuracy}% on a quiz.
Decision: {"advance to harder material" if decision == "advance" else "remediate weak concepts"}.
Weak topics: {weak or 'none'}
Strong topics: {strong or 'none'}
Next difficulty level: {next_difficulty}

Write a 1-2 sentence personalized note explaining what they should do next and why,
in an encouraging coach-like tone."""
        try:
            return self.llm.generate(prompt, temperature=0.6).strip()
        except Exception:
            if decision == "advance":
                return f"Great progress! Moving you to {next_difficulty} difficulty."
            return f"Let's reinforce {', '.join(weak) or 'recent topics'} before moving forward."
