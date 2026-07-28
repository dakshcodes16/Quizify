"""
AGENT 1 — Content & Quiz Generation Agent

Responsibilities:
  - Accept uploaded PDF/DOCX/notes text
  - Extract topics, concepts, learning objectives (stored as embeddings)
  - Generate quizzes (MCQ / True-False / Short Answer) grounded in the
    uploaded material via RAG, with Bloom's-taxonomy tagging,
    AI-generated distractors, difficulty balancing, and duplicate
    prevention against previously generated questions.
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils.gemini_client import get_gemini_client
from utils.document_parser import extract_text, chunk_text
from vectorstore.chroma_client import get_vector_store

BLOOM_LEVELS = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
DIFFICULTIES = ["easy", "medium", "hard"]


class ContentQuizAgent:
    """Agent 1: ingests course material and produces structured quizzes."""

    def __init__(self):
        self.llm = get_gemini_client()
        self.vector_store = get_vector_store()

    # ------------------------------------------------------------------
    # Step 1: Ingest uploaded material
    # ------------------------------------------------------------------
    def ingest_material(self, file_path: str, course_id: int) -> Dict:
        """Extract text, chunk it, embed it, and extract structured concepts."""
        raw_text = extract_text(file_path)
        if not raw_text or len(raw_text.strip()) < 50:
            raise ValueError("Could not extract meaningful text from the uploaded file.")

        chunks = chunk_text(raw_text, chunk_size=1200, overlap=150)
        self.vector_store.add_course_chunks(course_id, chunks)

        concepts = self._extract_concepts(raw_text)
        with self.vector_store.batch_concept_writes():
            for c in concepts:
                self.vector_store.add_concept(
                    course_id,
                    f"{c['topic']}: {', '.join(c['key_concepts'])}",
                    metadata={"topic": c["topic"]},
                )

        return {
            "course_id": course_id,
            "num_chunks": len(chunks),
            "concepts": concepts,
            "char_count": len(raw_text),
        }

    def _extract_concepts(self, text: str) -> List[Dict]:
        """Use Gemini to extract structured topics/concepts/objectives."""
        sample = text[:12000]  # cap to keep prompt reasonable; RAG handles the rest
        prompt = f"""You are an expert curriculum analyst. Read the study material below and
extract a structured breakdown of its educational content.

STUDY MATERIAL:
\"\"\"{sample}\"\"\"

Return JSON with this exact shape:
{{
  "topics": [
    {{
      "topic": "short topic name",
      "key_concepts": ["concept 1", "concept 2", "..."],
      "learning_objectives": ["objective 1", "objective 2"],
      "suggested_difficulty": "easy" | "medium" | "hard"
    }}
  ]
}}

Identify 3-8 distinct topics. Be specific and grounded only in the material provided."""

        result = self.llm.generate_json(
            prompt,
            system_instruction="You are a precise curriculum analysis engine. Always return valid JSON.",
            temperature=0.3,
        )
        return result.get("topics", [])

    # ------------------------------------------------------------------
    # Step 2: Generate a quiz (RAG-grounded)
    # ------------------------------------------------------------------
    def generate_quiz(
        self,
        course_id: int,
        topic: str,
        difficulty: str = "medium",
        bloom_level: str = "understand",
        num_questions: int = 5,
        question_types: Optional[List[str]] = None,
        weak_concepts: Optional[List[str]] = None,
    ) -> Dict:
        """
        Generate a quiz grounded in retrieved course content (RAG).
        If weak_concepts is provided (from Agent 3), bias questions
        toward those concepts for adaptive remediation.
        """
        question_types = question_types or ["mcq", "true_false", "short_answer"]
        difficulty = difficulty if difficulty in DIFFICULTIES else "medium"
        bloom_level = bloom_level if bloom_level in BLOOM_LEVELS else "understand"

        retrieval_query = topic
        if weak_concepts:
            retrieval_query += " " + " ".join(weak_concepts)
        context_chunks = self.vector_store.query_course_content(course_id, retrieval_query, n_results=5)
        context = "\n---\n".join(context_chunks) if context_chunks else "(no retrieved context — generate from general knowledge of the topic)"

        focus_instruction = ""
        if weak_concepts:
            focus_instruction = (
                f"\nIMPORTANT: This student is weak in: {', '.join(weak_concepts)}. "
                f"Prioritize questions that directly test these concepts."
            )

        unique_questions = []
        attempts = 0
        max_attempts = 4

        while len(unique_questions) < num_questions and attempts < max_attempts:
            needed = num_questions - len(unique_questions)

            avoid_instruction = ""
            if unique_questions:
                avoid_list = "\n".join([f"- {q.get('question', '')}" for q in unique_questions])
                avoid_instruction = (
                    f"\nIMPORTANT: Do NOT generate questions that are similar to or repeat "
                    f"the following questions that have already been generated:\n{avoid_list}"
                )

            prompt = f"""You are an expert quiz designer creating an adaptive assessment.

