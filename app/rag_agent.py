"""
RAG Agent: retrieves role-scoped document chunks from ChromaDB,
then generates a grounded answer using Groq (free LLM API).
"""

import os
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
from app.rbac import get_allowed_namespaces

load_dotenv()

CHROMA_PATH = "./chroma_db"
TOP_K = 5

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
embedder = SentenceTransformer("all-MiniLM-L6-v2")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def retrieve_documents(query: str, role: str) -> tuple[list[str], list[str]]:
    """
    Retrieve top-K relevant chunks from all namespaces the role is allowed to access.
    Returns (chunks, namespaces_accessed).
    """
    allowed = get_allowed_namespaces(role)
    if not allowed:
        return [], []

    query_embedding = embedder.encode(query).tolist()
    all_chunks = []
    namespaces_used = []

    for namespace in allowed:
        try:
            collection = chroma_client.get_collection(name=namespace)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(TOP_K, collection.count()),
                include=["documents", "distances"],
            )
            docs = results.get("documents", [[]])[0]
            if docs:
                all_chunks.extend(docs)
                namespaces_used.append(namespace)
        except Exception:
            continue

    # De-duplicate chunks
    seen = set()
    unique_chunks = []
    for c in all_chunks:
        if c not in seen:
            seen.add(c)
            unique_chunks.append(c)

    return unique_chunks[:TOP_K * 2], namespaces_used


def generate_answer(query: str, context_chunks: list[str], role: str) -> str:
    """Generate a grounded, role-aware answer using Groq LLM."""
    if not context_chunks:
        return (
            "I could not find relevant information in the documents you have access to. "
            "Please refine your query or contact your administrator if you believe you "
            "should have access to this information."
        )

    context = "\n\n---\n\n".join(context_chunks)

    system_prompt = f"""You are a secure enterprise AI assistant for Emerson.
You ONLY answer based on the provided document context.
The current user has the role: '{role}'.
Do NOT reveal information about documents outside the user's permitted namespaces.
Do NOT make up information not present in the context.
If the context does not contain the answer, say so clearly.
Always be factual, concise, and professional."""

    user_message = f"""Context from enterprise documents:
{context}

User question: {query}

Answer based ONLY on the context above:"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def run_rag(query: str, role: str) -> tuple[str, list[str]]:
    """Full RAG pipeline. Returns (answer, namespaces_accessed)."""
    chunks, namespaces = retrieve_documents(query, role)
    answer = generate_answer(query, chunks, role)
    return answer, namespaces
