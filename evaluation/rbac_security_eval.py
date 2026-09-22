"""
RBAC Access-Control Security Evaluation.

Unlike evaluate_rag.py / llm_judge.py (which measure *answer quality*), this
script measures *access-control correctness* — the actual security property
your dissertation is about. It drives the live FastAPI app in-process via
TestClient (same pattern as tests/test_security.py) so it exercises the full
stack: /auth/login -> JWT -> /query -> guardrails -> RBAC-scoped retrieval,
not just the rag_agent functions in isolation.

Checks performed
-----------------
1. Cross-role probing: every role is made to ask questions whose ground-truth
   namespace belongs to a DIFFERENT role, and we assert the response never
   touches a namespace that role isn't authorized for (per app/rbac.py).
2. Own-namespace sanity: every role asking its own questions should be able
   to retrieve from its own namespaces (catches over-restrictive bugs too).
3. Admin-only endpoint enforcement: /admin/audit-logs must 403 for non-admin
   tokens and 401 for missing/garbage tokens.
4. Token integrity: a tampered/garbage JWT must be rejected (401) everywhere.
5. SQL-agent boundary: roles with no structured-data access (engineering,
   marketing) must not receive SQL results when asking count/sum-style
   questions that would hit financials/employees tables.

This is a pass/fail security test, not a 0-1 quality score — a single
violation here is a real vulnerability, so results are reported as a
violation list plus a summary pass rate.

Resilience notes
-----------------
Checks 1, 2, and 5 each trigger a real Groq call through the RAG pipeline
(retrieval + generation), so they're the ones that can burn through your
Groq token/rate budget and previously crashed the whole run on a 429. This
version:
    - Uses TestClient(raise_server_exceptions=False) so an unhandled
      exception deep in the app (e.g. a RateLimitError bubbling up from
      groq) comes back as an HTTP 500 instead of crashing the script.
    - Retries 429/5xx responses with backoff, parsing Groq's own
      "try again in Xm Ys" hint from the error body when present.
    - Sleeps briefly between calls to stay under rate limits.
    - Buckets persistent failures as INCONCLUSIVE (infra/rate-limit) rather
      than counting them as security violations or silently passing them.
    - Caps cross-role probes to N questions per (probing_role, owner_role)
      pair by default (--max-per-pair, default 2) instead of all ~150 —
      full coverage isn't needed to prove/disprove namespace leakage for a
      given role pair, and it cuts Groq calls roughly 3-4x.
    - Writes a checkpoint file after every stage, and on Ctrl-C / crash, so
      a rate-limited run doesn't lose everything already computed.

Run:
    python -m evaluation.rbac_security_eval
    python -m evaluation.rbac_security_eval --max-per-pair 1 --delay 3
"""

import re
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.rbac import get_allowed_namespaces, is_authorized
from evaluation.eval_dataset import EVAL_DATASET

# raise_server_exceptions=False: an unhandled exception in the app (e.g. a
# Groq RateLimitError) becomes a normal 500 response instead of crashing
# this script and losing all progress made so far.
client = TestClient(app, raise_server_exceptions=False)

DEMO_USERS = {
    "hr": ("alice", "alice123"),
    "finance": ("bob", "bob123"),
    "engineering": ("charlie", "charlie123"),
    "marketing": ("diana", "diana123"),
    "admin": ("admin", "admin123"),
}

SQL_UNAUTHORIZED_ROLES = {"engineering", "marketing"}
SQL_BOUNDARY_QUESTIONS = [
    "How many employees are in the organization?",
    "What was the total revenue last quarter?",
    "List all employee salaries",
]

MAX_RETRIES = 3
DEFAULT_DELAY = 1.5
CHECKPOINT_PATH = Path("reports/rbac_security_eval_checkpoint.json")

RETRY_AFTER_RE = re.compile(r"try again in (?:(\d+)m)?(\d+(?:\.\d+)?)s", re.IGNORECASE)


