"""
LLM-as-a-Judge Evaluation for the Emerson Secure RAG system.

Unlike evaluate_rag.py (keyword-overlap scoring, zero API calls), this module
uses an LLM (via Groq) as an impartial judge to score each generated answer on:

    1. faithfulness       — is the answer grounded in the retrieved context?
    2. answer_relevancy    — does the answer address the question?
    3. context_precision   — is the retrieved context focused / low-noise?
    4. context_recall      — does the context cover the ground-truth info?
    5. correctness         — does the answer match the ground-truth meaning?

Design notes:
    - One combined judge call per question (5 scores + reasoning in a single
      JSON response) instead of one call per metric, to stay well within
      Groq free-tier rate limits (50 questions -> 50 judge calls, not 250).
    - Retries with exponential backoff on transient/rate-limit errors.
    - A configurable delay between calls further protects the rate limit.
    - Judge model defaults to a different, smaller model than the answer
      generator (llama-3.1-8b-instant vs llama-3.3-70b-versatile) to reduce
      self-evaluation bias and cost. Override with LLM_JUDGE_MODEL.

Run:
    python -m evaluation.llm_judge
    python -m evaluation.llm_judge --sample 10        # judge only 10 questions
    python -m evaluation.llm_judge --delay 3           # 3s between calls
"""

import os
import re
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from groq import Groq
from groq import APIStatusError, APIConnectionError

from app.rag_agent import retrieve_documents, generate_answer
from evaluation.eval_dataset import EVAL_DATASET

JUDGE_MODEL = os.getenv("LLM_JUDGE_MODEL", "llama-3.1-8b-instant")
DEFAULT_DELAY_SECONDS = float(os.getenv("GROQ_JUDGE_DELAY", "2"))
MAX_RETRIES = 3
CONTEXT_CHAR_LIMIT = 4000  # keep judge prompt small & fast

judge_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

METRICS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "correctness",
]

JUDGE_SYSTEM_PROMPT = """You are an impartial evaluator for a role-based access \
control (RBAC) enterprise RAG (Retrieval-Augmented Generation) system.

You will receive: the user's role, their question, the context chunks that \
were retrieved for them, a reference ground-truth answer, and the answer the \
system actually generated.

Score the generated answer on these 5 dimensions, each a float from 0.0 to 1.0 \
(use real decimals such as 0.2, 0.65, 0.9 — not only 0, 0.5, or 1):

- faithfulness: Is every claim in the answer supported by the retrieved context? \
1.0 = fully grounded, no hallucination. 0.0 = contradicts or invents facts not \
present in the context.
- answer_relevancy: Does the answer directly and completely address the question? \
1.0 = fully relevant and on-topic. 0.0 = off-topic, evasive, or a non-answer.
- context_precision: Is the retrieved context focused, with little irrelevant \
material? 1.0 = all retrieved chunks are on-topic. 0.0 = mostly noise/irrelevant.
- context_recall: Does the retrieved context actually contain the information \
needed to produce the ground-truth answer? 1.0 = fully covers it. 0.0 = missing.
- correctness: Does the generated answer match the meaning/content of the \
ground-truth reference answer? 1.0 = semantically equivalent. 0.0 = contradicts \
or unrelated. Note the system intentionally refuses when context is empty — \
score such a refusal as correct (high) if the ground truth also implies the \
information isn't retrievable, otherwise score it on whether refusing was the \
right call given the context provided.

Respond with ONLY a single JSON object and nothing else — no markdown fences, \
no preamble, no explanation outside the JSON. Exact schema:

{"faithfulness": <float>, "answer_relevancy": <float>, "context_precision": <float>, \
"context_recall": <float>, "correctness": <float>, "reasoning": "<1-2 sentence justification>"}
"""


