from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import LoginRequest, TokenResponse, QueryRequest, QueryResponse
from app.auth import authenticate_user, create_access_token, decode_token
from app.guardrails import validate_query
from app.query_classifier import classify_query
from app.rag_agent import run_rag
from app.sql_agent import run_sql_agent
from app.upload_ingestion import ingest_uploaded_pdf, list_uploaded_collections
from app import audit

app = FastAPI(title="Emerson Secure RAG API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


# ── Auth ───────────────────────────────────────────────────────────────────
@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return TokenResponse(
        access_token=token,
        role=user["role"],
        username=user["username"],
    )


# ── Query ──────────────────────────────────────────────────────────────────
@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    # 1. Verify JWT
    token_data = decode_token(request.token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = token_data.username
    role = token_data.role

    # 2. Guardrails check
    is_safe, reason = validate_query(request.query)
    if not is_safe:
        audit.log_query(username, role, request.query, blocked=True, block_reason=reason)
        return QueryResponse(
            answer=f"🚫 Query blocked: {reason}",
            response_type="blocked",
            role=role,
            username=username,
        )

    # 3. Classify: SQL or RAG?
    query_type = classify_query(request.query)

    if query_type == "sql":
        answer, success = run_sql_agent(request.query, role)
        if success:
            audit.log_query(username, role, request.query, response_type="sql")
            return QueryResponse(
                answer=answer,
                response_type="sql",
                role=role,
                username=username,
            )
        query_type = "rag"

    # 4. RAG pipeline
    answer, namespaces = run_rag(request.query, role)
    audit.log_query(
        username, role, request.query,
        response_type="rag",
        namespaces_accessed=namespaces,
    )
    return QueryResponse(
        answer=answer,
        response_type="rag",
        namespaces_accessed=namespaces,
        role=role,
        username=username,
    )


# ── Document Upload ────────────────────────────────────────────────────────
@app.post("/upload-document")
async def upload_document(
    token: str = Form(...),
    target_role: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload a PDF and ingest it into ChromaDB under the specified role namespace.
    Only admin users can upload documents for any role.
    Non-admin users can only upload documents for their own role.
    """
    # Verify JWT
    token_data = decode_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    uploader_role = token_data.role
    username = token_data.username

    # RBAC: non-admin can only upload to their own role's namespace
    if uploader_role != "admin" and target_role.lower() != uploader_role.lower():
        raise HTTPException(
            status_code=403,
            detail=f"You can only upload documents for your own role ({uploader_role}). "
                   f"Contact admin to upload for other roles."
        )

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Read file
    pdf_bytes = await file.read()
    if len(pdf_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 20MB.")

    try:
        result = ingest_uploaded_pdf(pdf_bytes, file.filename, target_role)
        audit.log_query(
            username, uploader_role,
            f"[UPLOAD] {file.filename} → role:{target_role}",
            response_type="upload",
            namespaces_accessed=[result["collection_name"]],
        )
        return {
            "success": True,
            "message": f"Document '{file.filename}' ingested successfully.",
            "collection_name": result["collection_name"],
            "chunks_added": result["chunks_added"],
            "role_granted": target_role,
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


# ── List Collections ───────────────────────────────────────────────────────
@app.get("/collections")
def get_collections(token: str):
    """Return all indexed document collections (admin only)."""
    token_data = decode_token(token)
    if not token_data or token_data.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return list_uploaded_collections()


# ── Audit Logs ─────────────────────────────────────────────────────────────
@app.get("/admin/audit-logs")
def get_audit_logs(token: str, limit: int = 50):
    token_data = decode_token(token)
    if not token_data or token_data.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return audit.get_audit_logs(limit=limit)
