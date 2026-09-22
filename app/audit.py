"""
Audit Logger: records every query, user, role, response type, and timestamp.
Uses SQLite for lightweight persistence.
"""

import sqlite3
from datetime import datetime
from datetime import datetime, timezone

DB_PATH = "./audit.db"


def init_audit_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            username    TEXT NOT NULL,
            role        TEXT NOT NULL,
            query       TEXT NOT NULL,
            response_type TEXT,
            namespaces_accessed TEXT,
            blocked     INTEGER DEFAULT 0,
            block_reason TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_query(
    username: str,
    role: str,
    query: str,
    response_type: str = "rag",
    namespaces_accessed: list[str] | None = None,
    blocked: bool = False,
    block_reason: str = "",
):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO audit_log
           (timestamp, username, role, query, response_type, namespaces_accessed, blocked, block_reason)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now(timezone.utc).isoformat(),
            username,
            role,
            query,
            response_type,
            ",".join(namespaces_accessed or []),
            int(blocked),
            block_reason,
        ),
    )
    conn.commit()
    conn.close()


def get_audit_logs(limit: int = 100) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_audit_db()