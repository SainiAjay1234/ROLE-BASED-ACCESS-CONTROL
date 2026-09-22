"""
upload_ingestion.py
Handles runtime PDF uploads from the Streamlit UI.
Ingests the uploaded file into ChromaDB under a role-scoped collection name,
and dynamically adds that collection to the uploader's role permissions.
"""

import os
import re
import tempfile
from pathlib import Path

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from app.rbac import ROLE_PERMISSIONS

CHROMA_PATH = "./chroma_db"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

_chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
_embedder = SentenceTransformer("all-MiniLM-L6-v2")


def _sanitize_name(name: str) -> str:
    """Convert filename to a valid ChromaDB collection name."""
    name = Path(name).stem                      # remove extension
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9_-]", "_", name)   # replace special chars
    name = re.sub(r"_+", "_", name)             # collapse repeated underscores
    return name[:60]                            # ChromaDB max 63 chars


def _extract_text(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        reader = PdfReader(tmp_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    finally:
        os.unlink(tmp_path)


def _chunk_text(text: str) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c.strip() for c in chunks if c.strip()]


def ingest_uploaded_pdf(
    pdf_bytes: bytes,
    filename: str,
    target_role: str,
) -> dict:
    """
    Ingest a user-uploaded PDF into ChromaDB and register it under target_role.

    Returns a dict with keys: collection_name, chunks_added, role
    """
    collection_name = _sanitize_name(filename)

    # Extract + chunk
    text = _extract_text(pdf_bytes)
    if not text.strip():
        raise ValueError("Could not extract any text from the uploaded PDF.")

    chunks = _chunk_text(text)
    if not chunks:
        raise ValueError("Document produced no indexable chunks.")

    # Upsert into ChromaDB (allows re-upload of same file)
    collection = _chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    embeddings = _embedder.encode(chunks).tolist()
    ids = [f"{collection_name}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"source": collection_name, "chunk_index": i, "uploaded_by_role": target_role}
        for i in range(len(chunks))
    ]

    # Delete existing chunks first (clean re-ingest)
    try:
        collection.delete(ids=ids)
    except Exception:
        pass

    collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)

    # Dynamically grant the target role access to this new collection
    role_key = target_role.lower()
    if role_key in ROLE_PERMISSIONS:
        if collection_name not in ROLE_PERMISSIONS[role_key]:
            ROLE_PERMISSIONS[role_key].append(collection_name)
    else:
        ROLE_PERMISSIONS[role_key] = [collection_name]

    # Admin always gets access too
    if "admin" in ROLE_PERMISSIONS:
        if collection_name not in ROLE_PERMISSIONS["admin"]:
            ROLE_PERMISSIONS["admin"].append(collection_name)

    return {
        "collection_name": collection_name,
        "chunks_added": len(chunks),
        "role": target_role,
    }


def list_uploaded_collections() -> list[dict]:
    """Return all collections in ChromaDB with their metadata."""
    collections = _chroma_client.list_collections()
    result = []
    for col in collections:
        result.append({
            "name": col.name,
            "count": col.count(),
        })
    return sorted(result, key=lambda x: x["name"])
