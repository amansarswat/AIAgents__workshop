# Demo 2 — OpenAI Agents SDK: a multi-agent sales team

**Agent type:** code-first, multi-agent orchestration with handoffs.
**Source:** `ed-donner/agents` → `2_openai` (lab 2).

## What it shows live
A Sales Manager agent that:
1. calls **three SDR agents-as-tools** (professional / witty / concise) to draft cold emails,
2. **picks the best draft**, then
3. **hands off** the whole conversation to an Emailer agent, which writes a subject
   line and "sends" the email (stubbed to `sent_email.txt` — no SendGrid needed).

```
                 ┌── professional_sdr (as tool) ┐
 Sales Manager ──┼── witty_sdr        (as tool) ┤── picks best ──► HANDOFF ──► Emailer ──► send_email()
                 └── concise_sdr      (as tool) ┘
```

## Three concepts in ~80 lines
| Concept | In the code | Why it matters |
|---|---|---|
| **Tool** | `@function_tool def send_email(...)` | Give an agent real-world actions |
| **Agent-as-tool** | `sdr_professional.as_tool(...)` | Compose specialists under a coordinator |
| **Handoff** | `handoffs=[emailer]` | Pass control (and context) to another agent |

## Run
```bash
python demos/2_openai_agents_sdk/sales_team.py
```
Output prints the manager's reasoning and the final email written to `sent_email.txt`.

## Azure notes
- We wrap `AsyncAzureOpenAI` in `OpenAIChatCompletionsModel` and pass it to every Agent.
- `set_tracing_disabled(True)` — the SDK's hosted trace viewer needs an OpenAI key, not Azure.
- We avoid `WebSearchTool` (an OpenAI-hosted tool that doesn't run on Azure).

## Application
SDR / outreach automation, tiered support (triage → specialist), any "manager
delegates to specialists" workflow.
