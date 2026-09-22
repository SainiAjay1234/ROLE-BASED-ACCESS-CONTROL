"""
Generates a clean HTML report from LLM-as-a-Judge evaluation results.
Run AFTER llm_judge.py has produced a JSON file in reports/.

Run: python -m evaluation.generate_llm_judge_report
"""

import json
import glob
from pathlib import Path
from datetime import datetime

METRIC_INFO = [
    ("faithfulness", "Faithfulness", "Answer is grounded in retrieved context. Prevents hallucination."),
    ("answer_relevancy", "Answer Relevancy", "Answer directly and completely addresses the question."),
    ("context_precision", "Context Precision", "Retrieved chunks are focused and relevant, low noise."),
    ("context_recall", "Context Recall", "Retrieved context covers the information in the ground truth."),
    ("correctness", "Correctness", "Generated answer matches the meaning of the ground-truth reference."),
]


def load_latest_results() -> tuple[dict, str]:
    files = sorted(glob.glob("reports/llm_judge_eval_*.json"), reverse=True)
    if not files:
        raise FileNotFoundError("No LLM-judge results found. Run: python -m evaluation.llm_judge")
    latest = files[0]
    with open(latest) as f:
        return json.load(f), latest


def score_color(score: float) -> str:
    if score >= 0.75:
        return "#22c55e"
    elif score >= 0.50:
        return "#f59e0b"
    return "#ef4444"


def score_label(score: float) -> str:
    if score >= 0.75:
        return "Good"
    elif score >= 0.50:
        return "Fair"
    return "Needs Improvement"


def lowest_scoring_rows(details: list, n: int = 8) -> list:
    valid = [d for d in details if not d.get("error")]
    return sorted(valid, key=lambda d: d["overall"])[:n]


