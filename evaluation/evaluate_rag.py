"""
Custom RAG Evaluation — No RAGAS, No rate limit issues.
Uses keyword overlap scoring (instant, no extra LLM calls).
Optionally uses Groq for LLM scoring if tokens are available.

Run: python -m evaluation.evaluate_rag
"""

import os
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag_agent import retrieve_documents, generate_answer
from evaluation.eval_dataset import EVAL_DATASET

# Set to True only if you have fresh Groq tokens tomorrow
USE_LLM_SCORING = False


# ── Scoring functions (keyword-based, no API calls) ───────────────────────

def tokenize(text: str) -> set:
    import re
    return set(re.findall(r'\b\w+\b', text.lower()))


def score_faithfulness(answer: str, context_chunks: list[str]) -> float:
    """
    Faithfulness: what fraction of answer words appear in the context?
    High score = answer is grounded in context, not hallucinated.
    """
    context_text = " ".join(context_chunks)
    answer_words = tokenize(answer)
    context_words = tokenize(context_text)
    # Remove stopwords for better signal
    stopwords = {"the","a","an","is","are","was","were","be","been","being",
                 "have","has","had","do","does","did","will","would","could",
                 "should","may","might","to","of","in","on","at","for","with",
                 "and","or","but","not","it","its","this","that","these","those"}
    answer_content = answer_words - stopwords
    if not answer_content:
        return 1.0
    overlap = answer_content & context_words
    return round(len(overlap) / len(answer_content), 4)


def score_answer_relevancy(question: str, answer: str) -> float:
    """
    Answer Relevancy: how much of the question's keywords appear in the answer?
    High score = answer addresses the question.
    """
    q_words = tokenize(question)
    a_words = tokenize(answer)
    stopwords = {"what","how","which","when","where","who","is","are","the",
                 "a","an","of","in","at","for","to","and","or","does","do"}
    q_content = q_words - stopwords
    if not q_content:
        return 1.0
    overlap = q_content & a_words
    return round(len(overlap) / len(q_content), 4)


def score_context_recall(context_chunks: list[str], ground_truth: str) -> float:
    """
    Context Recall: how much of the ground truth is covered by retrieved context?
    High score = context contains expected information.
    """
    context_text = " ".join(context_chunks)
    gt_words = tokenize(ground_truth)
    ctx_words = tokenize(context_text)
    stopwords = {"the","a","an","is","are","was","were","to","of","in","on",
                 "at","for","with","and","or","it","its","this","that","as"}
    gt_content = gt_words - stopwords
    if not gt_content:
        return 1.0
    overlap = gt_content & ctx_words
    return round(len(overlap) / len(gt_content), 4)


def score_context_precision(question: str, context_chunks: list[str]) -> float:
    """
    Context Precision: how relevant are retrieved chunks to the question?
    High score = retrieved chunks are focused and relevant.
    """
    q_words = tokenize(question)
    scores = []
    for chunk in context_chunks[:5]:
        chunk_words = tokenize(chunk)
        if not chunk_words:
            continue
        overlap = q_words & chunk_words
        scores.append(len(overlap) / len(q_words))
    return round(sum(scores) / len(scores), 4) if scores else 0.0


# ── Main evaluation loop ──────────────────────────────────────────────────

def run_evaluation():
    print("\n🚀 Starting Custom RAG Evaluation (Keyword-Based Scoring)")
    print("=" * 65)
    print(f"   Total questions  : {len(EVAL_DATASET)}")
    print(f"   Scoring method   : Keyword overlap (no API calls)")
    print(f"   Metrics          : Faithfulness, Answer Relevancy,")
    print(f"                      Context Recall, Context Precision")
    print("=" * 65)

    results = []

    for i, item in enumerate(EVAL_DATASET):
        role      = item["role"]
        question  = item["question"]
        gt        = item["ground_truth"]
        namespace = item["namespace"]

        print(f"\n[{i+1:02d}/{len(EVAL_DATASET)}] "
              f"Role: {role.upper():<12} | {question[:52]}...")

        # 1. Retrieve from ChromaDB
        chunks, namespaces = retrieve_documents(question, role)
        if not chunks:
            chunks = ["No relevant documents found."]
            namespaces = []

        # 2. Generate answer via LLM
        answer = generate_answer(question, chunks, role)

        # 3. Score all 4 metrics (pure keyword, no API)
        faith  = score_faithfulness(answer, chunks)
        relev  = score_answer_relevancy(question, answer)
        recall = score_context_recall(chunks, gt)
        precis = score_context_precision(question, chunks)
        avg    = round((faith + relev + recall + precis) / 4, 4)

        print(f"         Faith={faith:.2f}  Relevancy={relev:.2f}  "
              f"Recall={recall:.2f}  Precision={precis:.2f}  → Avg={avg:.2f}")

        results.append({
            "index":               i + 1,
            "role":                role,
            "namespace":           namespace,
            "question":            question,
            "ground_truth":        gt,
            "answer":              answer[:300],
            "namespaces_retrieved": namespaces,
            "faithfulness":        faith,
            "answer_relevancy":    relev,
            "context_recall":      recall,
            "context_precision":   precis,
            "overall":             avg,
        })

    return results


