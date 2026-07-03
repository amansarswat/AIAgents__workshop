"""
Agentic AI Masterclass — interactive control panel
==================================================
A working console for the session, not a slideshow. Every demo is presented as a
real system you can reason about and drive:

  • an ARCHITECTURE diagram (the layers + the data flow), rendered live with Mermaid,
  • the named LAYERS and what each one owns,
  • an INPUT → EXPECTED-OUTPUT contract (so you know what you're about to see),
  • EDITABLE inputs (you supply the goal / motion / incident / trade and re-run),
  • the real script streamed verbatim — the architecture above is exactly what runs.

The demo scripts under demos/ are unchanged in behaviour; the UI feeds your inputs in
through environment variables (each script keeps its original default) and runs the
script as a subprocess of THIS Python, so what you read is what executes.

Run:
    python app.py        # opens http://127.0.0.1:7860
"""

import os
import re
import sys
import subprocess
from pathlib import Path

from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import gradio as gr
except ModuleNotFoundError:
    sys.exit(
        "Gradio isn't installed in this environment.\n"
        "Install it with:  pip install -r requirements.txt   (or: pip install gradio)\n"
        "and run this app with the SAME Python (your .venv)."
    )

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


# =====================================================================
# Mermaid: render the architecture diagrams in the browser.
# Injected into <head>; a MutationObserver + interval re-renders any diagram
# that Gradio adds when you switch tabs (tabs render lazily).
# =====================================================================
MERMAID_HEAD = """
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose',
                       flowchart: { useMaxWidth: true, htmlLabels: true } });
  const run = () => { try { mermaid.run({ querySelector: '.mermaid:not([data-processed])' }); } catch (e) {} };
  const obs = new MutationObserver(run);
  window.addEventListener('load', () => { obs.observe(document.body, { childList: true, subtree: true }); run(); });
  setInterval(run, 600);
</script>
"""

CSS = """
.arch-card { background:#ffffff; border:1px solid #e5e7eb; border-radius:12px;
             padding:16px; margin:8px 0 4px 0; overflow-x:auto; }
.arch-card .mermaid { display:flex; justify-content:center; min-height:40px; }
.contract { background:#f8fafc; border-left:4px solid #2563eb; border-radius:6px;
            padding:10px 14px; }
footer { display:none !important; }
"""


def mermaid(src: str) -> str:
    return f'<div class="arch-card"><pre class="mermaid">\n{src.strip()}\n</pre></div>'


