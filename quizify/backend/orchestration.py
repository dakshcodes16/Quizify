"""
Agent Orchestration — LangGraph

Wires Agent 1 (Content & Quiz), Agent 2 (Evaluation), Agent 3 (Adaptive),
and Agent 4 (Analytics) into a single stateful graph with shared memory,
matching the workflow:

    upload -> embed -> generate quiz -> student answers -> evaluate
    -> detect gaps -> adapt path -> update analytics -> (loop)

Two entry points are exposed because the workflow has a natural pause
for human input (the student answering the quiz):

  - `run_quiz_generation(state)`  : upload/embed -> generate quiz
  - `run_evaluation_cycle(state)` : evaluate -> adapt -> analytics

Both share the same `QuizifyState` shape so LangGraph's state object
acts as the shared memory / context-persistence layer between agents.
"""
import sys
from pathlib import Path
from typing import TypedDict, List, Dict, Optional, Any

sys.path.append(str(Path(__file__).resolve().parent.parent))
from langgraph.graph import StateGraph, END

from agents.content_quiz_agent import ContentQuizAgent
from agents.evaluation_agent import EvaluationAgent
from agents.adaptive_agent import AdaptiveAgent
from agents.analytics_agent import AnalyticsAgent


class QuizifyState(TypedDict, total=False):
    # ---- shared identifiers ----
    course_id: int
    student_id: int
    quiz_id: int
    topic: str

    # ---- content ingestion (Agent 1) ----
    file_path: Optional[str]
    ingestion_result: Optional[Dict]

    # ---- quiz generation (Agent 1) ----
    difficulty: str
    bloom_level: str
    num_questions: int
    question_types: List[str]
    weak_concepts: Optional[List[str]]
    generated_quiz: Optional[Dict]

    # ---- student responses (human-in-the-loop) ----
    student_responses: Optional[List[Dict]]

    # ---- evaluation (Agent 2) ----
    evaluation_result: Optional[Dict]

    # ---- adaptive analysis (Agent 3) ----
    existing_topic_mastery: Dict[str, float]
    adaptive_result: Optional[Dict]

    # ---- analytics (Agent 4) ----
    analytics_result: Optional[Dict]

    # ---- error channel ----
    error: Optional[str]


# Agent instances are created lazily (they touch network/DB on init in
# some configs), shared across graph invocations for efficiency.
_content_agent: Optional[ContentQuizAgent] = None
_eval_agent: Optional[EvaluationAgent] = None
_adaptive_agent: Optional[AdaptiveAgent] = None
_analytics_agent: Optional[AnalyticsAgent] = None


def _agents():
    global _content_agent, _eval_agent, _adaptive_agent, _analytics_agent
    if _content_agent is None:
        _content_agent = ContentQuizAgent()
        _eval_agent = EvaluationAgent()
        _adaptive_agent = AdaptiveAgent()
        _analytics_agent = AnalyticsAgent()
    return _content_agent, _eval_agent, _adaptive_agent, _analytics_agent


# ----------------------------------------------------------------------
# Graph nodes
# ----------------------------------------------------------------------
def ingest_node(state: QuizifyState) -> QuizifyState:
    content_agent, *_ = _agents()
    try:
        if state.get("file_path"):
            result = content_agent.ingest_material(state["file_path"], state["course_id"])
            state["ingestion_result"] = result
    except Exception as e:
        state["error"] = f"Ingestion failed: {e}"
    return state


def generate_quiz_node(state: QuizifyState) -> QuizifyState:
    content_agent, *_ = _agents()
    try:
        quiz = content_agent.generate_quiz(
            course_id=state["course_id"],
            topic=state["topic"],
            difficulty=state.get("difficulty", "medium"),
            bloom_level=state.get("bloom_level", "understand"),
            num_questions=state.get("num_questions", 5),
            question_types=state.get("question_types"),
            weak_concepts=state.get("weak_concepts"),
        )
        state["generated_quiz"] = quiz
    except Exception as e:
        state["error"] = f"Quiz generation failed: {e}"
    return state