TOPIC: {topic}
DIFFICULTY: {difficulty}
BLOOM'S TAXONOMY LEVEL: {bloom_level}
ALLOWED QUESTION TYPES: {', '.join(question_types)}
NUMBER OF QUESTIONS TO GENERATE: {needed}
{focus_instruction}
{avoid_instruction}

GROUNDING CONTEXT FROM COURSE MATERIAL (use this to keep questions accurate and on-topic):
\"\"\"{context}\"\"\"

Generate EXACTLY {needed} new and unique questions. For MCQ, include exactly 4 options with 3 plausible,
well-reasoned distractors (not obviously wrong). For true_false, the statement should
not be trivially guessable. For short_answer, the answer should be a concise, gradable phrase or sentence.

Return JSON with this exact shape:
{{
  "questions": [
    {{
      "type": "mcq" | "true_false" | "short_answer",
      "question": "question text",
      "options": ["A", "B", "C", "D"],
      "answer": "the correct option text (for mcq), 'True'/'False' (for true_false), or model answer (for short_answer)",
      "explanation": "why this is correct, 1-2 sentences",
      "difficulty": "easy" | "medium" | "hard",
      "concept_tag": "the specific concept this tests",
      "time_limit": 30
    }}
  ]
}}
For true_false questions, options should be ["True", "False"]. For short_answer, options should be []. For each question, decide a suitable 'time_limit' in seconds based on the difficulty and question type (e.g. 30 seconds for MCQ/TF easy/medium questions, 45 seconds for MCQ/TF hard questions, and 60-90 seconds for short_answer questions). Keep it as an integer between 30 and 120."""

            result = self.llm.generate_json(
                prompt,
                system_instruction="You are a rigorous assessment design engine. Always return valid, complete JSON.",
                temperature=0.6,
            )

            generated = result.get("questions", [])
            if not isinstance(generated, list):
                generated = []

            filtered = self._filter_duplicates(course_id, generated)
            unique_questions.extend(filtered)
            attempts += 1

        if len(unique_questions) > num_questions:
            unique_questions = unique_questions[:num_questions]

        return {
            "course_id": course_id,
            "topic": topic,
            "difficulty": difficulty,
            "bloom_level": bloom_level,
            "questions": unique_questions,
        }

    def _filter_duplicates(self, course_id: int, questions: List[Dict]) -> List[Dict]:
        """Drop questions that are near-duplicates of previously stored concepts/questions."""
        unique = []
        with self.vector_store.batch_concept_writes():
            for q in questions:
                if not self.vector_store.is_duplicate_question(course_id, q.get("question", "")):
                    unique.append(q)
                    # register it so future generations avoid repeating it
                    # (still written to the in-memory store immediately, so
                    # later questions in this same batch are checked against
                    # it too -- only the disk write is deferred to the end)
                    self.vector_store.add_concept(
                        course_id, q.get("question", ""), metadata={"type": "generated_question"}
                    )
        return unique