# =====================================================================
# DEMO REGISTRY — single source of truth for every tab.
# =====================================================================
DEMOS = [
    {
        "id": "1",
        "tab": "1 · Agent Loop",
        "title": "Demo 1 — The Agent Loop",
        "agent_type": "The raw pattern under everything",
        "framework": "None — OpenAI SDK + a `while` loop (~120 lines)",
        "needs_azure": True,
        "cost": "A few gpt-4o-mini calls (fractions of a cent)",
        "runtime": "~10–20 s",
        "script": "demos/1_agent_loop/agent_loop.py",
        "teaches": (
            "Orbit's first job is to plan its own launch. Give the agent that goal and you see the "
            "pattern under everything: **an LLM in a loop, with tools, that decides for itself when "
            "it's done.** Every later tab is ergonomics over this exact loop."
        ),
        "architecture": """
flowchart TD
    IN["🧑 User goal — INPUT"] --> MSGS["messages[]  (system + user + tool results)"]
    MSGS --> LLM{{"LLM · Azure gpt-4o-mini<br/>decides the next action"}}
    LLM -->|"finish_reason = tool_calls"| DISP["Tool dispatch<br/>add_todos · complete_todo"]
    DISP --> STATE[("todos state")]
    STATE -->|"append result, loop"| MSGS
    LLM -->|"finish_reason = stop"| OUT["✅ Final answer + completed PLAN — OUTPUT"]
    classDef llm fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef tool fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class LLM llm;
    class DISP,STATE tool;
    class IN,OUT io;
""",
        "layers": [
            "**Input layer** — the goal + system prompt assembled into `messages[]`.",
            "**Decision layer** — the LLM chooses the next tool call, or decides to stop.",
            "**Orchestration layer** — the `while` loop: it reads `finish_reason`, runs the requested tools, and appends results.",
            "**Tool layer** — plain Python functions (`add_todos`, `complete_todo`) exposed to the model as JSON schemas.",
            "**State layer** — the `todos` list, mutated by tools and fed back every turn.",
        ],
        "contract": (
            "**Input** → a free-form goal.  \n"
            "**Output** → a turn-by-turn trace (`LLM turn N` → the tool calls it chose), then a "
            "**FINAL ANSWER** and a **PLAN** with every step checked `[x]`.  \n"
            "**Try this** → give it a vague goal, then a precise one, and watch the number of "
            "planning steps change. *You never tell it how many steps to take.*"
        ),
        "watch": "Each `─── LLM turn N ───` is one trip around the loop: it plans (`add_todos`), executes (`complete_todo` ×N), then stops on its own.",
        "when": "Learning the mechanism; total control; minimal deps; tasks where the number of steps isn't known up front.",
        "inputs": [
            {"kind": "textarea", "env": "DEMO_GOAL", "label": "Goal — the agent plans and executes this", "lines": 3,
             "value": "Plan Orbit's go-to-market launch: how a small team should take our new subscription e-commerce product to market. Work through the plan and give a recommendation."},
        ],
    },
    {
        "id": "5a",
        "tab": "1b · Native ($0)",
        "title": "Demo 1b-a — Native Agent (no AI)",
        "agent_type": "Deterministic agent — the brain is plain code, no LLM",
        "framework": "Plain Python (a rule cascade)",
        "needs_azure": False,
        "cost": "$0.00 — zero tokens, no API key",
        "runtime": "instant",
        "script": "demos/5_native_agents/native_agent.py",
        "teaches": (
            "Keeping Orbit's servers healthy is a solved problem — a runbook, not a reasoning task. So "
            "the brain here is **deterministic rules, not an LLM**: the same agent loop as Demo 1, but "
            "instant, 100% reproducible, unit-testable, and free. *Agentic ≠ AI-dependent.*"
        ),
        "architecture": """
flowchart TD
    IN["🖥️ Server metrics — INPUT"] --> PERCEIVE["perceive: read state"]
    PERCEIVE --> DECIDE{{"decide() · RULE CASCADE<br/>NO LLM · $0 · µs"}}
    DECIDE -->|"action"| ACT["act: restart · clear_logs · scale_out · rollback"]
    ACT --> OBS["observe: new metrics"]
    OBS -->|"still unhealthy → loop"| PERCEIVE
    DECIDE -->|"DONE (healthy)"| OUT["✅ Healthy + COST REPORT $0.00 — OUTPUT"]
    classDef brain fill:#fef9c3,stroke:#ca8a04,color:#713f12;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class DECIDE brain;
    class IN,OUT io;
""",
        "layers": [
            "**Input layer** — the perceived `Server` state (cpu/mem/disk/error/up).",
            "**Decision layer** — `decide()`: a priority-ordered rule cascade. **No model, no tokens.**",
            "**Action layer** — the remediation tools that mutate the simulated server.",
            "**Orchestration layer** — the same perceive→decide→act→observe loop as Demo 1.",
            "**Output layer** — a healthy server and a `COST REPORT` proving $0.00.",
        ],
        "contract": (
            "**Input** → an initial server state.  \n"
            "**Output** → one fix per turn until healthy, then `COST REPORT: 0 calls · $0.00`.  \n"
            "**Try this** → set only **Disk = 97** (everything else healthy, service up) → it takes "
            "exactly one action. Set everything bad → watch it triage worst-first. Same input → "
            "same trace, every run."
        ),
        "watch": "The `decide()` brain is a rule cascade; metrics improve each turn; the COST REPORT reads `LLM API calls: 0 · Tokens: 0 · Cost: $0.00`.",
        "when": "Any decision that's deterministic or matches a known playbook. The cheapest, fastest, most reliable agent.",
        "inputs": [
            {"kind": "number", "env": "DEMO_CPU", "label": "CPU %", "value": 95},
            {"kind": "number", "env": "DEMO_MEM", "label": "Memory %", "value": 88},
            {"kind": "number", "env": "DEMO_DISK", "label": "Disk %", "value": 93},
            {"kind": "number", "env": "DEMO_ERR", "label": "Error rate %", "value": 7.0},
            {"kind": "bool", "env": "DEMO_SERVICE_UP", "label": "Service up?", "value": False},
        ],
    },
    {
        "id": "5b",
        "tab": "1b · Hybrid (cost)",
        "title": "Demo 1b-b — Hybrid Agent (cost control)",
        "agent_type": "Native-first, escalate to the LLM only when stuck",
        "framework": "Plain Python rules + OpenAI SDK (escalation only)",
        "needs_azure": True,
        "cost": "Only the novel incidents hit Azure; the rest are free",
        "runtime": "~10–20 s",
        "script": "demos/5_native_agents/hybrid_agent.py",
        "teaches": (
            "Orbit's on-call gets a stream of incidents, and ~90% match a known playbook. Handle those "
            "with **free, instant rules** and escalate only the rare novel case to the LLM. "
            "*Don't pay a model to make a decision a rule already knows.*"
        ),
        "architecture": """
flowchart TD
    IN["🚨 Incident stream — INPUT"] --> ROUTER{"Known alert type?<br/>(router)"}
    ROUTER -->|"yes · ~90%"| RULE["Native RULES playbook<br/>$0 · instant"]
    ROUTER -->|"no · novel"| LLM{{"LLM · Azure<br/>reason out ONE action"}}
    RULE --> METER["Cost meter (free vs paid)"]
    LLM --> METER
    METER --> OUT["✅ Actions + savings % — OUTPUT"]
    classDef brain fill:#fef9c3,stroke:#ca8a04,color:#713f12;
    classDef llm fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class RULE brain;
    class LLM llm;
    class IN,OUT io;
""",
        "layers": [
            "**Input layer** — a stream of `(alert_type, description)` incidents.",
            "**Routing layer** — is the alert type in the `RULES` playbook?",
            "**Native path** — a dictionary lookup. $0, instant, deterministic.",
            "**Escalation path** — only unknown alerts call Azure to reason out one action.",
            "**Accounting layer** — a cost meter tallying free vs. paid decisions and the savings %.",
        ],
        "contract": (
            "**Input** → a fixed incident stream (plus, optionally, your own novel incident).  \n"
            "**Output** → `[RULE  $0.00]` vs `[LLM  ~paid]` per incident, then a **COST METER** with "
            "the savings %.  \n"
            "**Try this** → add a weird incident no rule covers (below) → it routes to the LLM and "
            "you see the exact tokens it adds."
        ),
        "watch": "`[RULE $0.00]` = free native decision; `[LLM ~paid]` = escalation. In the reference run, 10 of 12 were free (~83% fewer LLM calls).",
        "when": "Production systems where an 'LLM-for-everything' design would explode the bill. Rule for the known 90%, model for the long tail.",
        "inputs": [
            {"kind": "textarea", "env": "DEMO_EXTRA_INCIDENT",
             "label": "Add your own NOVEL incident (optional → forces an LLM escalation)", "lines": 2,
             "value": "",
             "placeholder": "e.g. Mobile users see a blank cart after the 14:30 deploy; desktop unaffected; CPU/mem/disk all normal."},
        ],
    },
    {
        "id": "2",
        "tab": "2 · Agents SDK",
        "title": "Demo 2 — OpenAI Agents SDK (sales team)",
        "agent_type": "Code-first multi-agent: tools, agents-as-tools, handoffs",
        "framework": "OpenAI Agents SDK",
        "needs_azure": True,
        "cost": "Several gpt-4o-mini calls (a few cents)",
        "runtime": "~20–40 s",
        "script": "demos/2_openai_agents_sdk/sales_team.py",
        "teaches": (
            "Orbit's outreach team in ~80 lines, showing three production concepts: **tools**, "
            "**agents-as-tools** (wrap an agent as a callable), and **handoffs** (transfer the whole "
            "conversation). A sales manager delegates to three SDR agents, picks the best cold-email "
            "draft, then hands off to an emailer that sends it."
        ),
        "architecture": """
flowchart TD
    IN["🧑 Sales brief — INPUT"] --> MGR{{"Sales Manager agent"}}
    MGR -->|"agent-as-tool"| SDR1["professional_sdr"]
    MGR -->|"agent-as-tool"| SDR2["witty_sdr"]
    MGR -->|"agent-as-tool"| SDR3["concise_sdr"]
    SDR1 -->|"draft"| MGR
    SDR2 -->|"draft"| MGR
    SDR3 -->|"draft"| MGR
    MGR -->|"HANDOFF — transfers control"| EM{{"Emailer agent"}}
    EM -->|"function_tool"| SEND["send_email()"]
    SEND --> OUT["✅ sent_email.txt + confirmation — OUTPUT"]
    classDef agent fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef tool fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class MGR,EM,SDR1,SDR2,SDR3 agent;
    class SEND tool;
    class IN,OUT io;
""",
        "layers": [
            "**Orchestration layer** — the Sales Manager agent; it never writes copy itself.",
            "**Specialist layer** — three SDR agents exposed as tools (`agent-as-tool`); a tool returns control to the caller.",
            "**Handoff** — the manager transfers the conversation to the Emailer; a handoff transfers control *away*.",
            "**Tool layer** — `send_email()` (a real `@function_tool`, stubbed to write a file).",
            "**Model layer** — one Azure adapter (`AsyncAzureOpenAI` → `OpenAIChatCompletionsModel`) reused by every agent.",
        ],
        "contract": (
            "**Input** → a sales brief.  \n"
            "**Output** → 3 SDR drafts → manager picks one → **handoff** to the emailer → "
            "`send_email()` writes `sent_email.txt` and prints **📧 EMAIL SENT**.  \n"
            "**Try this** → change the prospect / industry and watch all three writing styles adapt."
        ),
        "watch": "Manager calls all three SDR tools, picks a winner, hands off; the emailer writes a subject and sends. *Tool = control returns; handoff = control transfers.*",
        "when": "Production multi-agent, code-first, when you want full control plus handoffs, guardrails, and structured outputs.",
        "inputs": [
            {"kind": "textarea", "env": "DEMO_TASK", "label": "Sales brief for the manager", "lines": 2,
             "value": "Generate and send a cold sales email to the Head of E-commerce at a mid-size retailer."},
        ],
    },
    {
        "id": "3",
        "tab": "3 · CrewAI",
        "title": "Demo 3 — CrewAI (debate crew)",
        "agent_type": "Declarative role-based crew",
        "framework": "CrewAI (routed to Azure via LiteLLM)",
        "needs_azure": True,
        "cost": "Several calls; the longest-running demo",
        "runtime": "~60–120 s",
        "script": "demos/3_crewai_debate/debate.py",
        "teaches": (
            "Orbit's leadership needs to make a strategy call. Instead of coding the orchestration, you "
            "**declare a cast** (role / goal / backstory) and a list of tasks, and CrewAI runs them: a "
            "debater argues both sides of the motion and a judge decides."
        ),
        "architecture": """
flowchart TD
    IN["📜 Motion — INPUT"] --> CREW["Crew · Process.sequential"]
    CREW --> T1["Task 1 · PROPOSE<br/>agent: debater"]
    T1 -->|"output is context"| T2["Task 2 · OPPOSE<br/>agent: debater"]
    T2 -->|"output is context"| T3["Task 3 · DECIDE<br/>agent: judge"]
    T3 --> OUT["✅ JUDGE'S VERDICT — OUTPUT"]
    CREW -.->|"LiteLLM"| AZ[("azure/gpt-4o-mini")]
    classDef crew fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef az fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class CREW,T1,T2,T3 crew;
    class AZ az;
    class IN,OUT io;
""",
        "layers": [
            "**Declaration layer** — agents defined by role / goal / backstory (personas, not steps).",
            "**Task layer** — three tasks (propose → oppose → decide); each task's output becomes context for the next.",
            "**Process layer** — `Process.sequential` runs the tasks in order (vs. `hierarchical`, where a manager delegates).",
            "**Model layer** — CrewAI talks to Azure through LiteLLM (`azure/<deployment>`); each agent could use a different model.",
            "**Output layer** — the judge's final verdict.",
        ],
        "contract": (
            "**Input** → a debate motion.  \n"
            "**Output** → the debater argues FOR, then AGAINST, then the judge returns a **VERDICT** "
            "with justification (after verbose 'thinking' logs).  \n"
            "**Try this** → swap in a motion from your own domain. The personas stay fixed; only the "
            "content changes — that's the declarative trade-off."
        ),
        "watch": "Verbose logs show each agent reasoning in character; tasks run in order; ends with a JUDGE'S VERDICT block. *You declared roles; the framework orchestrated.*",
        "when": "Expressing 'a team of role-playing specialists' fast — research crews, expert panels, red-team/debate.",
        "inputs": [
            {"kind": "text", "env": "DEMO_MOTION", "label": "Strategy motion for the crew to debate",
             "value": "Orbit should launch a free tier to accelerate growth"},
        ],
    },
    {
        "id": "4",
        "tab": "4 · MCP finale",
        "title": "Demo 4 — MCP: connect an agent to YOUR OWN tools",
        "agent_type": "Agent + a reusable MCP tool server",
        "framework": "Model Context Protocol + OpenAI Agents SDK",
        "needs_azure": True,
        "cost": "A few calls + a local subprocess (the tool server)",
        "runtime": "~20–40 s",
        "script": "demos/4_mcp_trading/mcp_agent.py",
        "teaches": (
            "Where the industry is converging. Publish tools **once** as an MCP server and any agent "
            "connects to them. The agent here knows *nothing* about Orbit's store — it points at the "
            "server and the tools appear. The same server could plug into Claude Desktop or Cursor."
        ),
        "architecture": """
flowchart LR
    IN["🧑 Customer request — INPUT"] --> AGENT{{"account_manager agent<br/>knows NOTHING about the store"}}
    AGENT -.->|"reasoning"| AZ[("Azure OpenAI")]
    AGENT <-->|"MCP · stdio"| SRV["accounts_server.py<br/>(MCP server subprocess)"]
    SRV --> TOOLS["@mcp.tool<br/>get_store_credit · get_items · purchase · refund"]
    TOOLS --> DOMAIN["accounts.py (domain logic)"]
    DOMAIN --> DB[("accounts.json")]
    AGENT --> OUT["✅ store credit + items — OUTPUT"]
    classDef agent fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef mcp fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef az fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class AGENT agent;
    class SRV,TOOLS,DOMAIN mcp;
    class AZ az;
    class IN,OUT io;
""",
        "layers": [
            "**Agent layer** — the Agents-SDK agent; contains zero store logic.",
            "**Transport layer** — `MCPServerStdio` launches the server as a subprocess and auto-discovers its tools over stdin/stdout.",
            "**Tool layer (the MCP server)** — `@mcp.tool` functions: the published, reusable interface (get_store_credit, get_items, purchase, refund).",
            "**Domain layer** — `accounts.py`: store credit, items owned, purchase/refund rules.",
            "**Persistence layer** — `accounts.json`; state survives across runs.",
        ],
        "contract": (
            "**Input** → a customer name + a natural-language request.  \n"
            "**Output** → `🔌 Tools discovered: [...]`, the agent purchases items with store credit, then "
            "reports the remaining credit & items; state persists to `accounts.json`.  \n"
            "**Try this** → run it once, then again — the second run sees the persisted items. "
            "The agent code never changes; the **server** owns the domain."
        ),
        "watch": "`🔌 Connected to MCP server. Tools discovered: [...]` then purchases execute. You changed *only the server* to add capability — the agent is untouched.",
        "when": "Reusable tools across many agents/clients. Build Orbit's catalog/CRM/billing once as an MCP server; layer it under any framework.",
        "inputs": [
            {"kind": "text", "env": "DEMO_NAME", "label": "Customer name", "value": "Alice"},
            {"kind": "textarea", "env": "DEMO_REQUEST",
             "label": "Request to the agent (blank → default purchase for the customer above)", "lines": 2,
             "value": "", "placeholder": "Purchase 10 WIDGET and 2 GIZMO with my store credit, then report my remaining credit and items."},
        ],
    },

    # ================= ACT 2 — PRODUCTION DEPTH (what survives contact with prod) =================
    {
        "id": "6",
        "tab": "6 · Resilience",
        "title": "Demo 6 — Resilient Agent (tools fail; recover, then escalate)",
        "agent_type": "Resilience as an engineering concern, not a model decision",
        "framework": "Plain Python (retry / failover / escalation around the tool)",
        "needs_azure": False,
        "cost": "$0.00 — deterministic, no API key",
        "runtime": "~1 s",
        "script": "demos/6_resilient_agent/resilient_agent.py",
        "teaches": (
            "When Orbit charges a subscription, the payment gateway sometimes fails — a timeout, a 503, "
            "a declined card. What happens next is **not** a model decision: it's a retry policy, a "
            "fallback to a second gateway, and an escalation path. Deterministic, testable, observable."
        ),
        "architecture": """
flowchart TD
    IN["💳 charge $49.99 — INPUT"] --> ORCH["Orchestration: recover → escalate"]
    ORCH --> PRIM["PRIMARY provider"]
    PRIM --> RETRY{{"call_with_retry<br/>transient? backoff + retry"}}
    RETRY -->|"success"| OK["✅ charged — OUTPUT"]
    RETRY -->|"permanent / budget exhausted"| FB["FALLBACK provider"]
    FB -->|"success"| OK
    FB -->|"also fails"| ESC["ESCALATE → durable queue"]
    ESC --> OUT2["⚠️ escalated (never silently dropped) — OUTPUT"]
    classDef code fill:#fef9c3,stroke:#ca8a04,color:#713f12;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class ORCH,RETRY,PRIM,FB,ESC code;
    class IN,OK,OUT2 io;
""",
        "layers": [
            "**Input layer** — the request (charge $X) + the (simulated) failure scenario.",
            "**Resilience layer** — `call_with_retry`: classify the error (transient vs permanent) and back off + retry *only* the transient ones.",
            "**Recovery layer** — fail over to a secondary provider on a permanent failure or exhausted retries.",
            "**Escalation layer** — a durable queue for a human when everything fails; the request is never silently dropped.",
            "**Note** — the model is deliberately *not* in this loop. Retry/backoff is code.",
        ],
        "contract": (
            "**Input** → a charge + a failure scenario (transient-fail count / permanent / both fail).  \n"
            "**Output** → ✅ charged (primary or fallback path) **or** ⚠️ escalated.  \n"
            "**Try this** → set transient fails **above** the retry budget (e.g. 5) → primary exhausts → "
            "failover; tick **both providers fail** → escalation."
        ),
        "watch": "Transient errors back off and retry; permanent errors fail fast (no wasted retries) and fail over; total exhaustion escalates.",
        "when": "Any agent that calls a real, fallible service — i.e. all of them in production. Resilience lives around the tool, not in the prompt.",
        "inputs": [
            {"kind": "number", "env": "DEMO_TRANSIENT_FAILS", "label": "Primary: transient failures before success", "value": 2},
            {"kind": "bool", "env": "DEMO_PRIMARY_PERMANENT", "label": "Primary fails permanently (card declined)?", "value": False},
            {"kind": "bool", "env": "DEMO_SECONDARY_FAILS", "label": "Fallback provider also fails?", "value": False},
        ],
    },
    {
        "id": "7",
        "tab": "7 · Eval & Trace",
        "title": "Demo 7 — Eval & Trace (the part that actually ships agents)",
        "agent_type": "Measure it: trace every run, score against gold labels",
        "framework": "OpenAI SDK + a tiny eval harness (deterministic + LLM-as-judge)",
        "needs_azure": True,
        "cost": "~$0.0002 for the whole eval set",
        "runtime": "~10–20 s",
        "script": "demos/7_eval_trace/eval_trace.py",
        "teaches": (
            "Orbit's support agent triages tickets — but is it any good? A single run won't tell you. You "
            "need a **trace** (tokens + latency + raw output) and an **eval** (a score vs known-good labels) "
            "to know how often it's right, what it costs, and whether your last change helped."
        ),
        "architecture": """
flowchart TD
    IN["🎫 ticket set + GOLD labels — INPUT"] --> AGENT["Agent under test<br/>classify → JSON"]
    AGENT --> TRACE[("Trace: latency · tokens · raw out")]
    AGENT --> CHK{{"deterministic check<br/>pred == gold"}}
    AGENT --> JUDGE{{"LLM-as-judge<br/>rate justification 1–5"}}
    CHK --> CARD["Scorecard"]
    JUDGE --> CARD
    TRACE --> CARD
    CARD --> OUT["✅ accuracy · judge · p50/p95 · tokens · $ — OUTPUT"]
    classDef llm fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef tool fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class AGENT,JUDGE llm;
    class CHK,TRACE tool;
    class IN,OUT io;
""",
        "layers": [
            "**Dataset layer** — inputs + gold labels; the asset that makes iteration possible.",
            "**Agent-under-test** — the thing you're measuring (here: ticket triage → JSON).",
            "**Trace layer** — per-run latency, tokens, and raw output (your observability data).",
            "**Scoring layer** — deterministic check (free, 100% reliable) anchored by an LLM-as-judge (catches quality a string match can't).",
            "**Reporting layer** — the scorecard you diff across prompt/model changes and run in CI.",
        ],
        "contract": (
            "**Input** → a labelled ticket set (add your own ticket + expected category).  \n"
            "**Output** → per-case pass/fail + judge score, a **full trace** for case 1, and a "
            "**scorecard** (accuracy, judge avg, p50/p95 latency, tokens, $).  \n"
            "**Try this** → add an ambiguous ticket and see whether the classifier and the judge agree."
        ),
        "watch": "The scorecard — not a single run — is how you know a change helped. Wire the trace into real observability; run the eval in CI.",
        "when": "Before you ship, and on every prompt/model change thereafter. This is the day-to-day job of operating an agent.",
        "inputs": [
            {"kind": "textarea", "env": "DEMO_EVAL_TICKET", "label": "Add your own ticket to the eval set (optional)", "lines": 2,
             "value": "", "placeholder": "e.g. My invoice shows the wrong VAT rate for an EU order."},
            {"kind": "text", "env": "DEMO_EVAL_EXPECT", "label": "Expected category for your ticket", "value": "billing"},
        ],
    },
    {
        "id": "8",
        "tab": "8 · Real SQLite",
        "title": "Demo 8 — A Real Tool (agent over a real SQLite database)",
        "agent_type": "Touches something real: real DB, real SQL, a persisted write",
        "framework": "OpenAI SDK tool loop + sqlite3 (read guard + narrow write tool)",
        "needs_azure": True,
        "cost": "A few gpt-4o-mini calls",
        "runtime": "~10–20 s",
        "script": "demos/8_sqlite_agent/sqlite_agent.py",
        "teaches": (
            "Answer questions from Orbit's **real** orders database. The agent composes its own SQL against "
            "a real `sqlite3` file and can issue a refund — with the guardrails required the moment an agent "
            "touches real data: read-only SELECT enforcement, and writes only through a narrow, typed, "
            "parameterised tool."
        ),
        "architecture": """
flowchart TD
    IN["🧑 natural-language question — INPUT"] --> AGENT{{"LLM agent loop"}}
    AGENT -->|"list_tables / describe_table"| META["schema discovery"]
    AGENT -->|"run_select — SELECT-only guard"| READ["read path"]
    AGENT -->|"record_refund(id) — typed, parameterised"| WRITE["write path"]
    META --> DB[("shop.db — real sqlite3 file")]
    READ --> DB
    WRITE --> DB
    DB --> OUT["✅ answer + persisted refund (verified) — OUTPUT"]
    classDef llm fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef tool fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class AGENT llm;
    class META,READ,WRITE tool;
    class IN,OUT io;
""",
        "layers": [
            "**Agent layer** — composes SQL and decides which tool to call.",
            "**Read guard** — `run_select` permits exactly one read-only SELECT (no DDL/DML, no `;` stacking).",
            "**Write guard** — the *only* mutation is a narrow `record_refund(order_id, reason)`; the model picks *what* to refund, never *how* the write is done.",
            "**Data layer** — a real `sqlite3` file (`shop.db`), seeded deterministically.",
            "**Output layer** — the answer plus an independent DB-level verification of the write.",
        ],
        "contract": (
            "**Input** → a natural-language question (analytics + an action).  \n"
            "**Output** → the tool-call trace, a plain-English answer with numbers, and a "
            "DB-level verification that the write persisted.  \n"
            "**Try this** → ask a different aggregation, or instruct it to DELETE rows → the read guard refuses."
        ),
        "watch": "The agent discovers the schema, writes correct aggregate SQL, refunds an order — and the verification line reads the real DB, not the model's claim.",
        "when": "The moment an agent touches a real data store. Narrow, typed write tools + read-only guards keep 'DROP TABLE' off the table.",
        "inputs": [
            {"kind": "textarea", "env": "DEMO_QUESTION", "label": "Ask the database", "lines": 3,
             "value": "Which product has the highest total revenue (price*qty), and how many orders included it? Then refund order 1003 because the customer reports it never arrived."},
        ],
    },
    {
        "id": "9",
        "tab": "9 · LangGraph",
        "title": "Demo 9 — LangGraph (retry-until-criteria + human approval gate)",
        "agent_type": "Stateful graph: explicit nodes, cycles, checkpointed pause/resume",
        "framework": "LangGraph + langchain-openai (AzureChatOpenAI)",
        "needs_azure": True,
        "cost": "A few gpt-4o-mini calls",
        "runtime": "~15–30 s",
        "script": "demos/9_langgraph_workflow/langgraph_workflow.py",
        "teaches": (
            "Before Orbit publishes launch copy, it should be good *and* a human should sign off. This "
            "LangGraph flow regenerates the draft until it clears a quality bar (evaluator-optimizer), then "
            "**pauses at a human approval gate** before publishing — explicit nodes, **cycles**, persisted "
            "state."
        ),
        "architecture": """
flowchart TD
    IN["🧑 task + quality bar — INPUT"] --> GEN["generate (draft)"]
    GEN --> EVAL{{"evaluate (judge 1–5 + feedback)"}}
    EVAL -->|"score < bar AND iters < max"| GEN
    EVAL -->|"meets bar / max iters"| GATE["⏸ human gate · interrupt()"]
    GATE -->|"approve"| PUB["publish ✅"]
    GATE -->|"reject"| REJ["not published"]
    PUB --> OUT["OUTPUT"]
    REJ --> OUT
    classDef node fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef gate fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class GEN,EVAL,PUB,REJ node;
    class GATE gate;
    class IN,OUT io;
""",
        "layers": [
            "**State layer** — a typed, checkpointed object flowing through the graph.",
            "**Generate node** — drafts, then revises using the judge's feedback.",
            "**Evaluate node** — scores against criteria; a conditional edge loops back until the bar is met (hard-capped so it can't loop forever).",
            "**Human gate** — `interrupt()` pauses the graph (state persisted) for an out-of-band decision.",
            "**Action node** — `publish` runs only on approval; otherwise nothing happens.",
        ],
        "contract": (
            "**Input** → a copywriting task, a quality bar (1–5), and a human decision.  \n"
            "**Output** → the generate↔evaluate loop trace, a pause at the gate, then PUBLISHED or NOT PUBLISHED.  \n"
            "**Try this** → set the decision to **reject** → nothing publishes even though it cleared the "
            "bar; lower the bar to 2 → it passes in a single iteration."
        ),
        "watch": "The draft is regenerated WITH feedback until it clears the bar; the graph then truly pauses (checkpointed) and resumes only on the human's decision.",
        "when": "Deterministic branching/looping, durable state, and human-in-the-loop on consequential actions — the production-control framework.",
        "inputs": [
            {"kind": "textarea", "env": "DEMO_TASK", "label": "Task for the copywriter", "lines": 2,
             "value": "Write a one-sentence launch announcement (max 200 characters) for Orbit's new one-click checkout. Be specific; avoid hype words."},
            {"kind": "number", "env": "DEMO_BAR", "label": "Quality bar (judge score 1–5 required to proceed)", "value": 4},
            {"kind": "choice", "env": "DEMO_APPROVE", "label": "Human decision at the gate", "value": "approve", "choices": ["approve", "reject"]},
        ],
    },
    {
        "id": "10",
        "tab": "10 · Prod failures",
        "title": "Demo 10 — When this goes wrong in prod (failures + guards)",
        "agent_type": "Failure modes that page you at 2am — and the controls that stop them",
        "framework": "OpenAI SDK + orchestration-layer guards",
        "needs_azure": True,
        "cost": "A few gpt-4o-mini calls (bounded)",
        "runtime": "~20–40 s",
        "script": "demos/10_failure_modes/failure_modes.py",
        "teaches": (
            "The three ways Orbit's agents can hurt it in production — a runaway **cost blowup**, an "
            "**infinite loop**, and a **prompt injection** smuggled through tool output — each triggered for "
            "real, then contained by a guard. **Safety lives in the orchestration layer, not in hoping the "
            "model behaves.**"
        ),
        "architecture": """
flowchart TD
    IN["⚙️ choose failure mode — INPUT"] --> SEL{"which mode?"}
    SEL -->|"cost"| C["runaway crawl<br/>🛑 token budget"]
    SEL -->|"loop"| L["impossible goal<br/>🛑 cycle detector + turn cap"]
    SEL -->|"injection"| J["malicious tool output<br/>🛡️ data-not-instructions + allowlist"]
    C --> OUT["✅ guard engaged, damage contained — OUTPUT"]
    L --> OUT
    J --> OUT
    classDef guard fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class C,L,J guard;
    class IN,OUT io;
""",
        "layers": [
            "**Budget control** — a cumulative token/cost cap checked every turn; aborts runaway spend (watch the 1→2→4→8 fan-out trip it).",
            "**Liveness control** — a max-turn cap **and** a cycle detector (a revisited state ⇒ no progress).",
            "**Trust boundary** — tool output is untrusted DATA; the system never executes instructions found inside it.",
            "**Authorization control** — destructive tools sit behind an out-of-band allowlist the model cannot grant itself.",
        ],
        "contract": (
            "**Input** → which failure mode to run (all / cost / loop / injection) + a danger toggle.  \n"
            "**Output** → the failure unfolding (cost fan-out, oscillation, the injection payload) and the "
            "guard visibly engaging.  \n"
            "**Try this** → set mode = **injection** and flip *Allow delete* on/off to see the allowlist as "
            "the last line of defence even if the model is fooled."
        ),
        "watch": "Each guard *engages on screen*: BUDGET TRIPPED, CYCLE DETECTED, and the injected instruction refused with the database left intact.",
        "when": "Before production. These are engineering controls (caps, detectors, allowlists) — never things you delegate to the model's goodwill.",
        "inputs": [
            {"kind": "choice", "env": "DEMO_FAILURE_MODE", "label": "Failure mode to run", "value": "all",
             "choices": ["all", "cost", "loop", "injection"]},
            {"kind": "bool", "env": "DEMO_ALLOW_DELETE", "label": "Allow the destructive tool (disables the allowlist guard)?", "value": False},
        ],
    },

    # ================= FLAGSHIP — a real agent doing real work, verified =================
    {
        "id": "11",
        "tab": "★ Flagship · SWE Agent",
        "title": "Flagship — Autonomous SWE Agent (fixes a real bug, verified by real tests)",
        "agent_type": "A loop with real tools + an objective oracle — a mini Claude-Code",
        "framework": "OpenAI SDK tool loop + pytest (sandboxed file I/O & test runner)",
        "needs_azure": True,
        "cost": "~$0.0015 per run",
        "runtime": "~20–30 s",
        "script": "demos/11_swe_agent/swe_agent.py",
        "teaches": (
            "A boundary bug in Orbit's billing engine is under-charging customers on a pricing tier. Dropped "
            "into the sandboxed project with a **red** test suite, the agent fixes the **source** and re-runs "
            "until **green**, then stops. Success is `pytest` exiting 0, checked by the harness; it can't "
            "grade itself or edit the tests to cheat."
        ),
        "architecture": """
flowchart TD
    IN["🐛 Failing test suite — INPUT"] --> AGENT{{"SWE agent loop"}}
    AGENT -->|"list_files / read_file"| INV["investigate"]
    AGENT -->|"edit_file / write_file"| SRC["patch SOURCE<br/>🔒 test files frozen"]
    AGENT -->|"run_tests"| PT["pytest · subprocess · sandboxed"]
    INV --> WS[("_workspace sandbox")]
    SRC --> WS
    PT -->|"RED → failures fed back, loop"| AGENT
    PT -->|"GREEN — harness-verified"| OUT["✅ suite passes + diff + report — OUTPUT"]
    classDef agent fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef tool fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef guard fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class AGENT agent;
    class INV,PT tool;
    class SRC guard;
    class IN,OUT io;
""",
        "layers": [
            "**Agent layer** — the loop that reads failures, decides the next move, and patches code.",
            "**Tool layer** — *real* hands: `list_files`, `read_file`, `edit_file`/`write_file`, `run_tests` (a real pytest subprocess).",
            "**Verification layer** — pytest is the ground truth; the *harness* declares success on exit-0, not the model.",
            "**Guardrail layer** — test files are frozen (anti reward-hacking), paths are sandboxed (no `../` escape), a hard iteration cap, and a subprocess timeout.",
            "**Observability layer** — every tool call, tokens and latency are traced; the run ends with the unified diff and a before→after scorecard.",
        ],
        "contract": (
            "**Input** → a project with a failing suite + the task ('fix the bug, don't touch the tests').  \n"
            "**Output** → the investigate→patch→test loop, a **harness-verified green** suite, the **diff** the "
            "agent produced, and a before→after scorecard (tests, turns, tokens, $).  \n"
            "**Try this** → lower *max turns* to squeeze it; the sandbox resets every run, so the bug is always fresh."
        ),
        "watch": "It reads the failing assertions, finds the `>` vs `>=` boundary bug, patches all three pricing tiers, and only stops when pytest exits 0 — verified by the harness, not its own claim. Try telling it to edit the tests: the tool layer refuses.",
        "when": "Any closed-loop task with an objective oracle: code fixes, CI auto-repair, data-pipeline self-healing, IaC that must `validate`. If you have a test, you have an agent target.",
        "inputs": [
            {"kind": "textarea", "env": "DEMO_TASK", "label": "Task for the agent", "lines": 2,
             "value": "The billing test suite is failing. Investigate, fix the bug in the source code, and make every test pass. Do not modify the tests."},
            {"kind": "number", "env": "DEMO_MAX_TURNS", "label": "Max iterations (hard cap)", "value": 14},
        ],
    },
    {
        "id": "12",
        "tab": "12 · Model Router",
        "title": "Demo 12 — Model Router (LiteLLM): cheap model for easy, frontier only for hard",
        "agent_type": "Cost-tier routing across models — least capable model that works",
        "framework": "LiteLLM (one API, any provider) over Azure",
        "needs_azure": True,
        "cost": "~$0.008 per run",
        "runtime": "~15–25 s",
        "script": "demos/12_model_router/model_router.py",
        "teaches": (
            "Orbit's AI features handle a request stream — mostly routine (reformat a date, a one-line "
            "summary), a few genuinely hard. Sending them all to a frontier model is how the bill explodes. "
            "A cheap classifier routes each to a tier, all through **LiteLLM** — one provider-agnostic API "
            "where the model is a config string."),
        "architecture": """
flowchart TD
    IN["📥 request — INPUT"] --> ROUTER{{"cheap model classifies<br/>SIMPLE / COMPLEX"}}
    ROUTER -->|"SIMPLE (~most traffic)"| CHEAP["cheap model · gpt-4o-mini"]
    ROUTER -->|"COMPLEX"| FRONT["frontier model · gpt-4o"]
    CHEAP --> LL["LiteLLM<br/>azure/&lt;deployment&gt;"]
    FRONT --> LL
    LL --> METER["cost meter: cascade vs all-frontier"]
    METER --> OUT["✅ answers + savings — OUTPUT"]
    classDef llm fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef tool fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class ROUTER,CHEAP,FRONT llm;
    class LL,METER tool;
    class IN,OUT io;
""",
        "layers": [
            "**Routing layer** — a cheap-model classifier tags each task SIMPLE vs COMPLEX (a few tokens).",
            "**Provider layer** — LiteLLM: `litellm.completion(model='azure/<deployment>', …)`; swap providers by changing the string.",
            "**Cheap path** — routine tasks answered by gpt-4o-mini (a fraction of the frontier price).",
            "**Frontier path** — only genuinely hard tasks reach the expensive model.",
            "**Accounting layer** — a cost meter: cascade cost vs frontier-for-everything, and the per-task multiplier.",
        ],
        "contract": (
            "**Input** → a batch of mixed-difficulty tasks (add your own below).  \n"
            "**Output** → each task tagged `[→ CHEAP]` or `[→ FRONTIER]`, then a **cost meter** showing the "
            "multiplier (identical routine work costs ~17× more on the frontier model) and the overall saving.  \n"
            "**Try this** → add a hard task and watch it route to FRONTIER; add a lookup and watch it stay CHEAP."
        ),
        "watch": "The cheap classifier routes routine tasks to gpt-4o-mini and only escalates real reasoning; the meter shows the ~17× price gap you avoid on every routine request.",
        "when": "High-volume LLM traffic where most requests are routine. Pairs with Demo 1b (rules vs LLM); this is the tier up — cheap model vs frontier model.",
        "inputs": [
            {"kind": "textarea", "env": "DEMO_EXTRA_TASK", "label": "Add your own task to route (optional)", "lines": 2,
             "value": "", "placeholder": "e.g. Explain the CAP theorem and its practical trade-offs for a payments datastore."},
        ],
    },
]