def generate_html(data: dict) -> str:
    summary = data["summary"]
    details = data["details"]
    s = summary["scores"]
    overall = summary["overall_score"]
    ts = summary.get("timestamp", "N/A")

    cards_html = ""
    for key, name, desc in METRIC_INFO:
        val = s[key]
        color = score_color(val)
        label = score_label(val)
        pct = int(val * 100)
        cards_html += f"""
        <div class="card">
            <div class="metric-name">{name}</div>
            <div class="metric-score" style="color:{color}">{val:.4f}</div>
            <div class="badge" style="background:{color}">{label}</div>
            <div class="progress-bar"><div class="progress-fill" style="width:{pct}%;background:{color}"></div></div>
            <div class="metric-desc">{desc}</div>
        </div>"""

    role_rows = "".join(
        f"""<div class="info-item"><div class="label">{role}</div>
            <div class="value" style="color:{score_color(score)}">{score:.4f}</div></div>"""
        for role, score in summary["per_role_scores"].items()
    )

    worst = lowest_scoring_rows(details)
    worst_rows = ""
    for d in worst:
        worst_rows += f"""
        <tr>
          <td>{d['index']}</td>
          <td>{d['role']}</td>
          <td>{d['question']}</td>
          <td style="color:{score_color(d['overall'])}">{d['overall']:.2f}</td>
          <td class="reasoning">{d.get('reasoning', '')}</td>
        </tr>"""

    overall_color = score_color(overall)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LLM-as-a-Judge Evaluation Report — Emerson Enterprise AI</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
  .header {{ background: linear-gradient(135deg, #3f1e5f, #0f172a); padding: 40px; border-bottom: 2px solid #334155; }}
  .header h1 {{ font-size: 28px; font-weight: 700; color: #f8fafc; }}
  .header h2 {{ font-size: 16px; color: #94a3b8; margin-top: 6px; }}
  .meta {{ display: flex; gap: 30px; margin-top: 20px; flex-wrap: wrap; }}
  .meta-item {{ background: #1e293b; padding: 10px 20px; border-radius: 8px; font-size: 14px; }}
  .meta-item span {{ color: #94a3b8; }}
  .meta-item strong {{ color: #f1f5f9; display: block; font-size: 16px; margin-top: 2px; }}
  .container {{ max-width: 1100px; margin: 40px auto; padding: 0 24px; }}
  .section-title {{ font-size: 20px; font-weight: 600; color: #cbd5e1; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #334155; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }}
  .card {{ background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; }}
  .metric-name {{ font-size: 14px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }}
  .metric-score {{ font-size: 36px; font-weight: 700; margin: 10px 0 6px; }}
  .badge {{ display: inline-block; padding: 3px 12px; border-radius: 20px; font-size: 12px; color: white; font-weight: 600; margin-bottom: 14px; }}
  .progress-bar {{ background: #334155; border-radius: 4px; height: 6px; margin-bottom: 14px; }}
  .progress-fill {{ height: 6px; border-radius: 4px; }}
  .metric-desc {{ font-size: 12px; color: #64748b; line-height: 1.5; }}
  .overall {{ background: #1e293b; border-radius: 12px; padding: 30px; border: 2px solid {overall_color}; margin-bottom: 40px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px; }}
  .overall-left h3 {{ font-size: 18px; color: #94a3b8; }}
  .overall-left p {{ font-size: 13px; color: #64748b; margin-top: 6px; max-width: 500px; }}
  .overall-score {{ font-size: 64px; font-weight: 800; color: {overall_color}; }}
  .info-box {{ background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; margin-bottom: 40px; }}
  .info-box h3 {{ font-size: 16px; color: #cbd5e1; margin-bottom: 16px; }}
  .info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }}
  .info-item {{ background: #0f172a; padding: 12px 16px; border-radius: 8px; font-size: 13px; }}
  .info-item .label {{ color: #64748b; margin-bottom: 4px; }}
  .info-item .value {{ color: #e2e8f0; font-weight: 500; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; color: #94a3b8; padding: 10px; border-bottom: 1px solid #334155; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }}
  td {{ padding: 10px; border-bottom: 1px solid #1e293b; vertical-align: top; }}
  td.reasoning {{ color: #94a3b8; font-style: italic; max-width: 320px; }}
  .footer {{ text-align: center; padding: 30px; color: #475569; font-size: 13px; border-top: 1px solid #1e293b; margin-top: 20px; }}
</style>
</head>
<body>

<div class="header">
  <h1>🧑‍⚖️ Emerson Enterprise AI — LLM-as-a-Judge Evaluation Report</h1>
  <h2>Model-graded RAG quality assessment (complements keyword-overlap scoring)</h2>
  <div class="meta">
    <div class="meta-item"><span>Evaluation Date</span><strong>{datetime.now().strftime('%d %B %Y, %H:%M')}</strong></div>
    <div class="meta-item"><span>Questions Scored</span><strong>{summary['scored_questions']}/{summary['total_questions']}</strong></div>
    <div class="meta-item"><span>Judge Model</span><strong>{summary['judge_model']}</strong></div>
    <div class="meta-item"><span>Answer Generator</span><strong>LLaMA 3.3 70B (Groq)</strong></div>
  </div>
</div>

<div class="container">

  <div style="margin-bottom:30px; margin-top:10px;">
    <div class="section-title">Overall Performance</div>
    <div class="overall">
      <div class="overall-left">
        <h3>Overall Judge Score</h3>
        <p>Average across five model-graded metrics: Faithfulness, Answer Relevancy, Context Precision,
        Context Recall, and Correctness vs. ground truth. Score above 0.75 indicates production-ready quality.</p>
      </div>
      <div class="overall-score">{overall:.2f}</div>
    </div>
  </div>

  <div class="section-title">Metric Breakdown</div>
  <div class="cards">
    {cards_html}
  </div>

  <div class="info-box">
    <h3>👥 Per-Role Scores</h3>
    <div class="info-grid">
      {role_rows}
    </div>
  </div>

  <div class="info-box">
    <h3>🔻 Lowest-Scoring Answers (Review Candidates)</h3>
    <table>
      <thead><tr><th>#</th><th>Role</th><th>Question</th><th>Score</th><th>Judge Reasoning</th></tr></thead>
      <tbody>
        {worst_rows}
      </tbody>
    </table>
  </div>

  <div class="info-box">
    <h3>📋 Evaluation Configuration</h3>
    <div class="info-grid">
      <div class="info-item"><div class="label">Framework</div><div class="value">LLM-as-a-Judge (Groq)</div></div>
      <div class="info-item"><div class="label">Failed Judge Calls</div><div class="value">{summary['failed_questions']}</div></div>
      <div class="info-item"><div class="label">Scoring Method</div><div class="value">{summary['scoring_method']}</div></div>
      <div class="info-item"><div class="label">Roles Tested</div><div class="value">HR, Finance, Engineering, Marketing, Admin</div></div>
    </div>
  </div>

</div>

<div class="footer">
  LLM-as-a-Judge evaluation — complements the keyword-overlap RAG evaluation (evaluate_rag.py).<br>
  Compare reports/rag_eval_report_*.html against this report to sanity-check both scoring methods.
</div>

</body>
</html>"""
    return html


def main():
    print("📊 Generating LLM-as-a-Judge HTML report...")
    data, source_file = load_latest_results()
    print(f"   Loaded results from: {source_file}")

    html = generate_html(data)

    Path("reports").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"reports/llm_judge_report_{timestamp}.html"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ HTML report saved: {out_path}")


if __name__ == "__main__":
    main()
