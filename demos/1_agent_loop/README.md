# Demo 1 — The Agent Loop (no framework)

**Agent type:** the raw pattern underneath *every* framework.
**Source:** `ed-donner/agents` → `1_foundations` (labs 4 & 5).

## The one idea
> An agent is just an **LLM in a loop, with tools, that decides when it's done.**

```
┌─────────────────────────────────────────────┐
│  while True:                                 │
│     reply = LLM(messages, tools)             │
│     if reply asks for a tool:                │
│         run tool → append result → continue  │
│     else:                                    │
│         return reply   # the agent is done   │
└─────────────────────────────────────────────┘
```

## What it shows live
- The model is handed two tools (`add_todos`, `complete_todo`) as JSON schemas.
- Given a goal, it **plans** (adds todos), then **executes** (works each step,
  marking it complete), then **stops on its own** and summarises.
- Every turn of the loop is printed, so the audience literally watches the agent
  think → act → observe → repeat.

## Run
```bash
python demos/1_agent_loop/agent_loop.py
```

## Talking points
- No framework, no magic — ~120 lines of plain Python + the OpenAI SDK.
- The LLM never runs code; it *requests* tool calls and we execute them. The
  "agency" is the loop deciding to keep going.
- This is exactly the loop Claude Code, Cursor, and ChatGPT tools run.

## Application
Planning/research assistants, "do this multi-step task" copilots, any workflow
where the number of steps isn't known in advance.