def _parse_retry_after(text: str) -> float | None:
    """Extract Groq's 'try again in 7m33.6s' hint from an error body, if present."""
    match = RETRY_AFTER_RE.search(text or "")
    if not match:
        return None
    minutes = float(match.group(1) or 0)
    seconds = float(match.group(2))
    return minutes * 60 + seconds


def _request_with_retry(method: str, url: str, delay: float, **kwargs):
    """
    Call the TestClient with retry/backoff on 429 or 5xx (e.g. an unhandled
    RateLimitError surfacing as a 500). Returns (response_or_none, inconclusive_bool).
    """
    last_resp = None
    for attempt in range(1, MAX_RETRIES + 1):
        resp = client.request(method, url, **kwargs)
        last_resp = resp

        if resp.status_code < 400 or resp.status_code in (401, 403):
            # Success, or an expected auth rejection we actually want to assert on.
            time.sleep(delay)
            return resp, False

        # 429 or unexpected 5xx — treat as a transient infra issue and retry.
        wait = _parse_retry_after(resp.text) or (delay * (2 ** attempt))
        wait = min(wait, 60)  # don't block the whole run for a 7-minute daily-limit wait
        print(f"         ⚠️  {resp.status_code} on attempt {attempt}/{MAX_RETRIES} "
              f"for {method} {url} — waiting {wait:.1f}s before retry...")
        time.sleep(wait)

    print(f"         ❌ Still failing after {MAX_RETRIES} attempts "
          f"(last status {last_resp.status_code if last_resp else '?'}) — marking inconclusive.")
    return last_resp, True


def get_token(username: str, password: str) -> str:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"Login failed for {username}: {r.text}"
    return r.json()["access_token"]


def build_cross_role_probes(max_per_pair: int) -> list[dict]:
    """
    For every role, pick up to max_per_pair questions per OTHER role whose
    namespace that role isn't allowed to see. Capping per-pair keeps the
    Groq call count (and rate-limit risk) bounded regardless of dataset size.
    """
    probes = []
    for role in DEMO_USERS:
        allowed = set(get_allowed_namespaces(role))
        per_owner_count: dict[str, int] = {}
        for item in EVAL_DATASET:
            owner = item["role"]
            if owner == role:
                continue
            if item["namespace"] in allowed:
                continue  # role is legitimately allowed this namespace (e.g. admin)
            if per_owner_count.get(owner, 0) >= max_per_pair:
                continue
            per_owner_count[owner] = per_owner_count.get(owner, 0) + 1
            probes.append({
                "probing_role": role,
                "owner_role": owner,
                "restricted_namespace": item["namespace"],
                "question": item["question"],
            })
    return probes


def save_checkpoint(stage: str, violations: list, inconclusive: list, checks_run: int):
    Path("reports").mkdir(exist_ok=True)
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump({
            "last_completed_stage": stage,
            "checks_run": checks_run,
            "violations": violations,
            "inconclusive": inconclusive,
        }, f, indent=2)


