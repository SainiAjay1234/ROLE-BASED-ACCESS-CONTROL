"""
SQL Agent: answers structured/tabular queries using DuckDB + Groq.
Falls back to RAG if SQL fails.
"""

import os
import duckdb
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Sample in-memory data
SAMPLE_HR_DATA = pd.DataFrame({
    "employee_id": [1001, 1002, 1003, 1004, 1005],
    "name": ["Alice Smith", "Bob Jones", "Carol White", "Dan Brown", "Eve Black"],
    "department": ["HR", "Finance", "Engineering", "Marketing", "HR"],
    "salary": [75000, 90000, 110000, 80000, 72000],
    "location": ["Noida", "Mumbai", "Bangalore", "Delhi", "Noida"],
    "years_exp": [5, 8, 12, 4, 3],
})

SAMPLE_FINANCE_DATA = pd.DataFrame({
    "quarter": ["Q1", "Q2", "Q3", "Q4"],
    "revenue": [12500000, 13800000, 14200000, 15100000],
    "expenses": [9800000, 10200000, 10500000, 11000000],
    "profit": [2700000, 3600000, 3700000, 4100000],
})


def _nl_to_sql(query: str, schema: str) -> str:
    prompt = f"""Convert this natural language question to a DuckDB SQL query.
Available tables and their schemas:
{schema}

Question: {query}

Return ONLY the SQL query, no explanation, no markdown, no backticks.
SQL:"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=256,
    )
    return response.choices[0].message.content.strip().rstrip(";")


def run_sql_agent(query: str, role: str) -> tuple[str, bool]:
    """
    Runs NL→SQL→DuckDB pipeline.
    Returns (answer_string, success_bool).
    """
    conn = duckdb.connect(":memory:")
    schema_parts = []

    if role in ("hr", "admin"):
        conn.register("employees", SAMPLE_HR_DATA)
        schema_parts.append(
            "employees(employee_id INT, name VARCHAR, department VARCHAR, "
            "salary INT, location VARCHAR, years_exp INT)"
        )
    if role in ("finance", "admin"):
        conn.register("financials", SAMPLE_FINANCE_DATA)
        schema_parts.append(
            "financials(quarter VARCHAR, revenue BIGINT, expenses BIGINT, profit BIGINT)"
        )

    if not schema_parts:
        return "You do not have access to structured data tables.", False

    schema = "\n".join(schema_parts)

    try:
        sql = _nl_to_sql(query, schema)
        result = conn.execute(sql).df()
        if result.empty:
            return "No records found matching your query.", True
        return result.to_markdown(index=False), True
    except Exception as e:
        return f"SQL execution failed: {e}", False
