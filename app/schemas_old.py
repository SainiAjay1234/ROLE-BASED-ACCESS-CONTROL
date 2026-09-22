from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class QueryRequest(BaseModel):
    query: str
    token: str


class QueryResponse(BaseModel):
    answer: str
    response_type: str          # "rag", "sql", "blocked", "error"
    namespaces_accessed: list[str] = []
    role: str
    username: str