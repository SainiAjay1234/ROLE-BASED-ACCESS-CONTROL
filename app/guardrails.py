"""
Guardrails: detect prompt injection, blocked keywords, and out-of-scope queries.
"""

import re

INJECTION_PATTERNS = [
    r"ignore.*(instructions|rules|guidelines)",
    r"disregard.*(system prompt|instructions|rules)",
    r"you are now",
    r"act as (a |an )?(different|new|unrestricted)",
    r"jailbreak",
    r"DAN mode",
    r"forget your (rules|guidelines|instructions)",
    r"pretend you",
    r"bypass.*(filter|security|restriction)",
    r"reveal all",
    r"dump.*(all|data|everything)",
]

BLOCKED_KEYWORDS = [
    "password", "credentials", "hack", "exploit",
    "dump all data", "show all users", "drop table",
    "delete all", "system prompt", "master key",
]


def check_prompt_injection(query: str) -> tuple[bool, str]:
    """Returns (is_safe, reason)."""
    q = query.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, q):
            return False, f"Prompt injection attempt detected: pattern '{pattern}'"
    return True, ""


def check_blocked_keywords(query: str) -> tuple[bool, str]:
    q = query.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in q:
            return False, f"Blocked keyword detected: '{kw}'"
    return True, ""


def validate_query(query: str) -> tuple[bool, str]:
    """Run all guardrail checks. Returns (is_safe, reason)."""
    safe, reason = check_prompt_injection(query)
    if not safe:
        return False, reason
    safe, reason = check_blocked_keywords(query)
    if not safe:
        return False, reason
    if len(query.strip()) < 3:
        return False, "Query too short."
    if len(query) > 2000:
        return False, "Query too long (max 2000 characters)."
    return True, ""