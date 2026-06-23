# 🧠 Quizify — Multi-Agent Adaptive Learning Platform

Quizify turns course material into adaptive, AI-graded quizzes using four
cooperating agents orchestrated with **LangGraph**, grounded in your content
via **RAG** (a built-in pure-Python vector store), and powered by **Groq (llama-3.3-70b-versatile)**.

```
Teacher uploads PDF/notes  ->  Agent 1 extracts concepts + generates quiz
        |
Student takes quiz  ->  Agent 2 evaluates (objective + semantic grading)
        |
Agent 3 detects learning gaps  ->  decides: advance or remediate
        |
Agent 4 updates analytics, streaks, badges  ->  Faculty dashboard
        |
        (loop: next quiz is biased toward weak concepts)
```

---

## Architecture

| Layer | Tech |
|---|---|
| UI | Streamlit + custom CSS (glassmorphism, purple/blue gradients) + Plotly |
| Auth API | FastAPI + JWT (`python-jose`) + bcrypt (`passlib`) |
| Orchestration | LangGraph (`StateGraph`) - shared state across all 4 agents |
| LLM | Groq (`llama-3.3-70b-versatile`), JSON-mode for structured output -- 14,400 free requests/day |
| Vector DB | Built-in pure-Python/numpy store, JSON-persisted (zero compiled dependencies) |
| Relational DB | SQLite via SQLAlchemy (swap to Postgres by changing `DATABASE_URL`) |
| Doc parsing | `pypdf`, `python-docx` |
| Reports | `reportlab` (PDF export) |

**How Streamlit and FastAPI relate:** FastAPI owns authentication (JWT
issuance/validation, bcrypt password hashing) as a real HTTP service.
Streamlit calls it over HTTP for login/register, then calls the
agents/orchestration layer **in-process** for the core adaptive-learning
loop (quiz generation, evaluation, analytics) - this keeps the learning
loop fast with one fewer network hop, while auth still runs as a genuine,
independently-testable API. If FastAPI isn't running (e.g. on Streamlit
Community Cloud, which only runs one process), the UI transparently falls
back to in-process auth (`frontend/components/auth_fallback.py`) using the
identical hashing/JWT logic, so the app still works standalone.

### Project structure

```
quizify/
├── agents/
│   ├── content_quiz_agent.py     # Agent 1: ingestion, RAG, quiz generation
│   ├── evaluation_agent.py       # Agent 2: grading, semantic eval, feedback
│   ├── adaptive_agent.py         # Agent 3: gap detection, mastery, decisions
│   └── analytics_agent.py        # Agent 4: streaks, badges, dashboards, PDF
├── backend/
│   └── orchestration.py          # LangGraph wiring (shared state graph)
├── api/
│   ├── main.py                   # FastAPI app
│   ├── auth_routes.py            # /auth/register, /auth/login, /auth/me
│   ├── data_routes.py            # /api/courses, /api/faculty/dashboard, ...
│   └── schemas.py                # Pydantic request/response models
├── database/
│   ├── models.py                 # SQLAlchemy models (Users, Courses, ...)
│   ├── db.py                     # Engine/session management
│   └── quiz_repo.py               # Persists generated quizzes + assignments (see "Quiz assignment" below)
├── vectorstore/
│   └── chroma_client.py          # Pure-Python vector store (RAG, dedup, student context)
├── frontend/
│   ├── pages/                    # One module per UI page
│   └── components/                # Reusable UI bits, auth client, styles
├── utils/
│   ├── gemini_client.py          # Gemini wrapper (text + JSON mode)
│   ├── document_parser.py        # PDF/DOCX extraction + chunking
│   └── auth_utils.py             # JWT + bcrypt helpers
├── app.py                        # Streamlit entrypoint
├── config.py                     # Centralized settings (pydantic-settings)
├── requirements.txt
├── Dockerfile / docker-compose.yml
└── render.yaml / railway.json / Procfile
```

---

## Setup

