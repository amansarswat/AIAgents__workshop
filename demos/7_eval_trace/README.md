# Demo 7 — Eval & Trace (the part that actually ships agents)

**Act 2 — Production depth.** *Needs Azure.*
**Agent type:** measure it — trace every run, score against gold labels.

## The one idea
> A single happy-path run tells you nothing. You ship on a **scorecard** you can diff
> across prompt/model changes and run in CI.

## What it shows live
- An agent under test (support-ticket triage → JSON `{category, priority, justification}`).
- A **trace** per run: latency, prompt/completion tokens, raw output (your observability data).
- Two scorers: a **deterministic check** (predicted category == gold; free, 100% reliable) and an
  **LLM-as-judge** (rates the justification 1–5; catches quality a string match can't).
- A **scorecard**: accuracy, avg judge score, p50/p95 latency, tokens, $ cost.

## Run
```bash
python demos/7_eval_trace/eval_trace.py
DEMO_EVAL_TICKET="My invoice shows the wrong VAT rate" DEMO_EVAL_EXPECT=billing python ...
```

## Talking points
- The eval set (inputs + gold labels) is the asset that makes iteration possible.
- Anchor the (fallible, paid) LLM-judge with a (free, reliable) deterministic check.
- Wire the trace into real observability; gate merges on the scorecard, not vibes.

## Application
Any agent you intend to ship: regression-test prompts/models, catch drift, prove improvements.
