import os
from pathlib import Path
import sys

# Define base directories
workspace_dir = Path(__file__).resolve().parent.parent.parent
quizify_dir = workspace_dir / "quizify"

# Target files and directories to remove
targets = [
    # SQLite Database Files
    workspace_dir / "database" / "quizify.db",
    quizify_dir / "database" / "quizify.db",
    
    # Vectorstore JSON Files
    workspace_dir / "vectorstore" / "chroma_data" / "concepts.json",
    workspace_dir / "vectorstore" / "chroma_data" / "course_content.json",
    workspace_dir / "vectorstore" / "chroma_data" / "student_context.json",
    quizify_dir / "vectorstore" / "chroma_data" / "concepts.json",
    quizify_dir / "vectorstore" / "chroma_data" / "course_content.json",
    quizify_dir / "vectorstore" / "chroma_data" / "student_context.json",
]

print("Starting cleanup of Quizify database and vector store data...")

for target in targets:
    if target.exists():
        try:
            target.unlink()
            print(f"Deleted: {target}")
        except Exception as e:
            print(f"Failed to delete {target}: {e}")
    else:
        print(f"File not found (already clean): {target}")

# Try to initialize the database again
sys.path.append(str(quizify_dir))
try:
    from database.db import init_db
    print("Re-initializing SQLite databases...")
    init_db()
    print("Database tables re-created successfully!")
except Exception as e:
    print(f"Note: Could not automatically re-initialize database tables: {e}")
    print("They will be created automatically upon the next launch of the application.")

print("Cleanup complete!")