### 1. Clone and install

```bash
cd quizify
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=your_key_here        # https://console.groq.com
GROQ_MODEL=llama-3.3-70b-versatile
JWT_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
```

### 3. Run

You need **two processes** for the full experience (auth API + UI):

```bash
# Terminal 1 - FastAPI auth/data service
uvicorn api.main:app --reload --port 8000

# Terminal 2 - Streamlit UI
streamlit run app.py
```

Or with Docker:

```bash
docker compose up --build
```

Open **http://localhost:8501**. The database and vector store are created
automatically on first run (SQLite file + local Chroma persistence dir).

> **Streamlit-only mode:** if you skip Terminal 1, the app still works -
> auth automatically falls back to in-process mode. This is what happens
> on Streamlit Community Cloud, which only runs one process.

---

## How each agent works

### Agent 1 - Content & Quiz Generation
Extracts text from PDF/DOCX, chunks it, embeds it into the local vector store. Calls
Gemini (JSON mode) to extract structured topics/concepts/objectives, then
generates quizzes **grounded in retrieved chunks** (RAG) with Bloom's
taxonomy tagging, balanced difficulty, and AI-written distractors.
Duplicate questions are filtered by checking semantic similarity against
previously generated questions stored in the vector store.

### Agent 2 - Evaluation & Feedback
MCQ/True-False are graded deterministically. Short answers are graded by
Gemini with **partial credit** (0.0-1.0) based on semantic correctness, not
exact wording. Generates a non-revealing hint for any missed question and
an overall encouraging-but-honest feedback summary for the attempt.

### Agent 3 - Learning Gap & Adaptive
Aggregates per-concept scores from the graded attempt, blends them with
historical mastery (60% new / 40% prior), and applies the spec's decision
rule: **>80% -> advance to harder material, <80% -> remediate weak
concepts**. Outputs weak/strong topics, next difficulty, and recommended
topics, and persists a compact student-context summary to the vector store
so Agent 1 can bias future quiz generation toward known gaps.

### Agent 4 - Analytics & Progress
Updates mastery score, day-based learning streaks, and quiz history;
awards gamification badges; aggregates class-wide insights (average
mastery, common weak topics, leaderboard, heatmap data) for the faculty
dashboard; exports a PDF progress report via `reportlab`.

### Orchestration (LangGraph)
Two compiled graphs share the same `QuizifyState` TypedDict (the "shared
memory"):
- **Generation graph**: `ingest -> generate_quiz` (stops for human input -
  the student answering the quiz)
- **Evaluation graph**: `evaluate -> adapt -> update_analytics` (the back
  half of the loop, run on submission)

---

## Database schema

SQLAlchemy models in `database/models.py`, matching the spec plus the
extra fields needed to actually run gamification/leaderboards:

`Users(id, name, email, password_hash, role)` ·
`Courses(id, title, uploaded_material, owner_id, extracted_concepts)` ·
`Quizzes(id, course_id, topic, difficulty, bloom_level)` ·
`Questions(id, quiz_id, type, question, options, answer, explanation, concept_tag)` ·
`Assignments(id, quiz_id, student_id, assigned_by_id, assigned_at, due_date, completed)` ·
`Responses(student_id, question_id, response, score, ai_feedback)` ·
`Analytics(student_id, mastery_score, weak_topics, topic_mastery, current_streak, history)` ·
`Badges(student_id, name, icon, description)`

### Quiz assignment

A teacher generating a quiz on the Upload page persists it as real
`Quiz`/`Question` rows immediately (`database/quiz_repo.py`), then can
assign it to specific students or the whole class -- each assignment is
its own row in `Assignments`, so completion is tracked independently per
student. The student-facing Quiz page queries `Assignments` for the
logged-in student directly from the database (not from session state,
which is private per browser session and can't be written to by a
different user's session), shows what's pending, and on submission marks
that student's assignment `completed=True` and writes one `Response` row
per question. A self-practice generator is also available for students
with no pending assignment; it persists identically, just without a
teacher-created `Assignment` row.

Switch to Postgres by installing a driver (`pip install psycopg2-binary`)
and changing `DATABASE_URL` in `.env` to a `postgresql://...` URL --
SQLAlchemy handles the rest, no code changes needed. `init_db()` only
creates an on-disk directory for SQLite URLs, so this is safe to switch
without leaving stray folders behind.

---

## About the vector store

`vectorstore/chroma_client.py` is a pure-Python/numpy implementation (no
ChromaDB, no compiled extensions, no native build step). It was built this
way deliberately: ChromaDB's dependency chain (`chroma-hnswlib`,
`onnxruntime`) requires a C++ compiler to build from source on many
Windows/Python combinations, which isn't available in every environment.
This implementation needs only numpy (which always ships precompiled
wheels) and installs instantly anywhere.

It uses brute-force cosine similarity instead of an approximate-nearest-
neighbor index, which is irrelevant at this project's scale (hundreds to
low-thousands of chunks per course) and a hashed n-gram embedding instead
of a trained sentence-embedding model, so retrieval is directionally
useful but less semantically sharp than a real embedding model. All data
is persisted as JSON files under `vectorstore/chroma_data/`. For
production-grade semantic search, swap in `sentence-transformers` (for
better embeddings) and/or a dedicated vector DB (Chroma, Qdrant, pgvector)
behind the same `VectorStore` interface — every method this project calls
(`add_course_chunks`, `query_course_content`, `is_duplicate_question`,
etc.) is documented in that file and easy to re-implement against a
different backend without touching any agent code.

