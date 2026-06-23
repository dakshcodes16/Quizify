"""
Document parsing: extract raw text from PDF/DOCX/TXT uploads and
split it into overlapping chunks suitable for embedding + RAG.
"""
from pathlib import Path
from typing import List
from pypdf import PdfReader
from docx import Document as DocxDocument


def extract_text(file_path: str) -> str:
    """Extract raw text from a PDF, DOCX, or plain text file."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(file_path)
    elif suffix == ".docx":
        return _extract_docx(file_path)
    elif suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def _extract_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n\n".join(text_parts)


def _extract_docx(file_path: str) -> str:
    doc = DocxDocument(file_path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
    """
    Split text into overlapping chunks by character count, breaking on
    paragraph/sentence boundaries where possible to keep chunks coherent.
    """
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        # try to break on a paragraph or sentence boundary
        if end < text_len:
            for sep in ["\n\n", ". ", "\n"]:
                last_sep = text.rfind(sep, start, end)
                if last_sep > start + chunk_size // 2:
                    end = last_sep + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if end - overlap > start else end

    return chunks
