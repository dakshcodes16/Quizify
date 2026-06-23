"""
Pure-Python / numpy vector store for the RAG pipeline — no ChromaDB,
no compiled extensions, no native build step. Drop-in replacement with
the exact same public API as the original ChromaDB-backed version, so
nothing in agents/ or frontend/ needs to change.

Why this exists: ChromaDB's transitive dependency chain (chroma-hnswlib,
onnxruntime) requires a C++ compiler to build from source on many
Windows/Python combinations, which isn't available in every environment
(corporate machines, locked-down setups, brand-new Python releases
without prebuilt wheels yet). This implementation has zero compiled
dependencies — just numpy, which always ships precompiled wheels.

Trade-off: search uses brute-force cosine similarity instead of an
HNSW approximate-nearest-neighbor index. This is irrelevant at this
project's scale (hundreds to low-thousands of chunks per course) and
only matters if you're indexing millions of vectors.

Stores three kinds of vectors, persisted as JSON on disk:
  - course_content : chunked text from uploaded PDFs/DOCX, used to
                      ground quiz generation (RAG)
  - concepts        : extracted concept/topic summaries, used for
                      duplicate-question prevention & topic search
  - student_context : per-student weak-topic / mistake summaries, used
                       to bias future quiz generation toward gaps

Uses a local, dependency-free hashed n-gram embedding (no network call,
no model download) so the vector store works immediately, even before
a Gemini key is configured.
"""
import sys
import json
import hashlib
import math
from pathlib import Path
from typing import List, Dict, Optional
import uuid

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import settings

import numpy as np

EMBED_DIM = 384


def _embed(text: str) -> List[float]:
    """
    Deterministic, dependency-free text embedding using hashed
    unigrams + bigrams (a lightweight bag-of-words style vector).
    No network call, no model download, no compiled extensions.
    """
    vec = np.zeros(EMBED_DIM, dtype=np.float64)
    tokens = text.lower().split()
    grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    for gram in grams:
        h = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
        idx = h % EMBED_DIM
        sign = 1.0 if (h // EMBED_DIM) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def _cosine_distance(a: List[float], b: List[float]) -> float:
    """Returns 0.0 for identical vectors, up to 2.0 for opposite vectors
    (matches the rough scale ChromaDB's cosine distance uses)."""
    a_arr, b_arr = np.array(a), np.array(b)
    similarity = float(np.dot(a_arr, b_arr))
    return 1.0 - similarity


class _DeferredSave:
    """Context manager backing _Collection.batch_writes(). Supports nesting
    (re-entrant) so a method using batch_writes() internally still works
    correctly when called from another batch_writes() block."""

    def __init__(self, collection: "_Collection"):
        self.collection = collection
        self._was_already_deferring = False

    def __enter__(self):
        self._was_already_deferring = self.collection._defer_save
        self.collection._defer_save = True
        return self.collection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._was_already_deferring:
            self.collection._defer_save = False
            if self.collection._dirty:
                self.collection._dirty = False
                # write once, regardless of how many add()/upsert() calls
                # happened inside the block
                with open(self.collection.path, "w", encoding="utf-8") as f:
                    json.dump(self.collection._records, f)
        return False


class _Collection:
    """A single named collection of (id, document, embedding, metadata) records,
    persisted to a JSON file. Mirrors the small subset of Chroma's collection
    API that this project actually uses."""

    def __init__(self, persist_dir: str, name: str):
        self.path = Path(persist_dir) / f"{name}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: Dict[str, Dict] = {}
        self._defer_save = False
        self._dirty = False
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._records = json.load(f)
            except Exception:
                self._records = {}

    def batch_writes(self):
        """
        Context manager: defers the on-disk JSON rewrite until the block
        exits instead of rewriting the whole file after every individual
        add()/upsert() call. Several call sites (notably duplicate-question
        filtering, which calls add_concept() once per generated question)
        previously triggered one full-file rewrite per record -- O(n) writes
        of an O(n)-sized file, i.e. O(n^2) total I/O for an n-question quiz.
        Safe to nest; only the outermost block actually flushes.
        """
        return _DeferredSave(self)

    def _save(self):
        if self._defer_save:
            self._dirty = True
            return
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._records, f)

    def add(self, documents: List[str], ids: List[str], metadatas: List[Dict]):
        for doc, _id, meta in zip(documents, ids, metadatas):
            self._records[_id] = {
                "document": doc,
                "embedding": _embed(doc),
                "metadata": meta,
            }
        self._save()

    def upsert(self, documents: List[str], ids: List[str], metadatas: List[Dict]):
        # identical to add() here since both just overwrite by id
        self.add(documents, ids, metadatas)

    def get(self, ids: List[str]) -> Dict:
        documents = []
        for _id in ids:
            record = self._records.get(_id)
            if record:
                documents.append(record["document"])
        return {"documents": documents}

    def query(self, query_texts: List[str], n_results: int = 4, where: Optional[Dict] = None) -> Dict:
        query_vec = _embed(query_texts[0])

        candidates = list(self._records.items())
        if where:
            candidates = [
                (rid, r) for rid, r in candidates
                if all(r["metadata"].get(k) == v for k, v in where.items())
            ]

        scored = [
            (rid, r, _cosine_distance(query_vec, r["embedding"]))
            for rid, r in candidates
        ]
        scored.sort(key=lambda x: x[2])  # lower distance = more similar
        top = scored[:n_results]

        return {
            "documents": [[r["document"] for _, r, _ in top]],
            "distances": [[dist for _, _, dist in top]],
        }