## Deployment

### Docker (recommended for self-hosting)
```bash
docker compose up --build
```
Runs `api` (port 8000) and `ui` (port 8501) as separate services sharing a
persistent volume for the DB and vector store.

### Render
Push to a connected repo, then **New -> Blueprint** using `render.yaml`
(defines `quizify-api` and `quizify-ui` as two web services). Set
`GROQ_API_KEY` as a secret in the dashboard.

### Railway
`railway up` - uses `railway.json`, which runs `docker-entrypoint.sh`
(starts both FastAPI and Streamlit in one container). Set environment
variables in the Railway dashboard.

### Streamlit Community Cloud
Deploy `app.py` directly. Only the UI process runs, so auth automatically
uses the in-process fallback (no separate FastAPI deployment needed). Set
`GROQ_API_KEY` and `JWT_SECRET_KEY` as Streamlit secrets.

---

## Notes on scope

This is a complete, working reference implementation of the full agent
architecture and adaptive-learning loop described in the spec - every
agent makes real Gemini calls, real RAG retrieval, real grading, and real
DB writes; it isn't mocked. A few items from the spec are intentionally
left as documented extension points rather than fully built out, since
they're orthogonal to the core multi-agent architecture: a chatbot tutor
UI, an in-app leaderboard page (the data/query already exists in
`AnalyticsAgent.get_faculty_dashboard()` - only a dedicated page is
missing), and fine-grained Response-table persistence per question
(currently each attempt's grading detail lives in the evaluation result
and `Analytics.history`, not a row per `Response`). These are
straightforward to add on top of the existing models/agents.

---

## Production hardening changelog

