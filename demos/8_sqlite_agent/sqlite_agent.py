"""
DEMO 8 — A REAL TOOL: an agent over a REAL SQLite database
==========================================================
Every other demo simulates the outside world (fixed prices, a JSON file, a stubbed
email). This one does not. The agent reads and WRITES a real `sqlite3` database file
on disk, runs real SQL it composed itself, and the change persists. Delete the file
and it rebuilds; open it in any SQLite browser and you'll see the agent's refund.

It also shows the guardrails a senior expects the moment an agent can touch a real
data store:
  • READ path  — `run_select` executes model-generated SQL, but is hard-restricted to a
    single read-only SELECT (no INSERT/UPDATE/DELETE/DROP/PRAGMA, no statement stacking).
  • WRITE path — there is NO "run arbitrary SQL write" tool. The only mutation is
    `record_refund(order_id, reason)`, a narrow, typed, parameterised tool. The model
    chooses *what* to refund; it cannot choose *how* the write is done. That separation
    is what keeps "DROP TABLE orders" off the table — literally.

The agent loop is the raw one from Demo 1 (no framework) so the tool calls are visible.

Run:  python demos/8_sqlite_agent/sqlite_agent.py     (needs your Azure .env)
"""

import os
import re
import sys
import json
import sqlite3
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
from openai import AzureOpenAI

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
load_dotenv(ROOT / ".env")

client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
)
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
DB_PATH = HERE / "shop.db"


# =====================================================================
# REAL DATABASE — seeded deterministically so the answers are checkable.
# =====================================================================
def build_db() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    con.executescript(
        """
        CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL);
        CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, product_id INTEGER,
                             qty INTEGER, status TEXT, created_at TEXT);
        INSERT INTO products VALUES (1,'Widget',9.99),(2,'Gadget',24.99),(3,'Gizmo',99.99),(4,'Doohickey',4.99);
        INSERT INTO customers VALUES (1,'Alice'),(2,'Bob'),(3,'Carol');
        INSERT INTO orders VALUES
            (1001,1,3,2,'shipped','2026-05-02'),
            (1002,2,2,5,'shipped','2026-05-09'),
            (1003,1,3,1,'shipped','2026-05-15'),
            (1004,3,1,10,'shipped','2026-05-18'),
            (1005,2,3,1,'delivered','2026-05-21'),
            (1006,3,2,2,'delivered','2026-05-25'),
            (1007,1,4,20,'delivered','2026-05-29');
        """
    )
    con.commit()
    con.close()


# =====================================================================
# TOOLS — read is guarded; write is narrow + parameterised.
# =====================================================================
_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|attach|pragma|vacuum)\b", re.I)


def list_tables() -> str:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    con.close()
    return json.dumps([r[0] for r in rows])


def describe_table(table: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table or ""):
        return "ERROR: invalid table name."
    con = sqlite3.connect(DB_PATH)
    try:
        cols = con.execute(f"PRAGMA table_info({table})").fetchall()
    finally:
        con.close()
    if not cols:
        return f"ERROR: no such table {table}."
    return json.dumps([{"name": c[1], "type": c[2]} for c in cols])


def run_select(sql: str) -> str:
    """Execute ONE read-only SELECT. Anything else is refused — this is the guardrail."""
    s = (sql or "").strip().rstrip(";").strip()
    if ";" in s:
        return "ERROR: only a single statement is allowed (no ';' stacking)."
    if not re.match(r"^(select|with)\b", s, re.I):
        return "ERROR: only SELECT queries are allowed on this tool."
    if _FORBIDDEN.search(s):
        return "ERROR: write/DDL keywords are not allowed on the read tool."
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(s).fetchmany(50)
        return json.dumps([dict(r) for r in rows])
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        con.close()


def record_refund(order_id: int, reason: str) -> str:
    """The ONLY write. Typed + parameterised; the model can't express it as raw SQL."""
    con = sqlite3.connect(DB_PATH)
    try:
        row = con.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            return f"ERROR: order {order_id} does not exist."
        con.execute("UPDATE orders SET status = 'refunded' WHERE id = ?", (order_id,))
        con.commit()
        new = con.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()[0]
        return json.dumps({"order_id": order_id, "was": row[0], "now": new, "reason": reason})
    finally:
        con.close()


TOOL_FUNCS = {"list_tables": list_tables, "describe_table": describe_table,
              "run_select": run_select, "record_refund": record_refund}

TOOLS = [
    {"type": "function", "function": {"name": "list_tables",
        "description": "List the tables in the database.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "describe_table",
        "description": "Get the columns and types of a table.",
        "parameters": {"type": "object", "properties": {"table": {"type": "string"}},
                       "required": ["table"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "run_select",
        "description": "Run ONE read-only SELECT query and get rows back as JSON.",
        "parameters": {"type": "object", "properties": {"sql": {"type": "string"}},
                       "required": ["sql"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "record_refund",
        "description": "Refund an order by id (sets its status to 'refunded'). Use only when the user asks to refund a specific order.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "integer"}, "reason": {"type": "string"}},
            "required": ["order_id", "reason"], "additionalProperties": False}}},
]


def run_agent(question: str, max_turns: int = 12) -> str:
    system = (
        "You are a data analyst with access to a SQLite shop database via tools. "
        "Discover the schema if needed (list_tables / describe_table), then answer using "
        "run_select. Use record_refund ONLY when explicitly asked to refund a specific order. "
        "When done, give a short plain-English answer with the numbers."
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    for turn in range(1, max_turns + 1):
        resp = client.chat.completions.create(model=DEPLOYMENT, messages=messages, tools=TOOLS, temperature=0)
        choice = resp.choices[0]
        if choice.finish_reason != "tool_calls":
            print(f"\n─── turn {turn}: agent is DONE ───")
            return choice.message.content
        print(f"\n─── turn {turn}: tool call(s) ───")
        messages.append(choice.message)
        for call in choice.message.tool_calls:
            args = json.loads(call.function.arguments)
            preview = args.get("sql") or args.get("table") or (f"order {args.get('order_id')}" if "order_id" in args else "")
            print(f"   🔧 {call.function.name}({preview})")
            result = TOOL_FUNCS[call.function.name](**args)
            print(f"      → {result[:160]}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})
    return "(stopped: hit max turns)"


if __name__ == "__main__":
    build_db()
    question = os.getenv("DEMO_QUESTION") or (
        "Which product has the highest total revenue (price*qty), and how many orders "
        "included it? Then refund order 1003 because the customer reports it never arrived."
    )
    print(f"Model deployment: {DEPLOYMENT}")
    print(f"Real DB file    : {DB_PATH}")
    print(f"QUESTION        : {question}")
    answer = run_agent(question)
    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(answer)

    # Prove the write actually hit the real database (independent of the agent's claim).
    con = sqlite3.connect(DB_PATH)
    status = con.execute("SELECT status FROM orders WHERE id = 1003").fetchone()
    con.close()
    print(f"\n[verification] orders.status for 1003 in the real DB is now: '{status[0]}'")