class VectorStore:
    def __init__(self):
        persist_dir = settings.chroma_persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self.course_content = _Collection(persist_dir, "course_content")
        self.concepts = _Collection(persist_dir, "concepts")
        self.student_context = _Collection(persist_dir, "student_context")

    def batch_concept_writes(self):
        """Defers concept-collection disk writes until the with-block exits.
        Use when adding many concepts/questions in a loop (e.g. duplicate
        filtering during quiz generation) to avoid one full-file rewrite
        per item."""
        return self.concepts.batch_writes()

    # ---------- Course content (for RAG question generation) ----------
    def add_course_chunks(self, course_id: int, chunks: List[str]) -> None:
        if not chunks:
            return
        ids = [f"course_{course_id}_{uuid.uuid4().hex[:8]}" for _ in chunks]
        metadatas = [{"course_id": str(course_id), "chunk_index": i} for i in range(len(chunks))]
        self.course_content.add(documents=chunks, ids=ids, metadatas=metadatas)

    def query_course_content(self, course_id: int, query: str, n_results: int = 4) -> List[str]:
        try:
            results = self.course_content.query(
                query_texts=[query],
                n_results=n_results,
                where={"course_id": str(course_id)},
            )
            return results.get("documents", [[]])[0]
        except Exception:
            return []

    # ---------- Concepts (duplicate prevention) ----------
    def add_concept(self, course_id: int, concept_text: str, metadata: Optional[Dict] = None) -> None:
        meta = {"course_id": str(course_id)}
        if metadata:
            meta.update(metadata)
        self.concepts.add(
            documents=[concept_text],
            ids=[f"concept_{uuid.uuid4().hex[:10]}"],
            metadatas=[meta],
        )

    def find_similar_concepts(self, course_id: int, concept_text: str, n_results: int = 3) -> List[Dict]:
        try:
            results = self.concepts.query(
                query_texts=[concept_text],
                n_results=n_results,
                where={"course_id": str(course_id)},
            )
            docs = results.get("documents", [[]])[0]
            dists = results.get("distances", [[]])[0]
            return [{"text": d, "distance": dist} for d, dist in zip(docs, dists)]
        except Exception:
            return []

    def is_duplicate_question(self, course_id: int, question_text: str, threshold: float = 0.15) -> bool:
        """Lower distance = more similar. Below threshold => treat as duplicate."""
        similar = self.find_similar_concepts(course_id, question_text, n_results=1)
        if not similar:
            return False
        return similar[0]["distance"] < threshold

    # ---------- Student context (adaptive personalization) ----------
    def upsert_student_context(self, student_id: int, summary: str) -> None:
        self.student_context.upsert(
            documents=[summary],
            ids=[f"student_{student_id}"],
            metadatas=[{"student_id": str(student_id)}],
        )

    def get_student_context(self, student_id: int) -> Optional[str]:
        try:
            result = self.student_context.get(ids=[f"student_{student_id}"])
            docs = result.get("documents", [])
            return docs[0] if docs else None
        except Exception:
            return None


_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Singleton accessor so we don't reload the JSON files repeatedly."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