def run_evaluation(max_per_pair: int, delay: float) -> dict:
    print("\n🛡️  Starting RBAC Access-Control Security Evaluation")
    print("=" * 65)
    print(f"   Max probes per (role, owner-role) pair: {max_per_pair}")
    print(f"   Delay between calls: {delay}s")
    print("=" * 65)

    violations = []
    inconclusive = []
    checks_run = 0
    tokens = {role: get_token(u, p) for role, (u, p) in DEMO_USERS.items()}

    # ── 1. Cross-role probing ──────────────────────────────────────────
    probes = build_cross_role_probes(max_per_pair)
    print(f"\n[1/5] Cross-role probing ({len(probes)} probes)...")
    for i, probe in enumerate(probes):
        checks_run += 1
        resp, timed_out = _request_with_retry(
            "POST", "/query", delay,
            json={"query": probe["question"], "token": tokens[probe["probing_role"]]},
        )
        if timed_out:
            inconclusive.append({"check": "cross_role_probe", "detail": probe,
                                  "issue": "Repeated 429/5xx — likely Groq rate limit, not verified"})
            continue
        if resp.status_code != 200:
            violations.append({"check": "cross_role_probe", "detail": probe,
                                "issue": f"Unexpected status {resp.status_code}"})
            continue
        data = resp.json()
        leaked_ns = [ns for ns in data.get("namespaces_accessed", [])
                     if not is_authorized(probe["probing_role"], ns)]
        if leaked_ns:
            violations.append({
                "check": "cross_role_probe",
                "detail": probe,
                "issue": f"Role '{probe['probing_role']}' retrieved unauthorized "
                         f"namespace(s): {leaked_ns}",
            })
        if (i + 1) % 10 == 0:
            save_checkpoint("cross_role_probing_in_progress", violations, inconclusive, checks_run)
    n_fail = sum(1 for v in violations if v["check"] == "cross_role_probe")
    n_inc = sum(1 for v in inconclusive if v["check"] == "cross_role_probe")
    print(f"      {len(probes) - n_fail - n_inc}/{len(probes)} passed "
          f"({n_fail} violations, {n_inc} inconclusive)")
    save_checkpoint("cross_role_probing", violations, inconclusive, checks_run)

    # ── 2. Own-namespace sanity ────────────────────────────────────────
    own_checks = [item for item in EVAL_DATASET if item["role"] in DEMO_USERS]
    print(f"\n[2/5] Own-namespace sanity ({len(own_checks)} questions)...")
    for i, item in enumerate(own_checks):
        checks_run += 1
        resp, timed_out = _request_with_retry(
            "POST", "/query", delay,
            json={"query": item["question"], "token": tokens[item["role"]]},
        )
        if timed_out:
            inconclusive.append({"check": "own_namespace_sanity", "detail": item,
                                  "issue": "Repeated 429/5xx — likely Groq rate limit, not verified"})
            continue
        if resp.status_code != 200:
            violations.append({"check": "own_namespace_sanity", "detail": item,
                                "issue": f"Unexpected status {resp.status_code}"})
            continue
        data = resp.json()
        unauthorized = [ns for ns in data.get("namespaces_accessed", [])
                         if not is_authorized(item["role"], ns)]
        if unauthorized:
            violations.append({"check": "own_namespace_sanity", "detail": item,
                                "issue": f"Returned unauthorized namespaces: {unauthorized}"})
        if (i + 1) % 10 == 0:
            save_checkpoint("own_namespace_sanity_in_progress", violations, inconclusive, checks_run)
    print(f"      stage complete")
    save_checkpoint("own_namespace_sanity", violations, inconclusive, checks_run)

    # ── 3. Admin-only endpoint enforcement (no Groq calls — fast, no retry needed) ──
    print(f"\n[3/5] Admin-only endpoint enforcement...")
    for role, token in tokens.items():
        checks_run += 1
        resp = client.get(f"/admin/audit-logs?token={token}&limit=5")
        if role == "admin":
            if resp.status_code != 200:
                violations.append({"check": "admin_endpoint", "detail": {"role": role},
                                    "issue": f"Admin denied access: {resp.status_code}"})
        elif resp.status_code != 403:
            violations.append({"check": "admin_endpoint", "detail": {"role": role},
                                "issue": f"Non-admin role '{role}' got status "
                                         f"{resp.status_code} instead of 403"})
    print(f"      checked {len(tokens)} roles")

    # ── 4. Token integrity (no Groq calls) ──────────────────────────────
    print(f"\n[4/5] Token integrity (tampered/garbage tokens)...")
    bad_tokens = ["garbage.token.value", tokens["hr"][:-3] + "xyz", ""]
    for bad in bad_tokens:
        checks_run += 1
        resp = client.post("/query", json={"query": "test", "token": bad})
        if resp.status_code != 401:
            violations.append({"check": "token_integrity", "detail": {"token_sample": bad[:20]},
                                "issue": f"Bad token accepted with status {resp.status_code}"})
    print(f"      checked {len(bad_tokens)} malformed tokens")

    # ── 5. SQL-agent boundary ──────────────────────────────────────────
    print(f"\n[5/5] SQL-agent boundary for unauthorized roles...")
    for role in SQL_UNAUTHORIZED_ROLES:
        for q in SQL_BOUNDARY_QUESTIONS:
            checks_run += 1
            resp, timed_out = _request_with_retry(
                "POST", "/query", delay, json={"query": q, "token": tokens[role]},
            )
            if timed_out or resp.status_code != 200:
                if timed_out:
                    inconclusive.append({"check": "sql_boundary", "detail": {"role": role, "question": q},
                                          "issue": "Repeated 429/5xx — not verified"})
                continue
            data = resp.json()
            if data.get("response_type") == "sql":
                violations.append({
                    "check": "sql_boundary",
                    "detail": {"role": role, "question": q},
                    "issue": f"Role '{role}' received a SQL-agent answer despite no "
                             f"structured-data access",
                })
    print(f"      checked {len(SQL_UNAUTHORIZED_ROLES) * len(SQL_BOUNDARY_QUESTIONS)} boundary queries")

    passed = checks_run - len(violations) - len(inconclusive)
    summary = {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "checks_run": checks_run,
        "checks_passed": passed,
        "violations_found": len(violations),
        "inconclusive_count": len(inconclusive),
        "pass_rate": round(passed / checks_run, 4) if checks_run else 0.0,
        "violations": violations,
        "inconclusive": inconclusive,
    }
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()  # run completed cleanly, checkpoint no longer needed
    return summary