# =====================================================================
# DEEP DIVE — the senior-level "why", keyed by demo id. Rendered in each tab as
# Objective · Where it's used · Why this approach (trade-offs) · How to take it further.
# =====================================================================
DEEP_DIVE = {
    "1": {
        "objective": (
            "Orbit's first task — planning its own launch — is the excuse to build, from scratch, the "
            "one pattern the whole field reduces to: *an agent is an LLM in a loop, with tools, that "
            "decides for itself when to stop.* You can't reason about what CrewAI, LangGraph or the "
            "Agents SDK are doing until you've seen the bare loop they all wrap."),
        "use_cases": [
            "Coding agents (Claude Code, Cursor, Aider) — the read → edit → run → observe loop *is* this.",
            "Deep-research / analyst assistants where the number of steps isn't known up front.",
            "Multi-step ops & support copilots ('triage this, then act').",
            "Any 'do this open-ended task' workflow that must decide its own next step.",
        ],
        "why": (
            "We hand-roll the loop with the bare OpenAI SDK because the objective is *understanding*, not "
            "productivity — a framework here would hide the exact thing being taught: the `finish_reason` "
            "branch and the append-tool-result-and-continue step. Tools as JSON schemas dispatched by name "
            "is the literal contract every provider implements. The trade-off is real: a hand-rolled loop "
            "has no retries, tracing, parallel tool calls, or schema validation — which is precisely why "
            "the later tabs exist."),
        "improve": [
            "Validate tool arguments with Pydantic before dispatch (reject malformed calls).",
            "Execute independent tool calls in parallel; stream tokens to the UI.",
            "Add a max-turn + token budget (see Demo 10) so it can't run away.",
            "Persist `messages` for resumability; swap the planner tools for real ones (search, code-exec).",
            "Wrap it in the eval harness (Demo 7) before trusting any prompt change.",
        ],
    },
    "5a": {
        "objective": (
            "Keeping Orbit's servers healthy is a known playbook — the perfect place to break the assumption "
            "that 'agent' implies 'LLM'. The loop is brain-agnostic; for an enumerable decision space a "
            "deterministic policy is a legitimate — often superior — agent. Instil cost/latency/testability "
            "discipline *before* anyone reaches for a model."),
        "use_cases": [
            "SRE auto-remediation / runbooks (restart, scale out, fail over).",
            "Kubernetes controllers & operators — the reconcile loop is exactly perceive→decide→act.",
            "Rule-based fraud/risk declines, form validation & routing, feature-flag rollout controllers.",
            "Trading circuit-breakers and other hard-real-time control loops.",
        ],
        "why": (
            "When the mapping from state to action is known, rules are $0, microsecond-latency, deterministic, "
            "and unit-testable — an LLM would add cost, latency and nondeterminism for no gain. We use a plain "
            "rule cascade so the contrast with Demo 1 is visceral: same loop, different brain. The trade-off is "
            "that rules can't handle novelty or fuzzy input — which is exactly what the hybrid (next tab) is for."),
        "improve": [
            "Load the policy from a decision table / config instead of code; add property-based tests.",
            "Emit a metric + structured log per decision for observability.",
            "Add a coverage/confidence check that escalates unknown states to an LLM (→ hybrid).",
            "Model the policy as a formal state machine; shadow it against an LLM to find rule gaps.",
        ],
    },
    "5b": {
        "objective": (
            "Orbit's incident stream is mostly known, occasionally novel — the case for the production cost "
            "architecture: route the known ~90% through free rules and escalate only the long tail to the LLM, "
            "and *quantify* the saving with a live meter. Make 'don't pay a model for a decision a rule already "
            "knows' measurable, not a slogan."),
        "use_cases": [
            "Tiered customer support (FAQ/rules first, LLM for the remainder).",
            "Content moderation (hash/regex/classifier → LLM only for edge cases).",
            "Alert triage, ticket/email routing, spam & abuse pipelines.",
            "Semantic-cache + LLM fallback for any high-volume request stream.",
        ],
        "why": (
            "'LLM-for-everything' is the single most common way a promising pilot becomes unaffordable in "
            "production. A cheap router preserves quality on the hard cases while collapsing cost on the easy "
            "ones. The trade-off: you now run two paths plus a router, you carry misrouting risk, and you must "
            "monitor the escalation rate — a rising rate signals rule rot or a distribution shift."),
        "improve": [
            "Replace exact-match routing with an embedding / zero-shot classifier or a small cheap model.",
            "Add a semantic cache (e.g. GPTCache) for repeat queries; cascade models small→large.",
            "Track escalation-rate and cost-per-decision as SLOs; alert when they drift.",
            "Auto-mine escalated cases to propose new rules; add a confidence threshold + human-review queue.",
        ],
    },
    "2": {
        "objective": (
            "Orbit's customer outreach is a coordinator-plus-specialists job — the excuse to graduate from a "
            "hand-rolled loop to a production framework and learn its three primitives: tools, agents-as-tools, "
            "and handoffs, plus the control-transfer semantics that distinguish them (a tool returns control to "
            "the caller; a handoff transfers it away)."),
        "use_cases": [
            "SDR / outbound automation; coordinator-delegates-to-specialists pipelines.",
            "Tiered support triage that routes to specialist agents with distinct prompts/guardrails.",
            "Voice agents with routing; multi-skill assistants where each skill needs its own model/policy.",
        ],
        "why": (
            "The Agents SDK is code-first: you keep ordinary Python control flow and get tools, handoffs, "
            "guardrails, tracing and structured output without hand-managing the message loop. Agents-as-tool "
            "vs handoff is the key design axis — *tool* when you want the result back under the caller's "
            "control, *handoff* when the sub-agent should own the rest of the conversation. Trade-off: more "
            "abstraction than Demo 1 (the loop is hidden), and its hosted tracing is OpenAI-only, so on Azure "
            "we disable it."),
        "improve": [
            "Add input/output guardrails (PII, jailbreaks, competitor mentions).",
            "Return the chosen draft as a validated Pydantic structured output; wire a real email provider.",
            "Use per-agent models (cheap drafters, a strong judge) and parallelize the three SDR calls.",
            "Add sessions/memory and the eval harness (Demo 7).",
        ],
    },
    "3": {
        "objective": (
            "Deciding an Orbit strategy call by debate contrasts code-first orchestration with the *declarative* "
            "paradigm: you describe a cast (role/goal/backstory) and a list of tasks, and the framework "
            "orchestrates. Feel the trade-off between expressiveness/speed and control."),
        "use_cases": [
            "Research crews (researcher → writer → editor); content pipelines.",
            "'Panel of experts' / debate / red-team; competitive analysis and due-diligence.",
            "Rapid prototyping of a multi-agent idea, and workflows non-engineers can read.",
        ],
        "why": (
            "Declarative crews compress 'a team of personas' into a few lines and the persona framing reliably "
            "shapes behaviour — great for prototyping and for non-engineers. We route through LiteLLM to stay "
            "Azure-portable and provider-agnostic. The trade-off is control: you cede the orchestration, "
            "debugging is opaquer, and verbose agents can balloon token cost; for complex branching/state you "
            "outgrow it and move to LangGraph or code-first."),
        "improve": [
            "Move roles/tasks to YAML (the course's config-driven style); pin versions (the API moves fast).",
            "Give each agent a tuned model/provider and real tools (web, RAG).",
            "Switch to a hierarchical process with a manager; cap verbosity for cost.",
            "Add output validation and run it through the eval harness.",
        ],
    },
    "4": {
        "objective": (
            "Expose Orbit's store as a tool *standard*: publish tools once as an MCP server and any agent or "
            "client connects, decoupling tool authoring from agent code. See the M×N → M+N integration win — "
            "and that the agent itself contains zero store logic."),
        "use_cases": [
            "An internal tool platform: one MCP server for your DB/CRM/observability, used by every agent and by Claude Desktop / Cursor / IDEs.",
            "SaaS vendors shipping official MCP servers so any client can integrate.",
            "Connecting agents to Slack / GitHub / Jira / Postgres via existing community servers.",
        ],
        "why": (
            "Without a standard, every agent re-implements every integration — M agents × N tools. MCP makes "
            "tools reusable, versionable, independently deployable and shareable across clients; stdio/HTTP "
            "transports mean one server plugs into many hosts. Trade-off: another process and protocol to run, "
            "secure and version, and auth/permissions become first-class. We use stdio + a local server for a "
            "no-dependency demo."),
        "improve": [
            "Add auth + per-tool scopes/authorization; rate-limit and audit-log every tool call.",
            "Serve over HTTP/SSE for multi-client; back it with a real DB (→ Demo 8).",
            "Expose resources & prompts, not just tools; add a tool-schema contract test.",
            "Register it in Claude Desktop / Cursor to prove the portability claim.",
        ],
    },
    "6": {
        "objective": (
            "Charging an Orbit subscription must survive a flaky gateway — so it proves resilience (retry, "
            "backoff, failover, escalation) is deterministic code that *wraps* the tool, not a responsibility "
            "you hand to the model. The crux is a correct error taxonomy and a never-drop escalation path."),
        "use_cases": [
            "Payments (gateway failover), and any third-party API integration.",
            "Queue/stream consumers, ETL pipelines, webhook delivery.",
            "LLM provider failover itself (primary model → secondary on 429/5xx).",
            "Durable-execution engines (Temporal, AWS Step Functions) encode exactly this.",
        ],
        "why": (
            "LLMs are nondeterministic and must not own retry policy — that belongs in code where it is testable "
            "and observable. Classifying transient vs permanent is the crux: retrying a 402 burns time and money; "
            "*not* retrying a 503 drops recoverable work. We keep it deterministic so the trace is reproducible. "
            "Trade-off: more orchestration code, and you must choose budgets/backoff carefully (idempotency, "
            "thundering herd)."),
        "improve": [
            "Idempotency keys so retries never double-charge.",
            "Circuit breaker (open after N failures, half-open probes) + full-jitter backoff.",
            "Dead-letter queue + async retry worker; timeouts and bulkheads.",
            "Adopt durable execution (Temporal / Durable Functions); chaos-test the failure paths.",
        ],
    },
    "7": {
        "objective": (
            "Orbit's support-triage agent is the case study for the discipline that separates shipped agents "
            "from demos: trace every run and score it against gold labels, producing a diffable scorecard — so "
            "quality is *measurable* and regressions *catchable*."),
        "use_cases": [
            "Pre-ship validation and CI gates on every prompt/model change.",
            "Model migration and bake-offs (gpt-4o-mini → 4.1), prompt A/B tests.",
            "Production drift monitoring; RAG and tool-use evaluation.",
        ],
        "why": (
            "You cannot improve what you don't measure, and a single run is an anecdote. We pair a deterministic "
            "check (cheap, reliable, narrow) with an LLM-judge (broad, but fallible and costed) — the deterministic "
            "anchor keeps you honest about judge drift. Trade-off: building and maintaining a labelled set is real "
            "work, judges need their own calibration, and evals cost tokens."),
        "improve": [
            "Grow the labelled set from real production traces; add adversarial/red-team cases.",
            "Add rubric/pairwise judges and calibrate them against human labels; measure inter-judge agreement.",
            "Adopt a real eval/observability platform (LangSmith, Langfuse, Braintrust, Phoenix).",
            "Run in CI with thresholds; track p50/p95 latency and cost as SLOs.",
        ],
    },
    "8": {
        "objective": (
            "Answering questions from Orbit's real orders database moves from simulation to a real datastore, and "
            "shows the guardrails required the instant an agent can read and write real data: read-only "
            "enforcement plus narrow, typed write tools. Safe natural-language access to data."),
        "use_cases": [
            "Internal analytics / BI 'text-to-SQL' assistants and ops dashboards.",
            "Support tooling that looks up *and* mutates records; admin copilots.",
            "Data-exploration agents — and the read/write-guard pattern generalises to any API-backed agent.",
        ],
        "why": (
            "A real database makes the security model unavoidable: an unconstrained 'run SQL' tool is an "
            "injection / `DROP TABLE` waiting to happen. We separate a read-only, SELECT-guarded tool from a "
            "narrow, typed, parameterised write tool, so the model decides *what*, never *how*. Trade-off: "
            "model-generated SQL can still be wrong or slow (no semantic guarantee), and write coverage is "
            "deliberately limited to the tools you expose."),
        "improve": [
            "Run as a least-privilege DB user with row-level security; add LIMIT, timeouts and cost guards.",
            "Log every query for audit; validate result shape against a schema; use a read replica.",
            "Put writes behind a human-approval gate (→ Demo 9); add an NL→SQL eval set (→ Demo 7).",
            "Prefer a semantic/metrics layer (dbt) over raw model-authored SQL where correctness is critical.",
        ],
    },
    "9": {
        "objective": (
            "Publishing Orbit's launch copy needs quality *and* sign-off — the case for stateful, controllable "
            "orchestration: an explicit graph, cycles with caps (retry-until-criteria), durable checkpointed "
            "state, and a real human-in-the-loop gate. The right tool for flows that branch, loop, and need approval."),
        "use_cases": [
            "Any consequential action behind approval — refunds, deploys, outbound sends, financial transactions.",
            "Content generation with a review gate; evaluator-optimizer loops; deep-research with verification.",
            "Long-running, resumable multi-step processes that may pause for hours.",
        ],
        "why": (
            "When control flow has cycles, branches and pauses, both hand-rolled loops and declarative crews fall "
            "down; a graph makes the flow explicit, testable and resumable, and the checkpointer enables *true* "
            "pause/resume — a human can approve later from a different process. `interrupt()` is a first-class "
            "HITL primitive, not a hack. Trade-off: more ceremony and a learning curve, and you own the state schema."),
        "improve": [
            "Persist the checkpointer to SQLite/Postgres (not in-memory) for real durability + replay.",
            "Surface the approval gate in a real UI / Slack; add a timeout that escalates if no human responds.",
            "Add parallel branches (map-reduce) and subgraphs for modularity; stream intermediate state.",
            "Combine with the eval harness; version the graph and its prompts.",
        ],
    },
    "10": {
        "objective": (
            "Confront the failure modes that would take Orbit down — cost blowups, infinite loops, prompt "
            "injection — and show each is contained by an *engineering control*, not by trusting the model. "
            "Instil a defence-in-depth mindset."),
        "use_cases": [
            "Every production agent — these failure modes are universal.",
            "Especially: agents with autonomy + tools, public/untrusted input, RAG over external content, or destructive capabilities.",
            "Security reviews and pre-production hardening checklists.",
        ],
        "why": (
            "Autonomy + tools + untrusted data is an inherently dangerous combination: the model can be wrong, "
            "loop, or be manipulated, so safety must be enforced *in the loop*. Budgets, turn-caps, cycle "
            "detection and allowlists are deterministic and auditable; treating tool output as data — never "
            "instructions — is the core anti-injection principle. Trade-off: guards add complexity and can have "
            "false positives (a legitimately long task hits a cap), and allowlists need maintenance."),
        "improve": [
            "Per-tenant / per-session budgets with alerts and spend dashboards.",
            "Semantic loop detection (not just exact-state); dedicated prompt-injection detectors + content provenance.",
            "Sandbox + least-privilege execution for tools; signed, audited tool calls; rate limiting.",
            "A red-team suite run in CI; human approval for every destructive action (→ Demo 9).",
        ],
    },
    "11": {
        "objective": (
            "Fixing a real bug in Orbit's billing engine gives the agent real tools and an **objective oracle**: "
            "it must fix the bug and *prove* it with a real test suite it cannot game. The point is that the "
            "loop + verification + guardrails — not the prompt — make an agent trustworthy near a real codebase."),
        "use_cases": [
            "Autonomous code-fixing / SWE agents (Claude Code, Cursor, Devin; the SWE-bench task).",
            "CI 'fix-the-build' bots that iterate until the pipeline is green.",
            "Data-pipeline self-healing — re-run until the schema/contract validates.",
            "IaC / config agents that loop until `terraform plan` or a linter passes.",
            "Migration agents that iterate until a golden test reproduces the old behaviour.",
        ],
        "why": (
            "The defining feature here is not the model — it's the **objective oracle** (the tests) closing the "
            "loop, so the agent grounds on truth and self-corrects from real error output instead of vibes. We "
            "hand-roll the loop (no framework) so the grounding and the guardrails are visible. The hard, senior "
            "parts are the guardrails: **freezing the tests** stops reward-hacking (the agent's natural shortcut "
            "is to 'fix' the failing test), **sandboxing** stops path escape, and **harness-verified** success "
            "stops the model declaring a false victory. Trade-off: this pattern only works where you *have* a "
            "cheap, trustworthy oracle — without one you're back to the eval harness of Demo 7."),
        "improve": [
            "Run each attempt in an isolated git worktree/branch and open a PR for human review instead of editing in place.",
            "Add a planning step + scratchpad for multi-file bugs; let it write a failing repro test first (then freeze it).",
            "Bound by a token budget + no-progress detector (Demo 10), not just a turn cap.",
            "Execute tests in a container / seccomp sandbox, not only a path guard.",
            "Add a critic pass that reviews the diff before accepting; parallelise across many bugs with worktrees.",
            "Wire it to real CI as a fix-the-build bot, gated by the eval harness (Demo 7).",
        ],
    },
    "12": {
        "objective": (
            "Cut the cost of Orbit's AI features without cutting quality by routing each request to the cheapest "
            "model that can handle it, and by making the model a swappable config value via LiteLLM rather than "
            "a hard dependency on one frontier provider."),
        "use_cases": [
            "High-volume assistants where most queries are routine (support, search, classification, extraction).",
            "Model cascades: try a small model, escalate to a bigger one only on low confidence.",
            "Provider portability / failover — same code across OpenAI, Azure, Anthropic, Bedrock, local models.",
            "A/B and canary testing of models behind one interface.",
        ],
        "why": (
            "Frontier-for-everything is the second-most-common cause of a runaway LLM bill (after the loop in "
            "Demo 10). The price gap between a small and a frontier model is often 15–30× on output tokens, and "
            "routine traffic is the majority — so routing is where most of the money is. LiteLLM is the honest "
            "abstraction: the model becomes a string, so routing, failover and provider swaps are config, not "
            "rewrites. Trade-off: the router itself costs a little and can misroute — monitor its accuracy and "
            "the escalation rate, exactly as in Demo 1b."),
        "improve": [
            "Replace the LLM classifier with an embedding/logistic router, or a confidence-based cascade (small model first, escalate on low logprob).",
            "Add a semantic cache in front of everything so repeat questions cost nothing.",
            "Track router accuracy + per-tier cost as SLOs; sample misroutes for review.",
            "Use LiteLLM's Router for real load-balancing, rate-limit handling, and provider failover.",
            "Add a third tier (a local/OSS model) for the truly trivial requests.",
        ],
    },
}


