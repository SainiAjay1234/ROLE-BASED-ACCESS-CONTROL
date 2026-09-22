"""
Ingests enterprise PDFs into ChromaDB.
Each document is stored in its own collection (namespace),
which maps directly to the RBAC policy matrix.
Run this script ONCE to index all documents.
"""

import os
from pathlib import Path
import chromadb
from chromadb.config import Settings
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "./chroma_db"
PDF_DIR = "./data/enterprise_pdfs"
CHUNK_SIZE = 500       # characters per chunk
CHUNK_OVERLAP = 100

client = chromadb.PersistentClient(path=CHROMA_PATH)
embedder = SentenceTransformer("all-MiniLM-L6-v2")


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def ingest_pdf(pdf_path: str, collection_name: str):
    print(f"Ingesting: {pdf_path} → collection: {collection_name}")
    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text)

    # Get or create collection
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # Embed + add
    embeddings = embedder.encode(chunks).tolist()
    ids = [f"{collection_name}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": collection_name, "chunk_index": i} for i in range(len(chunks))]

    collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
    print(f"  ✅ {len(chunks)} chunks added to '{collection_name}'")


def ingest_all():
    pdf_dir = Path(PDF_DIR)
    if not pdf_dir.exists():
        print(f"❌ PDF directory not found: {PDF_DIR}")
        return

    for pdf_file in pdf_dir.glob("*.pdf"):
        # Collection name = filename without .pdf extension
        collection_name = pdf_file.stem  # e.g. employee_handbook
        ingest_pdf(str(pdf_file), collection_name)

    print("\n✅ All documents ingested successfully.")


if __name__ == "__main__":
    ingest_all()