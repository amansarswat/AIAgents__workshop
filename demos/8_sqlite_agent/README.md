# Demo 8 — A Real Tool: agent over a real SQLite database

**Act 2 — Production depth.** *Needs Azure.*
**Agent type:** the agent touches something **real** — a real `sqlite3` file, real SQL, a persisted write.

## The one idea
> The moment an agent can touch a datastore, guardrails move to the **tool boundary**:
> read-only reads, and writes only through narrow, typed tools.

## What it shows live
- A raw agent loop (no framework) discovers the schema (`list_tables`/`describe_table`),
  composes its own `SELECT`, and answers an analytics question over a **real** `shop.db`.
- It then performs a **write** — but only via `record_refund(order_id, reason)`, a narrow,
  parameterised tool. There is no "run arbitrary SQL write" tool.
- A final **verification line reads the DB directly** to prove the write persisted (not the
  model's claim). Open `shop.db` in any SQLite browser afterwards to see it.

## Guardrails
- `run_select` permits exactly one read-only `SELECT` — no DDL/DML, no `;` statement stacking.
- The model chooses *what* to refund; your code owns *how* the write happens → `DROP TABLE` is
  impossible by construction.

## Run
```bash
python demos/8_sqlite_agent/sqlite_agent.py
DEMO_QUESTION="Who is the top-spending customer and what did they buy?" python ...
```

## Talking points
- "This isn't a toy" — the change is on disk after the run.
- Narrow typed write tools + a read-only guard are how you let an agent near real data safely.