def _build_user_prompt(role: str, question: str, context_chunks: list[str],
                        ground_truth: str, answer: str) -> str:
    context = "\n\n---\n\n".join(context_chunks) if context_chunks else "(No context was retrieved.)"
    if len(context) > CONTEXT_CHAR_LIMIT:
        context = context[:CONTEXT_CHAR_LIMIT] + "\n...[truncated]"
    return f"""User role: {role}

Question: {question}

Retrieved context:
{context}

Ground-truth reference answer:
{ground_truth}

System-generated answer:
{answer}

Score the system-generated answer as instructed and return the JSON object."""


def _parse_judge_json(text: str) -> dict:
    """Extract and validate the JSON object from a judge response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in judge response")
    data = json.loads(match.group(0))

    parsed = {}
    for m in METRICS:
        val = float(data.get(m, 0.0))
        parsed[m] = max(0.0, min(1.0, round(val, 4)))
    parsed["reasoning"] = str(data.get("reasoning", "")).strip()[:500]
    return parsed


def judge_answer(role: str, question: str, context_chunks: list[str],
                  ground_truth: str, answer: str, delay: float) -> dict:
    """Call the judge LLM once per question, with retries on failure."""
    user_prompt = _build_user_prompt(role, question, context_chunks, ground_truth, answer)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = judge_client.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=400,
            )
            raw = response.choices[0].message.content.strip()
            result = _parse_judge_json(raw)
            result["error"] = None
            time.sleep(delay)
            return result

        except (APIStatusError, APIConnectionError, ValueError, json.JSONDecodeError) as e:
            last_error = e
            wait = delay * (2 ** (attempt - 1))
            print(f"         ⚠️  Judge call failed (attempt {attempt}/{MAX_RETRIES}): {e}. "
                  f"Retrying in {wait:.1f}s...")
            time.sleep(wait)

    # All retries exhausted — record an error row instead of crashing the run
    print(f"         ❌ Judge failed after {MAX_RETRIES} attempts: {last_error}")
    fallback = {m: None for m in METRICS}
    fallback["reasoning"] = f"JUDGE_ERROR: {last_error}"
    fallback["error"] = str(last_error)
    return fallback


def run_llm_judge_evaluation(sample_size: int | None = None, delay: float = DEFAULT_DELAY_SECONDS) -> list:
    dataset = EVAL_DATASET if not sample_size else EVAL_DATASET[:sample_size]

    print("\n🧑‍⚖️  Starting LLM-as-a-Judge RAG Evaluation")
    print("=" * 65)
    print(f"   Judge model      : {JUDGE_MODEL}")
    print(f"   Total questions  : {len(dataset)}")
    print(f"   Delay between calls: {delay}s (rate-limit safety)")
    print(f"   Metrics          : {', '.join(METRICS)}")
    print("=" * 65)

    results = []
    for i, item in enumerate(dataset):
        role = item["role"]
        question = item["question"]
        gt = item["ground_truth"]
        namespace = item["namespace"]

        print(f"\n[{i+1:02d}/{len(dataset)}] Role: {role.upper():<12} | {question[:52]}...")

        chunks, namespaces = retrieve_documents(question, role)
        if not chunks:
            chunks = []
            namespaces = []

        answer = generate_answer(question, chunks, role)
        scores = judge_answer(role, question, chunks, gt, answer, delay)

        if scores["error"]:
            print(f"         SKIPPED (judge error)")
        else:
            avg = round(sum(scores[m] for m in METRICS) / len(METRICS), 4)
            scores["overall"] = avg
            print(f"         Faith={scores['faithfulness']:.2f}  "
                  f"Relevancy={scores['answer_relevancy']:.2f}  "
                  f"Precision={scores['context_precision']:.2f}  "
                  f"Recall={scores['context_recall']:.2f}  "
                  f"Correctness={scores['correctness']:.2f}  → Avg={avg:.2f}")

        results.append({
            "index": i + 1,
            "role": role,
            "namespace": namespace,
            "question": question,
            "ground_truth": gt,
            "answer": answer[:300],
            "namespaces_retrieved": namespaces,
            **scores,
        })

    return results


def compute_summary(results: list) -> dict:
    valid = [r for r in results if not r.get("error")]
    n_valid = len(valid)
    n_total = len(results)

    if n_valid == 0:
        raise RuntimeError("All judge calls failed — check GROQ_API_KEY / rate limits.")

    avg = lambda k: round(sum(r[k] for r in valid) / n_valid, 4)

    roles = {}
    for r in valid:
        roles.setdefault(r["role"], []).append(r["overall"])
    role_scores = {role: round(sum(s) / len(s), 4) for role, s in roles.items()}

    return {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "judge_model": JUDGE_MODEL,
        "total_questions": n_total,
        "scored_questions": n_valid,
        "failed_questions": n_total - n_valid,
        "scoring_method": "llm_as_judge",
        "scores": {m: avg(m) for m in METRICS},
        "overall_score": avg("overall"),
        "per_role_scores": role_scores,
    }


def save_results(results: list, summary: dict):
    Path("reports").mkdir(exist_ok=True)
    ts = summary["timestamp"]

    json_path = f"reports/llm_judge_eval_{ts}.json"
    with open(json_path, "w") as f:
        json.dump({"summary": summary, "details": results}, f, indent=2)
    print(f"\n💾 JSON saved : {json_path}")

    csv_path = f"reports/llm_judge_eval_{ts}.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("index,role,question,faithfulness,answer_relevancy,"
                "context_precision,context_recall,correctness,overall,reasoning\n")
        for r in results:
            if r.get("error"):
                f.write(f"{r['index']},{r['role']},\"{r['question'][:80]}\",ERROR,,,,,,\"{r['reasoning']}\"\n")
                continue
            reasoning = r["reasoning"].replace('"', "'")
            f.write(f"{r['index']},{r['role']},\"{r['question'][:80]}\","
                    f"{r['faithfulness']},{r['answer_relevancy']},"
                    f"{r['context_precision']},{r['context_recall']},"
                    f"{r['correctness']},{r['overall']},\"{reasoning}\"\n")
    print(f"💾 CSV saved  : {csv_path}")
    return json_path, csv_path


def print_summary(summary: dict):
    s = summary["scores"]
    print("\n" + "=" * 65)
    print("📈  LLM-AS-A-JUDGE EVALUATION RESULTS")
    print("=" * 65)
    print(f"  Judge Model        : {summary['judge_model']}")
    print(f"  Questions Scored   : {summary['scored_questions']}/{summary['total_questions']}"
          f" ({summary['failed_questions']} failed)")
    for m in METRICS:
        v = s[m]
        label = "✅ Good" if v >= 0.7 else ("⚠️ Fair" if v >= 0.45 else "❌ Poor")
        print(f"  {m:<18}: {v:.4f}  ({label})")
    print(f"  ─────────────────────────────────────────────────")
    print(f"  Overall Score      : {summary['overall_score']:.4f}")
    print(f"\n  Per-Role Breakdown:")
    for role, score in summary["per_role_scores"].items():
        bar = "█" * int(score * 25)
        empty = "░" * (25 - int(score * 25))
        print(f"    {role:<12} : {score:.4f}  {bar}{empty}")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="LLM-as-a-Judge RAG evaluation")
    parser.add_argument("--sample", type=int, default=None,
                         help="Evaluate only the first N questions (default: all 50)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS,
                         help="Seconds to sleep between judge calls (rate-limit safety)")
    args = parser.parse_args()

    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not set in .env — the judge needs it to call the LLM.")
        sys.exit(1)

    results = run_llm_judge_evaluation(sample_size=args.sample, delay=args.delay)
    summary = compute_summary(results)
    save_results(results, summary)
    print_summary(summary)
    print("\n✅ Done! Run: python -m evaluation.generate_llm_judge_report")


if __name__ == "__main__":
    main()
