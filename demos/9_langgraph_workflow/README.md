# Demo 9 — LangGraph: retry-until-criteria + a human approval gate

**Act 2 — Production depth.** *Needs Azure (uses `langchain-openai`'s `AzureChatOpenAI`).*
**Agent type:** a stateful graph — explicit nodes, conditional edges, cycles, checkpointed pause/resume.

## The one idea
> When "an agent that calls some tools" isn't enough, model the flow as a graph you can see and
> control — including the ability to **pause for a human** before a consequential action.

```
START ─► generate ─► evaluate ──(score < bar AND iters < max)──► generate   (retry-until-criteria)
                         │ meets bar / max iters
                         ▼
                    ⏸ human gate  (interrupt → state checkpointed → resume on decision)
                    approve ─► publish ✅     reject ─► not published
```

## What it shows live
- **Evaluator–optimizer:** the draft is regenerated *with the judge's feedback* until it clears a
  quality bar — capped by a max-iteration count so it can never loop forever.
- **Human-in-the-loop:** `interrupt()` truly pauses the graph (state persisted via a checkpointer);
  it resumes only when a decision is supplied — potentially from a different process, hours later.

## Run
```bash
python demos/9_langgraph_workflow/langgraph_workflow.py
DEMO_APPROVE=reject python ...     # clears the bar but nothing publishes
DEMO_BAR=2 python ...              # lower bar → passes in one iteration
```

## Talking points
- Cycles + a cap = controllable self-improvement, not an open-ended loop.
- `interrupt()` + `MemorySaver` is the real HITL primitive — durable, resumable approval gates.