The following real bugs were found by actually running the project
(installing dependencies, executing the smoke test, and rendering every
page with Streamlit's `AppTest` framework) and fixed:

- **Broken card UI across 3 pages** (`teacher_upload`, `quiz_interface`,
  `learning_gap_dashboard`): a hand-rolled `st.markdown('<div class="glass-card">')`
  ... `st.markdown('</div>')` pattern doesn't actually nest Streamlit
  widgets inside the div (each `st.markdown()` call is its own isolated
  DOM node), so the cards rendered empty with stray closing tags. Replaced
  with `st.container(border=True)` via the new `card_container()` helper
  in `frontend/components/ui.py`, re-skinned in `styles.py` to keep the
  same glassmorphism look.
- **Noisy bcrypt/passlib error on every login and registration**:
  `passlib==1.7.4` reads `bcrypt.__about__.__version__`, which was removed
  in `bcrypt>=4.1`. Every password hash/verify call threw a
  caught-but-noisy `AttributeError` traceback to stderr. Pinned
  `bcrypt==4.0.1` in `requirements.txt`.
- **Orchestration graph didn't stop on error**: each LangGraph node caught
  its own exceptions into `state["error"]`, but downstream nodes ran
  anyway regardless. Added conditional edges in `backend/orchestration.py`
  so the graph now routes straight to `END` the moment any node fails,
  verified by a test that forces a failure in `evaluate_node` and confirms
  `adapt_node`/`analytics_node` never execute.
- **O(n²) vector store writes during quiz generation**: duplicate-question
  filtering and concept ingestion called `add_concept()` once per item in
  a loop, and every call rewrote the *entire* JSON collection file to
  disk. Added a `batch_writes()` / `batch_concept_writes()` context
  manager so a whole batch (e.g. 10 questions) now does exactly one disk
  write instead of 10, while preserving duplicate-detection against
  earlier items in the same batch.
- **Sequential per-question grading**: `EvaluationAgent.evaluate_quiz` graded
  questions one at a time, and each non-trivial question can trigger up to
  two LLM calls (grading + hint), so a 10-question quiz could mean
  15-20 sequential round-trips. Parallelized with a thread pool
  (`ThreadPoolExecutor`, capped at 6 concurrent calls), verified to
  preserve correct question ordering under concurrency.
- **`init_db()` created a garbage directory for non-SQLite URLs**: deriving
  a filesystem path from `DATABASE_URL` unconditionally meant a Postgres
  connection string like `postgresql://user:pass@host/db` produced a
  literal directory named after the connection string. Now scoped to only
  run for `sqlite://` URLs.
- **Dead/confusing `student_id=0` write** in `AdaptiveAgent.analyze()`: the
  base method wrote a vector-store record under a fake `student_id=0`
  that the caller (`analyze_for_student`) immediately overwrote with the
  real ID. Refactored so `analyze()` is now a pure function with no
  side effects, and `analyze_for_student()` is the single place that
  persists -- under the correct ID, exactly once.
- **Quiz assignment didn't actually work**: quiz generation only ever
  wrote to `st.session_state`, which is private to one browser session --
  a teacher generating a quiz had no way to get it in front of a specific
  student, since there was no shared database row either side could
  reference (`Quiz`/`Question` tables existed but nothing wrote to them).
  Added `database/quiz_repo.py` (a tested persistence layer: save a
  generated quiz as real rows, load it back, assign it to one/many/all
  students via a new `Assignment` table, list a student's pending
  assignments, persist per-question `Response` rows, mark assignments
  completed) and wired it into `teacher_upload.py` (real "Assign quiz"
  UI: pick students or whole class, optional due date) and
  `quiz_interface.py` (student page now queries actual assignments from
  the database instead of reading session state). Verified end-to-end
  with a test that generates, assigns, takes, submits, and grades a quiz
  across two separate simulated browser sessions and confirms the
  assignment is marked complete.
- **`DetachedInstanceError` risk on any ORM object used after its
  `with get_db_session()` block closed**: SQLAlchemy's default
  `expire_on_commit=True` marks every loaded column "expired" on commit,
  so the next access tries to lazily reload from a session that already
  closed. This codebase's standard pattern (query inside a `with` block,
  read the results afterward) collided with that default. Set
  `expire_on_commit=False` in `database/db.py`'s session factory --
  already-loaded columns stay cached on the object after the session
  closes; this does not serve stale data across reruns, since each
  `with get_db_session()` block still opens a fresh session and queries
  current state every time. (Relationship attributes that were *never*
  accessed before the session closed still need to be read inside the
  `with` block, same as always -- audited every call site in this
  codebase and confirmed none currently hit that narrower case.)
