# Agentic AI Masterclass (2 hours)

A hands-on, **watch-along** masterclass on the *types* of AI agents and where each
one fits — built from [ed-donner/agents](https://github.com/ed-donner/agents)
("The Complete Agentic AI Engineering Course") and **adapted to run on Azure OpenAI**.

**One business objective, solved three ways.** Every demo is a step in running one company —
*Orbit, a subscription e-commerce SaaS* — decomposed across the three levels of automation:
**Workflows** (you own the steps) → **AI Agents** (one LLM + tools) → **Agentic AI** (autonomous,
multi-agent, stateful). The Overview tab of the UI (`python app.py`) shows the complete flow as a
single map, and each demo tab is badged with the Orbit step it performs.

It also runs in two acts. **Act 1 — Foundations** teaches *what the categories are*. **Act 2 —
Production depth** teaches *how to build one that survives contact with production* (for an
audience that's seen the demos and asked "yes, but what happens when it **fails**?").

**Act 1 — Foundations**

| # | Demo | Agent type | Framework | Needs |
|---|------|-----------|-----------|-------|
| 1 | [The Agent Loop](demos/1_agent_loop/) | The raw pattern under everything | *none* (OpenAI SDK) | Azure only |
| 1b | [Native & Hybrid Agents](demos/5_native_agents/) | Deterministic (no-AI) + cost-saving hybrid | *plain Python* | 5a: nothing · 5b: Azure |
| 2 | [Sales Team](demos/2_openai_agents_sdk/) | Code-first multi-agent + handoffs | OpenAI Agents SDK | Azure only |
| 3 | [Debate Crew](demos/3_crewai_debate/) | Declarative role-based crew | CrewAI | Azure only* |
| 4 | [MCP Trading](demos/4_mcp_trading/) | Agent + reusable tool servers | MCP + Agents SDK | Azure only |

**Act 2 — Production depth**

| # | Demo | What it proves | Stack | Needs |
|---|------|----------------|-------|-------|
| 6 | [Resilient Agent](demos/6_resilient_agent/) | tool fails → retry/backoff → fail over → escalate (in code, not the model) | plain Python | nothing |
| 7 | [Eval & Trace](demos/7_eval_trace/) | trace every run + score vs gold labels (deterministic + LLM-as-judge) | OpenAI SDK | Azure only |
| 8 | [Real SQLite Agent](demos/8_sqlite_agent/) | a real DB on disk; read-only guard + narrow typed write tool | OpenAI SDK + `sqlite3` | Azure only |
| 9 | [LangGraph Workflow](demos/9_langgraph_workflow/) | stateful graph: retry-until-criteria + a human approval gate | LangGraph | Azure only |
| 10 | [Failure Modes](demos/10_failure_modes/) | cost blowup · infinite loop · prompt injection — each guard engages | OpenAI SDK | Azure only |

**★ Flagship & bonus**

| # | Demo | What it proves | Stack | Needs |
|---|------|----------------|-------|-------|
| 11 | [SWE Agent](demos/11_swe_agent/) | autonomous agent fixes a real bug; success is `pytest` exit-0, verified by the harness (frozen tests, sandboxed) | OpenAI SDK + pytest | Azure only |
| 12 | [Model Router](demos/12_model_router/) | route each request to the cheapest capable model — cheap for easy, frontier for hard | LiteLLM | Azure only |

> 💡 **Demo 1b (`demos/5_native_agents/`)** makes the point that *agentic ≠ AI-dependent*:
> the agent loop runs fine on plain deterministic code at **$0/decision**, and a
> *native-first hybrid* escalates to the LLM only for the hard cases to keep cost in check.
>
> 🔧 **Act 2 is the senior track.** Demos 6 & 10 carry deterministic guards (retry, budget,
> cycle detector, allowlist); Demo 8 writes a real `sqlite3` file you can open afterwards;
> Demo 9 truly pauses the graph for a human and resumes from a checkpoint.

\* CrewAI has a heavier install on Windows — see [SETUP.md](SETUP.md).

Every demo runs on **just your Azure OpenAI key** — no SendGrid, Polygon, Serper,
Brave, or Pushover accounts required.

> ✅ **Verified:** all demos were run end-to-end against the Azure deployment
> `gpt-4o-mini` (API version `2024-10-21`) and produced correct output (Demo 5a runs
> with no API at all). See the per-demo READMEs for what each one prints.

## What's in this repo
```
agentic-ai-masterclass/
├── README.md                             ← you are here (index)
├── SETUP.md                              ← environment setup + troubleshooting
├── PARTICIPANT_HANDOUT.md                ← concepts, cheat-sheets, "when to use which", glossary, links
├── Understanding-Agentic-AI-Explainer.md ← plain-language primer (Workflow · Agent · Agentic AI · MCP · LangGraph)
├── app.py                                ← interactive UI (Gradio): every demo on one self-explanatory page
├── smoke_test.py                         ← confirm Azure connectivity
├── requirements.txt  ·  .env.example  ·  .gitignore
└── demos/                                ← runnable demos (Act 1–2 demos each have a README)
    │  # Act 1 — Foundations
    ├── 1_agent_loop/           raw LLM agent loop
    ├── 5_native_agents/        Demo 1b — native ($0) + hybrid cost-control
    ├── 2_openai_agents_sdk/    OpenAI Agents SDK (tools, handoffs)
    ├── 3_crewai_debate/        CrewAI declarative crew
    ├── 4_mcp_trading/          MCP — your own tool server
    │  # Act 2 — Production depth
    ├── 6_resilient_agent/      retry / failover / escalation around a flaky tool
    ├── 7_eval_trace/           eval harness: trace + score vs gold labels
    ├── 8_sqlite_agent/         agent over a REAL sqlite3 DB (read guard + write tool)
    ├── 9_langgraph_workflow/   LangGraph state machine + human-in-the-loop gate
    ├── 10_failure_modes/       cost blowup · infinite loop · prompt injection + guards
    │  # ★ Flagship & bonus
    ├── 11_swe_agent/           autonomous SWE agent — fixes a real bug, verified by pytest
    └── 12_model_router/        LiteLLM cost router — cheap model for easy, frontier for hard
```

> `.venv/` and `source-course/` live on the presenter's machine but are **git-ignored — not in this repo**. Create the virtual env with the [Quick start](#quick-start) below; clone the source course separately from [ed-donner/agents](https://github.com/ed-donner/agents).

## The deliverables
- **[SETUP.md](SETUP.md)** — get the environment working before the session.
- **[PARTICIPANT_HANDOUT.md](PARTICIPANT_HANDOUT.md)** — concepts, framework cheat-sheets, "when to use which", glossary, links.
- **[Understanding-Agentic-AI-Explainer.md](Understanding-Agentic-AI-Explainer.md)** — a plain-language primer on Workflow · AI Agent · Agentic AI · MCP · LangGraph (also shown on the app's Overview tab).
- **[demos/](demos/)** — twelve runnable demos (Azure-ready; Demos 5a and 6 need no API at all); the Act 1–2 demos each include a README.
- **Source course** — this pack is built from [ed-donner/agents](https://github.com/ed-donner/agents) ("The Complete Agentic AI Engineering Course"). Clone it separately for deeper reference (LangGraph, AutoGen, capstones, etc.).

## Quick start
```bash
cd agentic-ai-masterclass
python -m venv .venv
.venv\Scripts\activate            # Windows;  source .venv/bin/activate on mac/linux
pip install -r requirements.txt
cp .env.example .env              # then paste your ROTATED Azure key into .env
python smoke_test.py              # should print "Azure OK"
python demos/1_agent_loop/agent_loop.py
```

## 🖥️ Interactive UI (recommended for the live session)
Prefer one console over six terminal commands? Launch the web app:
```bash
python app.py                     # opens http://127.0.0.1:7860 in your browser
```
It's a working control panel, not a slideshow. Each demo tab presents the demo as a real
system you can reason about and drive:
- a rendered **architecture diagram** (the layers + the data flow, via Mermaid),
- the named **layers** and what each one owns,
- an **Input → Expected-output contract** so you know what you're about to see,
- **editable inputs** — you supply the goal / server state / incident / motion / trade and re-run,
- the **source code**, and a **▶ Run** button that streams the real script verbatim.

The demo scripts are unchanged in behaviour; the UI feeds your inputs in through environment
variables (each script keeps its original default) and runs the script as a subprocess of the
same Python — so what you read is exactly what executes. The **Overview** tab has the core
idea, the universal agent-loop diagram, a "when to use which" guide, and a one-click Azure
connectivity check. (Demo 1b-a runs with no key; the rest use your Azure `.env`.)

## ⚠️ Security note
This pack was built after some live Azure keys were shared in chat. **Rotate those
keys** in the Azure portal before the session and put only the new key in `.env`
(which is git-ignored). Never commit secrets.

## Bonus material
The handout also summarises **LangGraph** (graph/state-machine agents — see Demo 9) and
**Microsoft AutoGen** (conversational multi-agent teams) — two more frameworks from the
broader course — so you can extend the class to a longer format later.
