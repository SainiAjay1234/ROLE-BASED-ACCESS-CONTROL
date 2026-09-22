"""
SQL Agent Accuracy Evaluation.

evaluate_rag.py and llm_judge.py both call run_rag()/generate_answer() directly
— they never exercise app/sql_agent.py, even though several EVAL_DATASET
questions ("how many employees...", "total revenue...") are exactly the kind
of question query_classifier.py routes to SQL. This script tests the NL->SQL
pipeline directly against ground truth computed independently from the same
in-memory sample tables (SAMPLE_HR_DATA / SAMPLE_FINANCE_DATA), so a wrong
answer here means the LLM's generated SQL (or its formatting) was wrong —
not that the retrieval/RBAC layer was wrong (that's covered by
rbac_security_eval.py).

Approach: each test case gives an expected value computed directly with
pandas, plus a "check" type describing how to validate the agent's markdown
table / text output against it (numeric containment, or text containment for
name lookups). This keeps the eval deterministic and free of a second LLM
judge call.

Run: python -m evaluation.sql_agent_eval
"""

import sys
import re
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.sql_agent import run_sql_agent, SAMPLE_HR_DATA, SAMPLE_FINANCE_DATA

# ── Ground truth computed independently from the same sample tables ───────
SQL_EVAL_DATASET = [
    {
        "role": "hr",
        "question": "How many employees are there in total?",
        "expected": len(SAMPLE_HR_DATA),
        "check": "numeric",
    },
    {
        "role": "hr",
        "question": "How many employees work in the Engineering department?",
        "expected": int((SAMPLE_HR_DATA["department"] == "Engineering").sum()),
        "check": "numeric",
    },
    {
        "role": "hr",
        "question": "What is the average salary of all employees?",
        "expected": round(SAMPLE_HR_DATA["salary"].mean(), 2),
        "check": "numeric",
    },
    {
        "role": "hr",
        "question": "Who is the employee with the highest salary?",
        "expected": SAMPLE_HR_DATA.loc[SAMPLE_HR_DATA["salary"].idxmax(), "name"],
        "check": "text",
    },
    {
        "role": "hr",
        "question": "How many employees are based in Noida?",
        "expected": int((SAMPLE_HR_DATA["location"] == "Noida").sum()),
        "check": "numeric",
    },
    {
        "role": "hr",
        "question": "List employees with more than 5 years of experience.",
        "expected": SAMPLE_HR_DATA[SAMPLE_HR_DATA["years_exp"] > 5]["name"].tolist(),
        "check": "text_list",
    },
    {
        "role": "finance",
        "question": "What was the total revenue across all quarters?",
        "expected": int(SAMPLE_FINANCE_DATA["revenue"].sum()),
        "check": "numeric",
    },
    {
        "role": "finance",
        "question": "What was the profit in Q4?",
        "expected": int(SAMPLE_FINANCE_DATA.loc[SAMPLE_FINANCE_DATA["quarter"] == "Q4", "profit"].iloc[0]),
        "check": "numeric",
    },
    {
        "role": "finance",
        "question": "What were the total expenses for the year?",
        "expected": int(SAMPLE_FINANCE_DATA["expenses"].sum()),
        "check": "numeric",
    },
    {
        "role": "finance",
        "question": "Which quarter had the highest revenue?",
        "expected": SAMPLE_FINANCE_DATA.loc[SAMPLE_FINANCE_DATA["revenue"].idxmax(), "quarter"],
        "check": "text",
    },
    {
        "role": "admin",
        "question": "How many employees are in the HR department?",
        "expected": int((SAMPLE_HR_DATA["department"] == "HR").sum()),
        "check": "numeric",
    },
    {
        "role": "admin",
        "question": "What is the total profit across all quarters?",
        "expected": int(SAMPLE_FINANCE_DATA["profit"].sum()),
        "check": "numeric",
    },
    # Roles with no structured data — must be denied, not hallucinate a number
    {
        "role": "engineering",
        "question": "How many employees are there in total?",
        "expected": None,
        "check": "denied",
    },
    {
        "role": "marketing",
        "question": "What was the total revenue last quarter?",
        "expected": None,
        "check": "denied",
    },
]


def _extract_numbers(text: str) -> list[float]:
    cleaned = text.replace(",", "")
    return [float(n) for n in re.findall(r"-?\d+\.?\d*", cleaned)]


def check_numeric(answer: str, expected: float, tolerance: float = 0.5) -> bool:
    numbers = _extract_numbers(answer)
    return any(abs(n - expected) <= tolerance for n in numbers)


