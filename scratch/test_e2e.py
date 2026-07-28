import sys
from pathlib import Path

# Add quizify directory to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent / "quizify"))

from database.db import init_db, get_db_session
from database.models import User, Course, Quiz, Assignment, Response, Analytics
from database.quiz_repo import save_generated_quiz, access_quiz_by_code
from agents.content_quiz_agent import ContentQuizAgent
from backend.orchestration import run_evaluation_cycle

def run_test():
    init_db()
    print("Database initialized.")

    # 1. Create a teacher
    with get_db_session() as db:
        teacher = db.query(User).filter_by(email="teacher@test.com").first()
        if not teacher:
            teacher = User(
                name="Test Teacher",
                email="teacher@test.com",
                password_hash="hashed_password",
                role="teacher"
            )
            db.add(teacher)
            db.flush()
        teacher_id = teacher.id
        print(f"Teacher created/found: ID {teacher_id}")

        # 2. Create a course
        course = Course(
            title="E2E Cell Biology",
            uploaded_material="sample_notes.txt",
            owner_id=teacher_id
        )
        db.add(course)
        db.flush()
        course_id = course.id
        print(f"Course created: ID {course_id}")

    # 3. Ingest sample notes
    notes_path = Path(__file__).resolve().parent.parent / "sample_notes.txt"
    print(f"Reading notes from {notes_path}")
    
    agent = ContentQuizAgent()
    ingest_result = agent.ingest_material(str(notes_path), course_id)
    print(f"Extracted {len(ingest_result['concepts'])} topics.")

    with get_db_session() as db:
        course = db.query(Course).filter_by(id=course_id).first()
        course.extracted_concepts = ingest_result["concepts"]
        db.add(course)
        db.flush()

    # 4. Generate a quiz
    print("Generating quiz...")
    topic = ingest_result["concepts"][0]["topic"]
    quiz = agent.generate_quiz(
        course_id=course_id,
        topic=topic,
        difficulty="medium",
        bloom_level="understand",
        num_questions=3,
        question_types=["mcq"]
    )
    
    quiz_id = save_generated_quiz(course_id, quiz)
    print(f"Quiz persisted: ID {quiz_id}, Code {quiz['code']}")

    # 5. Access quiz by code (simulating student join)
    print(f"Joining quiz using code {quiz['code']} as student 'Jane Doe'...")
    quiz_dict, student, err = access_quiz_by_code(quiz['code'], "Jane Doe", "ROLL-123")
    if err:
        print(f"Error accessing quiz: {err}")
        return
    print(f"Guest student joined: {student.name} (ID {student.id})")

    # 6. Simulate quiz responses (answering all questions correctly)
    student_responses = []
    for i, q in enumerate(quiz_dict["questions"]):
        student_responses.append({
            "question_index": i,
            "response": q["answer"]
        })
    
    with get_db_session() as db:
        analytics = db.query(Analytics).filter_by(student_id=student.id).first()
        existing_mastery = analytics.topic_mastery if analytics else {}

    state = {
        "student_id": student.id,
        "topic": quiz_dict["topic"],
        "difficulty": quiz_dict["difficulty"],
        "quiz_id": quiz_id,
        "existing_topic_mastery": existing_mastery,
        "generated_quiz": quiz_dict,
        "student_responses": student_responses,
    }

    # Run the evaluation graph
    print("Running evaluation cycle...")
    result = run_evaluation_cycle(state)
    if "error" in result and result["error"]:
        print(f"Evaluation cycle failed: {result['error']}")
        return
    
    eval_res = result["evaluation_result"]
    print(f"Grading accuracy: {eval_res['accuracy']}%")
    print(f"Total score: {eval_res['total_score']}/{eval_res['max_score']}")
    
    assert eval_res['accuracy'] == 100.0, f"Expected 100% accuracy, got {eval_res['accuracy']}%"
    assert eval_res['total_score'] == eval_res['max_score'], f"Expected total score {eval_res['max_score']}, got {eval_res['total_score']}"
    
    # Save student responses and mark completed
    from database.quiz_repo import save_responses, mark_assignment_completed
    save_responses(student.id, quiz_id, eval_res["graded_questions"])
    mark_assignment_completed(quiz_id, student.id)
    print("Responses saved and assignment marked completed successfully!")

if __name__ == "__main__":
    run_test()