def evaluate_node(state: QuizifyState) -> QuizifyState:
    _, eval_agent, *_ = _agents()
    try:
        questions = state["generated_quiz"]["questions"]
        responses = state.get("student_responses", [])
        result = eval_agent.evaluate_quiz(questions, responses)
        state["evaluation_result"] = result
    except Exception as e:
        state["error"] = f"Evaluation failed: {e}"
    return state


def adapt_node(state: QuizifyState) -> QuizifyState:
    _, _, adaptive_agent, _ = _agents()
    try:
        evaluation = state["evaluation_result"]
        result = adaptive_agent.analyze_for_student(
            student_id=state["student_id"],
            graded_questions=evaluation["graded_questions"],
            accuracy=evaluation["accuracy"],
            current_difficulty=state.get("difficulty", "medium"),
            existing_topic_mastery=state.get("existing_topic_mastery", {}),
        )
        state["adaptive_result"] = result
    except Exception as e:
        state["error"] = f"Adaptive analysis failed: {e}"
    return state


def analytics_node(state: QuizifyState) -> QuizifyState:
    _, _, _, analytics_agent = _agents()
    try:
        adaptive = state["adaptive_result"]
        evaluation = state["evaluation_result"]
        result = analytics_agent.record_attempt(
            student_id=state["student_id"],
            quiz_id=state.get("quiz_id", 0),
            topic=state["topic"],
            accuracy=evaluation["accuracy"],
            topic_mastery=adaptive["topic_mastery"],
            weak_topics=adaptive["weak_topics"],
            strong_topics=adaptive["strong_topics"],
        )
        state["analytics_result"] = result
    except Exception as e:
        state["error"] = f"Analytics update failed: {e}"
    return state


def _route_on_error(state: QuizifyState) -> str:
    """
    Conditional-edge router used after every node: if the node we just
    ran set state['error'], stop the graph immediately instead of letting
    downstream nodes execute against incomplete/stale state (e.g. running
    generate_quiz_node after ingest_node failed, which would either crash
    on a missing 'ingestion_result' or silently generate an ungrounded
    quiz without telling the caller ingestion failed).
    """
    return "error" if state.get("error") else "continue"


# ----------------------------------------------------------------------
# Graph construction
# ----------------------------------------------------------------------
def build_generation_graph():
    """Upload -> embed -> generate quiz. Stops here for human input (student answers).
    Short-circuits to END if ingestion fails, so a bad upload can't silently
    fall through into quiz generation on incomplete state."""
    graph = StateGraph(QuizifyState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("generate_quiz", generate_quiz_node)
    graph.set_entry_point("ingest")
    graph.add_conditional_edges("ingest", _route_on_error, {"error": END, "continue": "generate_quiz"})
    graph.add_edge("generate_quiz", END)
    return graph.compile()


def build_evaluation_graph():
    """Evaluate -> detect gaps/adapt -> update analytics. The adaptive learning loop's back half.
    Short-circuits to END as soon as any stage fails, so e.g. a failed
    evaluation can't cascade into adapt_node crashing on a missing
    evaluation_result, and a failed adapt step can't cascade into
    analytics_node recording wrong/partial data."""
    graph = StateGraph(QuizifyState)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("adapt", adapt_node)
    graph.add_node("update_analytics", analytics_node)
    graph.set_entry_point("evaluate")
    graph.add_conditional_edges("evaluate", _route_on_error, {"error": END, "continue": "adapt"})
    graph.add_conditional_edges("adapt", _route_on_error, {"error": END, "continue": "update_analytics"})
    graph.add_edge("update_analytics", END)
    return graph.compile()


_generation_graph = None
_evaluation_graph = None


def run_quiz_generation(state: QuizifyState) -> QuizifyState:
    """Entry point 1: ingest material (if provided) and generate a quiz."""
    global _generation_graph
    if _generation_graph is None:
        _generation_graph = build_generation_graph()
    return _generation_graph.invoke(state)


def run_evaluation_cycle(state: QuizifyState) -> QuizifyState:
    """Entry point 2: evaluate student responses, adapt, update analytics — the full adaptive loop."""
    global _evaluation_graph
    if _evaluation_graph is None:
        _evaluation_graph = build_evaluation_graph()
    return _evaluation_graph.invoke(state)
