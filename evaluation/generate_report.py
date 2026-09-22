"""
Generates a clean HTML evaluation report from RAGAS results.
Run AFTER evaluate_rag.py has produced a JSON file in reports/.

Run: python -m evaluation.generate_report
"""

import json
import glob
import os
from pathlib import Path
from datetime import datetime


def load_latest_results() -> tuple[dict, str]:
    """Load the most recent evaluation JSON from reports/."""
    files = sorted(glob.glob("reports/rag_eval_*.json"), reverse=True)
    if not files:
        raise FileNotFoundError(
            "No evaluation results found. Run evaluate_rag.py first."
        )
    latest = files[0]
    with open(latest) as f:
        return json.load(f), latest


def score_color(score: float) -> str:
    if score >= 0.75:
        return "#22c55e"   # green
    elif score >= 0.50:
        return "#f59e0b"   # amber
    else:
        return "#ef4444"   # red


def score_label(score: float) -> str:
    if score >= 0.75:
        return "Good"
    elif score >= 0.50:
        return "Fair"
    else:
        return "Needs Improvement"


def generate_html(scores: dict) -> str:
    s = scores["scores"]
    overall = scores["overall_score"]
    ts = scores.get("timestamp", "N/A")
    n = scores.get("total_questions", 0)

    metrics = [
        ("Faithfulness",      s["faithfulness"],
         "Answer is grounded in retrieved context. Prevents hallucination."),
        ("Answer Relevancy",  s["answer_relevancy"],
         "Answer directly addresses the user's question."),
        ("Context Precision", s["context_precision"],
         "Retrieved chunks are relevant to the question."),
        ("Context Recall",    s["context_recall"],
         "Retrieved context covers the expected ground truth."),
    ]

    cards_html = ""
    for name, val, desc in metrics:
        color = score_color(val)
        label = score_label(val)
        pct = int(val * 100)
        cards_html += f"""
        <div class="card">
            <div class="metric-name">{name}</div>
            <div class="metric-score" style="color:{color}">{val:.4f}</div>
            <div class="badge" style="background:{color}">{label}</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width:{pct}%;background:{color}"></div>
            </div>
            <div class="metric-desc">{desc}</div>
        </div>"""

    overall_color = score_color(overall)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RAG Evaluation Report — Emerson Enterprise AI</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
  .header {{ background: linear-gradient(135deg, #1e3a5f, #0f172a); padding: 40px; border-bottom: 2px solid #334155; }}
  .header h1 {{ font-size: 28px; font-weight: 700; color: #f8fafc; }}
  .header h2 {{ font-size: 16px; color: #94a3b8; margin-top: 6px; }}
  .meta {{ display: flex; gap: 30px; margin-top: 20px; }}
  .meta-item {{ background: #1e293b; padding: 10px 20px; border-radius: 8px; font-size: 14px; }}
  .meta-item span {{ color: #94a3b8; }}
  .meta-item strong {{ color: #f1f5f9; display: block; font-size: 16px; margin-top: 2px; }}
  .container {{ max-width: 1100px; margin: 40px auto; padding: 0 24px; }}
  .section-title {{ font-size: 20px; font-weight: 600; color: #cbd5e1; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #334155; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 40px; }}
  .card {{ background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; }}
  .metric-name {{ font-size: 14px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }}
  .metric-score {{ font-size: 42px; font-weight: 700; margin: 10px 0 6px; }}
  .badge {{ display: inline-block; padding: 3px 12px; border-radius: 20px; font-size: 12px; color: white; font-weight: 600; margin-bottom: 14px; }}
  .progress-bar {{ background: #334155; border-radius: 4px; height: 6px; margin-bottom: 14px; }}
  .progress-fill {{ height: 6px; border-radius: 4px; transition: width 0.3s; }}
  .metric-desc {{ font-size: 12px; color: #64748b; line-height: 1.5; }}
  .overall {{ background: #1e293b; border-radius: 12px; padding: 30px; border: 2px solid {overall_color}; margin-bottom: 40px; display: flex; align-items: center; justify-content: space-between; }}
  .overall-left h3 {{ font-size: 18px; color: #94a3b8; }}
  .overall-left p {{ font-size: 13px; color: #64748b; margin-top: 6px; max-width: 500px; }}
  .overall-score {{ font-size: 64px; font-weight: 800; color: {overall_color}; }}
  .info-box {{ background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; margin-bottom: 40px; }}
  .info-box h3 {{ font-size: 16px; color: #cbd5e1; margin-bottom: 16px; }}
  .info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
  .info-item {{ background: #0f172a; padding: 12px 16px; border-radius: 8px; font-size: 13px; }}
  .info-item .label {{ color: #64748b; margin-bottom: 4px; }}
  .info-item .value {{ color: #e2e8f0; font-weight: 500; }}
  .footer {{ text-align: center; padding: 30px; color: #475569; font-size: 13px; border-top: 1px solid #1e293b; margin-top: 20px; }}
</style>
</head>
<body>

<div class="header">
  <h1>🏭 Emerson Enterprise AI — RAG Evaluation Report</h1>
  <h2>BITS Pilani MTech AI/ML Dissertation · Ajay Saini (2024aa05167)</h2>
  <div class="meta">
    <div class="meta-item"><span>Evaluation Date</span><strong>{datetime.now().strftime('%d %B %Y, %H:%M')}</strong></div>
    <div class="meta-item"><span>Questions Evaluated</span><strong>{n}</strong></div>
    <div class="meta-item"><span>LLM Used</span><strong>LLaMA 3.3 70B (Groq)</strong></div>
    <div class="meta-item"><span>Embedding Model</span><strong>all-MiniLM-L6-v2</strong></div>
    <div class="meta-item"><span>Vector DB</span><strong>ChromaDB</strong></div>
  </div>
</div>

<div class="container">

  <div style="margin-bottom:30px; margin-top:10px;">
    <div class="section-title">Overall Performance</div>
    <div class="overall">
      <div class="overall-left">
        <h3>Overall RAG Score</h3>
        <p>Average across all four RAGAS metrics: Faithfulness, Answer Relevancy, Context Precision, and Context Recall. Score above 0.75 indicates production-ready quality.</p>
      </div>
      <div class="overall-score">{overall:.2f}</div>
    </div>
  </div>

  <div class="section-title">Metric Breakdown</div>
  <div class="cards">
    {cards_html}
  </div>

  <div class="info-box">
    <h3>📋 Evaluation Configuration</h3>
    <div class="info-grid">
      <div class="info-item"><div class="label">Framework</div><div class="value">RAGAS v0.1+</div></div>
      <div class="info-item"><div class="label">Roles Tested</div><div class="value">HR, Finance, Engineering, Marketing, Admin</div></div>
      <div class="info-item"><div class="label">Chunking Strategy</div><div class="value">500 chars, 100 overlap</div></div>
      <div class="info-item"><div class="label">Top-K Retrieval</div><div class="value">5 chunks per namespace</div></div>
      <div class="info-item"><div class="label">Access Control</div><div class="value">Role-Based (RBAC)</div></div>
      <div class="info-item"><div class="label">Guardrails</div><div class="value">Prompt injection + keyword filter</div></div>
    </div>
  </div>

  <div class="info-box">
    <h3>📖 Metric Definitions</h3>
    <div class="info-grid">
      <div class="info-item">
        <div class="label">Faithfulness</div>
        <div class="value">Measures if the answer is factually consistent with the retrieved context. Score of 1.0 means no hallucination.</div>
      </div>
      <div class="info-item">
        <div class="label">Answer Relevancy</div>
        <div class="value">Measures how pertinent the answer is to the question asked. Penalises incomplete or off-topic answers.</div>
      </div>
      <div class="info-item">
        <div class="label">Context Precision</div>
        <div class="value">Measures the signal-to-noise ratio of retrieved chunks. Higher means fewer irrelevant chunks retrieved.</div>
      </div>
      <div class="info-item">
        <div class="label">Context Recall</div>
        <div class="value">Measures how much of the ground truth is covered by the retrieved context. Higher means better coverage.</div>
      </div>
    </div>
  </div>

</div>

<div class="footer">
  Dissertation: Design and Evaluation of a Secure RAG System with RBAC for Enterprise Knowledge Management<br>
  BITS Pilani WILP · MTech AI/ML · S2-25_AIMLCZG628T · April 2026
</div>

</body>
</html>"""
    return html


def main():
    print("📊 Generating HTML evaluation report...")

    scores, source_file = load_latest_results()
    print(f"   Loaded results from: {source_file}")

    html = generate_html(scores)

    Path("reports").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"reports/rag_eval_report_{timestamp}.html"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ HTML report saved: {out_path}")
    print(f"   Open with: start {out_path}")


if __name__ == "__main__":
    main()