def check_text(answer: str, expected: str) -> bool:
    return expected.lower() in answer.lower()


def check_text_list(answer: str, expected: list) -> bool:
    return all(name.lower() in answer.lower() for name in expected)


def check_denied(answer: str, success: bool) -> bool:
    # Either the agent explicitly denies access, or fails cleanly (success=False)
    # without returning a markdown table full of numbers/data.
    denial_phrases = ["do not have access", "no access", "not authorized"]
    return (not success) or any(p in answer.lower() for p in denial_phrases)


def run_evaluation() -> list[dict]:
    print("\n🧮  Starting SQL Agent Accuracy Evaluation")
    print("=" * 65)
    print(f"   Total questions: {len(SQL_EVAL_DATASET)}")
    print("=" * 65)

    results = []
    for i, item in enumerate(SQL_EVAL_DATASET):
        role = item["role"]
        question = item["question"]
        expected = item["expected"]
        check_type = item["check"]

        print(f"\n[{i+1:02d}/{len(SQL_EVAL_DATASET)}] Role: {role.upper():<12} | {question[:52]}...")
        answer, success = run_sql_agent(question, role)

        if check_type == "numeric":
            passed = success and check_numeric(answer, expected)
        elif check_type == "text":
            passed = success and check_text(answer, expected)
        elif check_type == "text_list":
            passed = success and check_text_list(answer, expected)
        elif check_type == "denied":
            passed = check_denied(answer, success)
        else:
            passed = False

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"         {status} | expected={expected!r} | success={success} | "
              f"answer={answer[:100]!r}")

        results.append({
            "index": i + 1,
            "role": role,
            "question": question,
            "check_type": check_type,
            "expected": expected,
            "agent_success": success,
            "agent_answer": answer[:400],
            "passed": passed,
        })

    return results


def compute_summary(results: list[dict]) -> dict:
    n = len(results)
    passed = sum(1 for r in results if r["passed"])

    roles = {}
    for r in results:
        roles.setdefault(r["role"], []).append(r["passed"])
    per_role = {role: round(sum(p) / len(p), 4) for role, p in roles.items()}

    return {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "total_questions": n,
        "passed": passed,
        "failed": n - passed,
        "accuracy": round(passed / n, 4) if n else 0.0,
        "per_role_accuracy": per_role,
        "failures": [
            {"question": r["question"], "role": r["role"], "expected": r["expected"],
             "got": r["agent_answer"]}
            for r in results if not r["passed"]
        ],
    }


def save_results(results: list[dict], summary: dict):
    Path("reports").mkdir(exist_ok=True)
    ts = summary["timestamp"]

    json_path = f"reports/sql_agent_eval_{ts}.json"
    with open(json_path, "w") as f:
        json.dump({"summary": summary, "details": results}, f, indent=2)
    print(f"\n💾 JSON saved: {json_path}")

    csv_path = f"reports/sql_agent_eval_{ts}.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("index,role,question,check_type,expected,agent_success,passed\n")
        for r in results:
            q = r["question"].replace('"', "'")
            f.write(f'{r["index"]},{r["role"]},"{q}",{r["check_type"]},'
                    f'"{r["expected"]}",{r["agent_success"]},{r["passed"]}\n')
    print(f"💾 CSV saved : {csv_path}")


def print_summary(summary: dict):
    print("\n" + "=" * 65)
    print("🧮  SQL AGENT ACCURACY EVALUATION RESULTS")
    print("=" * 65)
    print(f"  Total Questions : {summary['total_questions']}")
    print(f"  Passed          : {summary['passed']}")
    print(f"  Failed          : {summary['failed']}")
    print(f"  Accuracy        : {summary['accuracy']:.2%}")
    print(f"\n  Per-Role Accuracy:")
    for role, acc in summary["per_role_accuracy"].items():
        bar = "█" * int(acc * 25)
        empty = "░" * (25 - int(acc * 25))
        print(f"    {role:<12} : {acc:.2%}  {bar}{empty}")
    if summary["failures"]:
        print(f"\n  ❌ Failures:")
        for f in summary["failures"]:
            print(f"    - [{f['role']}] {f['question']}")
            print(f"      expected={f['expected']!r} got={f['got'][:100]!r}")
    print("=" * 65)


def main():
    results = run_evaluation()
    summary = compute_summary(results)
    save_results(results, summary)
    print_summary(summary)


if __name__ == "__main__":
    main()