# =====================================================================
# Helpers
# =====================================================================
def read_source(rel_path: str) -> str:
    try:
        return (ROOT / rel_path).read_text(encoding="utf-8")
    except Exception as e:  # pragma: no cover
        return f"# (could not read {rel_path}: {e})"


def read_markdown(rel_path: str) -> str:
    """Read a Markdown file for direct rendering (raw text, not a code block)."""
    try:
        return (ROOT / rel_path).read_text(encoding="utf-8")
    except Exception as e:  # pragma: no cover
        return f"*(Could not load {rel_path}: {e})*"


def render_markdown_with_mermaid(md_text: str) -> None:
    """Render Markdown in the current Blocks context, turning ```mermaid fenced
    blocks into live Mermaid diagrams that render exactly like the rest of the app
    (Gradio's Markdown does not render mermaid fences on its own)."""
    for i, seg in enumerate(re.split(r"```mermaid\s*\n(.*?)```", md_text, flags=re.DOTALL)):
        if i % 2 == 1:            # captured mermaid source
            gr.HTML(mermaid(seg))
        elif seg.strip():         # surrounding markdown
            gr.Markdown(seg)


def azure_ready() -> bool:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_API_KEY")
    return bool(endpoint) and bool(key) and not key.startswith("PASTE_")