def compute_summary(results: list) -> dict:
    n = len(results)
    avg = lambda k: round(sum(r[k] for r in results) / n, 4)

    roles = {}
    for r in results:
        roles.setdefault(r["role"], []).append(r["overall"])
    role_scores = {
        role: round(sum(s)/len(s), 4)
        for role, s in roles.items()
    }

    return {
        "timestamp":       datetime.now().strftime("%Y%m%d_%H%M%S"),
        "total_questions": n,
        "scoring_method":  "keyword_overlap",
        "scores": {
            "faithfulness":      avg("faithfulness"),
            "answer_relevancy":  avg("answer_relevancy"),
            "context_recall":    avg("context_recall"),
            "context_precision": avg("context_precision"),
        },
        "overall_score":   avg("overall"),
        "per_role_scores": role_scores,
    }


def save_results(results: list, summary: dict):
    Path("reports").mkdir(exist_ok=True)
    ts = summary["timestamp"]

    # JSON
    json_path = f"reports/rag_eval_{ts}.json"
    with open(json_path, "w") as f:
        json.dump({"summary": summary, "details": results}, f, indent=2)
    print(f"\n💾 JSON saved : {json_path}")

    # CSV
    csv_path = f"reports/rag_eval_{ts}.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("index,role,question,faithfulness,answer_relevancy,"
                "context_recall,context_precision,overall\n")
        for r in results:
            f.write(f"{r['index']},{r['role']},"
                    f"\"{r['question'][:80]}\","
                    f"{r['faithfulness']},{r['answer_relevancy']},"
                    f"{r['context_recall']},{r['context_precision']},"
                    f"{r['overall']}\n")
    print(f"💾 CSV saved  : {csv_path}")


def print_summary(summary: dict):
    s = summary["scores"]
    print("\n" + "=" * 65)
    print("📈  RAG EVALUATION RESULTS")
    print("=" * 65)
    print(f"  Total Questions    : {summary['total_questions']}")
    print(f"  Scoring Method     : {summary['scoring_method']}")
    print(f"  Faithfulness       : {s['faithfulness']:.4f}  "
          f"({'✅ Good' if s['faithfulness']>=0.6 else '⚠️ Fair'})")
    print(f"  Answer Relevancy   : {s['answer_relevancy']:.4f}  "
          f"({'✅ Good' if s['answer_relevancy']>=0.6 else '⚠️ Fair'})")
    print(f"  Context Recall     : {s['context_recall']:.4f}  "
          f"({'✅ Good' if s['context_recall']>=0.6 else '⚠️ Fair'})")
    print(f"  Context Precision  : {s['context_precision']:.4f}  "
          f"({'✅ Good' if s['context_precision']>=0.6 else '⚠️ Fair'})")
    print(f"  ─────────────────────────────────────────────────")
    print(f"  Overall Score      : {summary['overall_score']:.4f}")
    print(f"\n  Per-Role Breakdown:")
    for role, score in summary["per_role_scores"].items():
        bar   = "█" * int(score * 25)
        empty = "░" * (25 - int(score * 25))
        print(f"    {role:<12} : {score:.4f}  {bar}{empty}")
    print("=" * 65)


if __name__ == "__main__":
    results = run_evaluation()
    summary = compute_summary(results)
    save_results(results, summary)
    print_summary(summary)
    print("\n✅ Done! Run: python -m evaluation.generate_report")