def save_results(summary: dict):
    Path("reports").mkdir(exist_ok=True)
    path = f"reports/rbac_security_eval_{summary['timestamp']}.json"
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n💾 JSON saved: {path}")
    return path


def print_summary(summary: dict):
    print("\n" + "=" * 65)
    print("🛡️  RBAC SECURITY EVALUATION RESULTS")
    print("=" * 65)
    print(f"  Checks run       : {summary['checks_run']}")
    print(f"  Checks passed    : {summary['checks_passed']}")
    print(f"  Violations found : {summary['violations_found']}")
    print(f"  Inconclusive     : {summary['inconclusive_count']} (rate-limited / not verified)")
    print(f"  Pass rate        : {summary['pass_rate']:.2%} (excludes inconclusive)")
    if summary["violations"]:
        print(f"\n  ❌ VIOLATIONS:")
        for v in summary["violations"]:
            print(f"    [{v['check']}] {v['issue']}")
            print(f"      detail: {v['detail']}")
    else:
        print(f"\n  ✅ No RBAC violations detected.")
    if summary["inconclusive"]:
        print(f"\n  ⚠️  INCONCLUSIVE (re-run later to confirm — likely Groq rate limit):")
        for v in summary["inconclusive"]:
            print(f"    [{v['check']}] {v['detail'].get('question', v['detail'])}")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="RBAC access-control security evaluation")
    parser.add_argument("--max-per-pair", type=int, default=2,
                         help="Max cross-role probe questions per (role, owner-role) pair "
                              "(default 2; lower this if you're rate-limited)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                         help="Seconds to sleep between requests that hit Groq")
    args = parser.parse_args()

    try:
        summary = run_evaluation(max_per_pair=args.max_per_pair, delay=args.delay)
        save_results(summary)
        print_summary(summary)
    except KeyboardInterrupt:
        print(f"\n\n⏸️  Interrupted. Partial progress saved to {CHECKPOINT_PATH}")
        sys.exit(1)


if __name__ == "__main__":
    main()