def _stream_script(rel_path: str, env_overrides: dict | None = None):
    """Generator: yields the accumulating console output of `rel_path`."""
    script = ROOT / rel_path
    header = f"$ python {rel_path}\n" + "─" * 64 + "\n"
    if not script.exists():
        yield header + f"❌ Script not found: {script}"
        return

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    for k, v in (env_overrides or {}).items():
        env[k] = "" if v is None else str(v)

    try:
        proc = subprocess.Popen(
            [sys.executable, str(script)],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except Exception as e:  # pragma: no cover
        yield header + f"❌ Failed to launch: {e!r}"
        return

    acc = header + "▶ running…\n"
    yield acc
    acc = header
    for line in iter(proc.stdout.readline, ""):
        acc += line
        yield acc
    proc.stdout.close()
    code = proc.wait()
    status = "✅ finished cleanly" if code == 0 else f"⚠️ exited with code {code}"
    yield acc + "\n" + "─" * 64 + f"\n{status}"


def make_runner(demo: dict):
    """Build the streaming click handler for a demo. Gradio passes the input
    component values positionally, in the order of demo['inputs']."""
    envs = [spec["env"] for spec in demo["inputs"]]
    needs_azure = demo["needs_azure"]
    script = demo["script"]

    def _run(*values):
        if needs_azure and not azure_ready():
            yield (
                "⚠️  This demo calls Azure OpenAI, but your `.env` isn't filled in.\n\n"
                "  1. Copy .env.example → .env\n"
                "  2. Paste AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY\n"
                "  3. Use 'Check Azure connection' on the Overview tab to confirm.\n\n"
                "(Demo 1b-a — the native agent — needs no key and runs anywhere.)"
            )
            return
        overrides = {env: val for env, val in zip(envs, values)}
        yield from _stream_script(script, overrides)

    return _run


def check_azure():
    if not azure_ready():
        yield (
            "⚠️  `.env` isn't filled in yet.\n"
            f"Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}\n"
            "Copy .env.example → .env, paste your rotated Azure endpoint + key, then retry."
        )
        return
    yield from _stream_script("smoke_test.py")


# =====================================================================
# Overview tab
# =====================================================================
OVERVIEW_MD = r"""
# Running Orbit — one business problem, solved as workflows, AI agents & agentic AI

**The business problem.** We are launching and running **Orbit**, a subscription e-commerce SaaS.
Like any real company that's not one task — it's a dozen: take the product to market, reach
customers, support them, keep the storefront and payments running, watch the AI bill, and make
sure none of it breaks or gets abused. This masterclass takes that *single* objective and solves
each piece with the **right level of automation** — so you see exactly where each tool fits.

**How we broke it down.** For every piece we asked one question: *how much of the control should a
human hard-code, and how much do we hand to a model?* That sorts the work into three buckets:

- **⚙️ Workflows — you own the steps.** A known, repeatable process: write the steps in code, use a
  model (if at all) only *inside* a step. Cheapest, fastest, most reliable.
  → *keep the platform healthy · triage incidents · charge subscriptions · control AI spend.*
- **🤖 AI Agents — one LLM drives a bounded task with tools.** The steps aren't known up front but
  the task is bounded, so one model loops with tools until it's done.
  → *plan the launch · triage & measure support · answer questions from the orders data.*
- **🧠 Agentic AI — autonomous, cooperating, stateful.** The work needs several specialists,
  branching, memory, or a human gate, so we hand whole goals to a system of agents.
  → *run outreach · decide strategy · publish with sign-off · share tools · fix the billing engine.*

Plus one **🛡️ cross-cutting** concern — **guardrails** — because the more control you hand the model,
the more ways it can fail.

> **Core idea:** an agent is an **LLM in a loop, with tools, that decides for itself when it's
> done.** Workflow → AI agent → agentic AI is one spectrum of *how much control you hand over.*
> **Pick the least autonomy that solves the step.** Every tab below is one step — run it and watch.
"""

# The complete flow: one objective → three categories → each demo as a step.
OVERVIEW_FLOW = """
flowchart TB
    OBJ["🏢 OBJECTIVE — launch & run Orbit (subscription e-commerce SaaS)"]
    OBJ --> W["⚙️ WORKFLOWS<br/>you own the steps"]
    OBJ --> A["🤖 AI AGENTS<br/>one LLM + tools, bounded"]
    OBJ --> AG["🧠 AGENTIC AI<br/>autonomous · multi-agent · stateful"]
    W --> W1["Keep the platform healthy<br/>1b · Native"]
    W --> W2["Triage incidents at scale<br/>1b · Hybrid"]
    W --> W3["Charge subscriptions reliably<br/>6 · Resilient"]
    W --> W4["Control AI spend<br/>12 · Model Router"]
    A --> A1["Plan the launch<br/>1 · Agent Loop"]
    A --> A2["Triage & measure support<br/>7 · Eval & Trace"]
    A --> A3["Answer from the orders data<br/>8 · Real SQLite"]
    AG --> G1["Run customer outreach<br/>2 · Agents SDK"]
    AG --> G2["Decide strategy<br/>3 · CrewAI"]
    AG --> G3["Publish with human sign-off<br/>9 · LangGraph"]
    AG --> G4["Tools for every agent<br/>4 · MCP"]
    AG --> G5["Fix the billing engine<br/>★ SWE flagship"]
    SAFE["🛡️ CROSS-CUTTING — guardrails: cost · loops · injection  (10 · Failure Modes)"]
    W -.-> SAFE
    A -.-> SAFE
    AG -.-> SAFE
    classDef obj fill:#fef3c7,stroke:#d97706,color:#78350f;
    classDef w fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef a fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef ag fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;
    classDef safe fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    class OBJ obj;
    class W,W1,W2,W3,W4 w;
    class A,A1,A2,A3 a;
    class AG,G1,G2,G3,G4,G5 ag;
    class SAFE safe;
"""

# Per-demo place in the Orbit flow: category + the business step it performs.
FLOW = {
    "1":  ("AI Agent",    "Plan the launch"),
    "5a": ("Workflow",    "Keep the platform healthy"),
    "5b": ("Workflow",    "Triage incidents at scale"),
    "2":  ("Agentic AI",  "Run customer outreach"),
    "3":  ("Agentic AI",  "Decide company strategy"),
    "4":  ("Agentic AI",  "Give every agent Orbit's tools"),
    "6":  ("Workflow",    "Charge subscriptions reliably"),
    "7":  ("AI Agent",    "Triage & measure support"),
    "8":  ("AI Agent",    "Answer questions from the orders data"),
    "9":  ("Agentic AI",  "Publish launch copy with human sign-off"),
    "10": ("Cross-cutting", "Keep the whole system safe"),
    "11": ("Agentic AI",  "Fix the billing engine autonomously"),
    "12": ("Workflow",    "Control AI spend"),
}

OVERVIEW_ARCH = """
flowchart LR
    IN["🧑 Goal — INPUT"] --> CTX["context / messages"]
    CTX --> BRAIN{{"BRAIN<br/>LLM · or · plain code"}}
    BRAIN -->|"act"| TOOLS["TOOLS (functions / APIs / MCP)"]
    TOOLS --> ENV[("world / state")]
    ENV -->|"observe → loop"| CTX
    BRAIN -->|"done"| OUT["✅ Result — OUTPUT"]
    classDef b fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef t fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef io fill:#fff7ed,stroke:#ea580c,color:#7c2d12;
    class BRAIN b;
    class TOOLS,ENV t;
    class IN,OUT io;
"""

OVERVIEW_MD_2 = r"""
### How to read the flow
Each tab is one step in running Orbit. For each: **read the architecture → check the
Input→Output contract → change the input → run it → watch the steps**. The three lanes:

- **⚙️ Workflows — you own the steps.** Keep the platform healthy (Native), triage incidents
  (Hybrid), charge subscriptions (Resilient), control AI spend (Model Router). Deterministic,
  cheap, testable; the model is optional.
- **🤖 AI Agents — one LLM drives a bounded task with tools.** Plan the launch (Agent Loop),
  triage & measure support (Eval & Trace), answer questions from the orders data (SQLite).
- **🧠 Agentic AI — autonomous, cooperating, stateful.** Run outreach (Agents SDK), decide
  strategy (CrewAI), publish with a human gate (LangGraph), share tools (MCP), and fix the
  billing engine end-to-end (SWE flagship).
- **🛡️ Cross-cutting — Failure Modes** shows the guardrails that keep the whole thing safe.

The progression is deliberate: as you move left→right, you hand more control to the model —
so you also add more guardrails. **Pick the least autonomy that solves the step.**

### Workflow vs. agent (when *not* to use one)

| | **Workflow** | **Agent** |
|---|---|---|
| Who controls the steps? | **You** (hard-coded) | **The model** |
| Predictability / cost | High / low | Lower / higher |
| Best for | Known, repeatable processes | Open-ended, unknown # of steps |

**Rule of thumb:** if a fixed script does the job, write the script. Use agency only when
the path can't be known in advance. (The Hybrid tab proves it with a live cost meter.)

### When to use which

| Need | Reach for | Tab |
|---|---|---|
| Deterministic / known playbook | a native rule, **not** an LLM ($0) | 1b · Native |
| Cap the cost of an LLM system | native-first routing | 1b · Hybrid |
| Learn / total control / tiny footprint | the raw loop | 1 · Agent Loop |
| Production multi-agent + handoffs | OpenAI Agents SDK | 2 · Agents SDK |
| "A team of personas," fast | CrewAI | 3 · CrewAI |
| Reusable tools across many agents | MCP (under any of the above) | 4 · MCP finale |

### Production depth (Act 2)

| Concern | The control / pattern | Tab |
|---|---|---|
| A tool call fails | retry transient · fail over · escalate (in code, not the model) | 6 · Resilience |
| "Is it actually any good?" | trace every run + score vs gold labels (eval in CI) | 7 · Eval & Trace |
| Touch real data safely | read-only guard + narrow typed write tool over a real DB | 8 · Real SQLite |
| Branching, loops, human sign-off | a checkpointed state machine with an approval gate | 9 · LangGraph |
| Cost blowups / loops / injection | budgets · cycle detection · trust boundary · allowlists | 10 · Prod failures |
"""

OVERVIEW_TYPES_MD = r"""
---

## The types of agent (and when each fits)

"Agent" is an umbrella over several quite different things. They differ in **what the 'brain'
is** and **how many of them there are** — not in whether they use AI (a native agent uses none).

| Type | The "brain" / structure | Strengths | Weaknesses | Tab |
|---|---|---|---|---|
| **Native / deterministic** | hand-written rules / policy — *no LLM* | $0, µs latency, 100% reproducible, unit-testable | can't handle novelty or fuzzy input; you must enumerate the logic | 1b · Native |
| **Hybrid (native-first)** | rules for the common case, LLM for the tail | most of the cost saving, keeps quality on hard cases | two paths + a router to maintain; misrouting risk | 1b · Hybrid |
| **Single LLM loop (tool-using)** | one LLM in a loop with tools | flexible; handles unknown step counts; simple | one context bottlenecks; no role separation; loop/cost risk | 1 · Agent Loop |
| **Multi-agent (code-first)** | coordinator + specialists via tools / handoffs | separation of concerns; per-agent prompt/model; control | more moving parts; orchestration is your code; latency | 2 · Agents SDK |
| **Declarative crew** | roles + tasks; the framework orchestrates | fastest way to express a 'team'; readable by non-engineers | least control; opaque debugging; verbose → costly | 3 · CrewAI |
| **Graph / state machine** | explicit nodes, edges, cycles, persisted state | branching/loops/human-in-the-loop; durable + resumable | most boilerplate; you own the state schema | 9 · LangGraph |
| **Conversational team** *(bonus)* | agents chat until a stop condition | great for free-form collaboration / simulation | hard to steer & terminate; less predictable; cost | (handout) |

**Rule of thumb:** pick the *least* powerful type that solves the problem — deterministic if you
can, a single loop before multi-agent, code-first before a graph — and add structure only when the
task forces it. More agency = more cost, latency, and surface area to get wrong.

## MCP — the tool standard (a different axis, not an agent type)

MCP (Model Context Protocol) isn't a way to *build* an agent — it's a standard way for agents to
**get tools**. Without it, every agent re-implements every integration: *M agents × N tools* of
glue. Publish each tool once as an **MCP server** and it becomes *M + N*: any MCP-aware client
(your agent, Claude Desktop, Cursor, an IDE) connects to it over stdio or HTTP. You layer it
**under** any framework above — that's what Demo 4 does inside an Agents-SDK agent.

| | Advantages | Disadvantages |
|---|---|---|
| **MCP** | tools reusable across agents *and* clients; versionable; independently deployable; a growing ecosystem of ready servers (GitHub, Slack, Postgres…) | another process + protocol to run, secure and version; auth/permissions become first-class; one extra network hop |

## Frameworks: advantages & disadvantages

All of these are *ergonomics over the same loop* (tab 1). Choose by how much control vs. convenience
the task needs.

| Framework | Advantages | Disadvantages | Reach for it when |
|---|---|---|---|
| **Raw loop** (OpenAI SDK) | total control; tiny footprint; nothing hidden; best for learning | you build retries, tracing, validation, parallelism by hand | learning, or you want full control / minimal deps |
| **OpenAI Agents SDK** | code-first control *plus* tools, agents-as-tools, handoffs, guardrails, structured output | hosted tracing is OpenAI-only (disable on Azure); orchestration is still your code; young ecosystem | production multi-agent where you want to keep Python control flow |
| **CrewAI** | declarative; fastest to express a 'team of personas'; readable | low control; opaque debugging; verbose runs get costly; fast-moving API | prototyping a role-based crew quickly |
| **LangGraph** | explicit graph; cycles; durable checkpointed state; first-class human-in-the-loop; testable | steeper learning curve; more boilerplate; you design the state schema | deterministic branching/looping, memory, approvals |
| **AutoGen** *(bonus)* | strong for free-form multi-agent *conversation* / research; group chat | harder to steer & terminate; less predictable; cost | open-ended agent-to-agent collaboration |

👉 **Before the live demos, click *Check Azure connection* below**, then open a tab.
"""


# =====================================================================
# Build the UI
# =====================================================================
def _make_input_component(spec):
    kind = spec["kind"]
    label = spec["label"]
    if kind == "number":
        return gr.Number(value=spec.get("value", 0), label=label)
    if kind == "bool":
        return gr.Checkbox(value=bool(spec.get("value", False)), label=label)
    if kind == "choice":
        return gr.Radio(choices=spec["choices"], value=spec.get("value"), label=label)
    if kind == "textarea":
        return gr.Textbox(value=spec.get("value", ""), label=label,
                          lines=spec.get("lines", 2), placeholder=spec.get("placeholder", ""))
    return gr.Textbox(value=spec.get("value", ""), label=label,
                      placeholder=spec.get("placeholder", ""))


def build_ui() -> "gr.Blocks":
    with gr.Blocks(title="Agentic AI Masterclass") as demo:
        with gr.Tabs():
            # ---------- Overview ----------
            with gr.Tab("📖 Overview"):
                gr.Markdown(OVERVIEW_MD)
                with gr.Accordion(
                    "📚 New to the terms? Plain-language primer — Workflow · AI Agent · Agentic AI · MCP · LangGraph",
                    open=True,
                ):
                    render_markdown_with_mermaid(read_markdown("Understanding-Agentic-AI-Explainer.md"))
                gr.Markdown("### 🗺️ The complete flow — one objective, three categories, every demo a step")
                gr.HTML(mermaid(OVERVIEW_FLOW))
                gr.Markdown("### The shared mechanism every step is built on")
                gr.HTML(mermaid(OVERVIEW_ARCH))
                gr.Markdown(OVERVIEW_MD_2)
                gr.Markdown(OVERVIEW_TYPES_MD)
                azure_btn = gr.Button("🔌 Check Azure connection (runs smoke_test.py)", variant="primary")
                azure_out = gr.Textbox(label="Azure connectivity", lines=8, max_lines=8,
                                       autoscroll=True, buttons=["copy"],
                                       placeholder="Confirm your deployment is reachable before the live demos.")
                azure_btn.click(check_azure, inputs=None, outputs=azure_out)

            # ---------- One tab per demo ----------
            for d in DEMOS:
                dd = DEEP_DIVE.get(d["id"], {})
                with gr.Tab(d["tab"]):
                    needs = "Azure OpenAI (.env)" if d["needs_azure"] else "nothing — no API key"
                    cat, step = FLOW.get(d["id"], ("", ""))
                    flow_line = f"🏢 **Orbit flow:** {cat} — *{step}*\n\n" if step else ""
                    gr.Markdown(
                        f"## {d['title']}\n\n"
                        f"{flow_line}"
                        f"**Agent type:** {d['agent_type']}  \n"
                        f"**Framework:** {d['framework']}  \n"
                        f"**Needs:** {needs}  ·  **Cost:** {d['cost']}  ·  **Runtime:** {d['runtime']}\n\n"
                        f"{d['teaches']}"
                    )

                    if dd.get("objective"):
                        gr.Markdown(f"### 🎯 Objective\n{dd['objective']}")

                    gr.Markdown("### 🧭 Architecture & data flow")
                    gr.HTML(mermaid(d["architecture"]))
                    gr.Markdown("**Layers**\n" + "\n".join(f"- {l}" for l in d["layers"]))

                    if dd.get("use_cases"):
                        gr.Markdown("### 🌍 Where this is used in the real world\n"
                                    + "\n".join(f"- {u}" for u in dd["use_cases"]))
                    if dd.get("why"):
                        gr.Markdown(f"### 🧠 Why this approach (and the trade-offs)\n{dd['why']}")

                    contract_md = "\n".join(
                        ("> " + ln) if ln.strip() else ">" for ln in d["contract"].split("\n")
                    )
                    gr.Markdown(
                        f"### 🔌 Contract\n\n{contract_md}\n\n*What to watch:* {d['watch']}"
                    )

                    gr.Markdown("### ▶ Run it — change the input, then run")
                    input_components = [_make_input_component(s) for s in d["inputs"]]
                    run_btn = gr.Button(f"▶ Run {d['title'].split('—')[0].strip()}", variant="primary")
                    out = gr.Textbox(
                        label="Live output (streamed verbatim from the real script)",
                        lines=24, max_lines=24, autoscroll=True, buttons=["copy"],
                        placeholder="Adjust the input above, then click ▶ Run to launch the real script and stream its output here.",
                    )
                    run_btn.click(make_runner(d), inputs=input_components, outputs=out)

                    if dd.get("improve"):
                        gr.Markdown("### 🚀 How to take this to production\n"
                                    + "\n".join(f"- {i}" for i in dd["improve"]))

                    with gr.Accordion("📄 View source — the architecture above is exactly this code", open=False):
                        gr.Code(value=read_source(d["script"]), language="python", label=d["script"])

                    gr.Markdown(f"**When you'd reach for this:** {d['when']}")

        gr.Markdown(
            "---\nBuilt from [ed-donner/agents](https://github.com/ed-donner/agents), adapted for Azure OpenAI. "
            "Deeper reference: `PARTICIPANT_HANDOUT.md` (cheat-sheets, glossary) · `FACILITATOR_GUIDE.md` (run sheet)."
        )
    return demo


if __name__ == "__main__":
    app = build_ui()
    app.queue()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,
        show_error=True,
        theme=gr.themes.Soft(),
        css=CSS,
        head=MERMAID_HEAD,
    )
