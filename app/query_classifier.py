"""
Decides whether a query should go to the SQL agent or the RAG agent.
Uses simple keyword heuristics + optional LLM classification.
"""

SQL_KEYWORDS = [
    "how many", "count", "total", "average", "sum", "list all",
    "show me all", "table", "rows", "records", "employees in",
    "employees with", "salary", "headcount",
]


def classify_query(query: str) -> str:
    """Returns 'sql' or 'rag'."""
    q = query.lower()
    for kw in SQL_KEYWORDS:
        if kw in q:
            return "sql"
    return "rag"