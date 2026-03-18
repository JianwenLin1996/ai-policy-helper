import os, re, hashlib
from typing import List, Dict, Tuple
from .settings import settings

def _read_text_file(path: str) -> str:
    """Read a text file as UTF-8, ignoring decode errors."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def _md_sections(text: str) -> List[Tuple[str, str]]:
    """Split Markdown text into (section_title, section_text) pairs."""
    # Very simple section splitter by Markdown headings
    parts = re.split(r"\n(?=#+\s)", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        lines = p.splitlines()
        title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else "Body"
        out.append((title, p))
    return out or [("Body", text)]

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Chunk text into overlapping token windows."""
    tokens = text.split()
    chunks = []
    i = 0
    while i < len(tokens):
        chunk = tokens[i:i+chunk_size]
        chunks.append(" ".join(chunk))
        if i + chunk_size >= len(tokens): break
        i += chunk_size - overlap
    return chunks

def load_documents(data_dir: str) -> List[Dict]:
    """Load .md and .txt documents from a directory into sectioned dicts."""
    docs = []
    # use os.scandir for more efficient directory listing and to avoid loading non-file entries
    with os.scandir(data_dir) as it:
        entries = sorted(
            (e for e in it if e.is_file() and e.name.lower().endswith((".md", ".txt"))),
            key=lambda e: e.name
        )
    for entry in entries:
        text = _read_text_file(entry.path)
        # avoid repeated dict lookups
        title = entry.name
        append = docs.append
        for section, body in _md_sections(text):
            append({
                "title": title,
                "section": section,
                "text": body
            })
    return docs

def doc_hash(text: str) -> str:
    """Return a stable SHA-256 hash for text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
