# Participant Handout — Agentic AI Masterclass

Your take-home reference. Concepts first, then a one-page cheat-sheet per framework,
a "when to use which" guide, the Azure adaptation recipe, a glossary, and links.

---

## 1. The one idea

> **An agent is an LLM in a loop, with tools, that decides for itself when it's done.**

```
        ┌──────────────────────────────────────────────┐
        │   messages ──►  LLM  ──►  wants a tool?        │
        │                          │            │       │
        │                       yes│         no │       │
        │                          ▼            ▼       │
        │                run tool, append    return     │
        │                result, loop back   answer     │
        └──────────────────────────────────────────────┘
```

- A **plain LLM call** is one-shot: prompt in, text out.
- An **agent** can *act* (call tools), *observe* results, and *act again* — a feedback
  loop. The model decides the next step; your code executes tools and feeds results back.
- The model **never runs your code** — it only *requests* a tool call (by name + JSON
  arguments). Your code chooses whether/how to run it. That boundary is where you put
  validation, permissions, and logging.

---

## 2. Workflows vs. agents (and when NOT to use an agent)

From Anthropic's *Building Effective Agents*:

| | **Workflow** | **Agent** |
|---|---|---|
| Who controls the steps? | **You** (hard-coded) | **The model** |
| Predictability | High | Lower |
| Cost / latency | Lower | Higher (more LLM calls) |
| Best for | Known, repeatable processes | Open-ended tasks, unknown # of steps |

**Rule of thumb:** if a fixed script does the job, write the script. Use agency only
when the path can't be known in advance. Most production "agents" are mostly workflow
with a little agency at the edges.

Common workflow patterns worth knowing (all in the source course's `1_foundations`):
- **Prompt chaining** — output of one call feeds the next.
- **Routing** — classify, then send to a specialized handler.
- **Parallelization** — fan out, then aggregate.
- **Evaluator–optimizer** — one model generates, another critiques, loop until good.

---

## 3. The framework landscape

| Framework | Philosophy | You write… | Sweet spot |
|---|---|---|---|
| **(native rules)** | Deterministic, **no LLM** | A policy/rule cascade | Known playbooks; $0/decision; speed + testability |
| **(raw loop)** | No framework | The loop yourself | Learning; total control; tiny footprint |
| **OpenAI Agents SDK** | Code-first agents | Agents + tools + handoffs in Python | Production multi-agent, full control |
| **CrewAI** | Declarative crews | Roles, goals, tasks | "Team of personas" fast |
| **LangGraph** *(bonus)* | Graph / state machine | Nodes + edges + state | Branching, stateful, human-in-the-loop |
| **AutoGen** *(bonus)* | Conversational teams | Agents that chat in a group | Free-form multi-agent collaboration |
| **MCP** | Tool standard | Tool *servers* | Reusable tools across many agents/clients |

MCP is a different axis: it's not an agent framework, it's how agents *get tools*.
You layer it **under** any of the above.

---

## 4. Cheat-sheets (the 3 core demos)

### 4a. The raw agent loop (Demo 1)
```python
while True:
    resp = client.chat.completions.create(model=DEPLOYMENT, messages=messages, tools=TOOLS)
    choice = resp.choices[0]
    if choice.finish_reason != "tool_calls":
        return choice.message.content          # agent decided it's done
    messages.append(choice.message)
    for call in choice.message.tool_calls:     # run every requested tool
        result = TOOL_FUNCS[call.function.name](**json.loads(call.function.arguments))
        messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
```
- Tools are declared as JSON schemas; you dispatch by name.
- **Everything below is ergonomics over this.**

### 4b. OpenAI Agents SDK (Demo 2)
```python
from agents import Agent, Runner, function_tool

@function_tool
def send_email(subject: str, body: str) -> dict: ...        # a TOOL

specialist = Agent(name="sdr", instructions="...", model=model)
manager = Agent(
    name="manager",
    instructions="...",
    tools=[specialist.as_tool(tool_name="sdr", tool_description="...")],  # AGENT-AS-TOOL
    handoffs=[emailer_agent],                                            # HANDOFF
    model=model,
)
result = await Runner.run(manager, "do the thing")
```
| Concept | Meaning |
|---|---|
| **Tool** | A function the agent can call (returns control to the agent). |
| **Agent-as-tool** | Wrap a whole agent as a callable for another agent. |
| **Handoff** | Transfer the conversation (and control) to another agent. |
| **Guardrail** | A check that can block an input/output (e.g. PII). |
| **Structured output** | `output_type=PydanticModel` → validated JSON back. |

### 4c. Native & hybrid agents — agentic ≠ AI-dependent (Demo 1b)
The agent loop doesn't care what the "brain" is. Swap the LLM for deterministic code
and you get a **native agent**: $0/decision, instant, fully testable.
```python
def decide(state):                      # the brain — pure code, no tokens
    if not state.service_up: return "restart_service"
    if state.disk > 90:      return "clear_logs"
    if state.cpu > 80:       return "scale_out"
    return "DONE"
# same perceive -> decide -> act -> observe loop as Demo 1
```
**Hybrid (the production pattern):** native rules handle the known cases for free;
escalate to the LLM only for the novel/ambiguous long tail.
```python
if alert_type in RULES:                 # ~90% of traffic: $0, instant
    action = RULES[alert_type]
else:                                    # rare unknowns: pay the model
    action = decide_with_llm(alert_type, description)
```
| | Native (rules) | LLM | Hybrid |
|---|---|---|---|
| Cost/decision | **$0** | tokens ≈ ¢ | mostly $0 |
| Latency | µs | round-trip | mixed |
| Testable | ✅ | ❌ stochastic | ✅ (rule path) |
| Novel cases | ❌ | ✅ | ✅ (escalates) |

> **Don't pay a model to make a decision a rule already knows.** In the demo, 10 of 12
> incidents were resolved by free rules → ~83% fewer LLM calls.

### 4d. CrewAI (Demo 3)
```python
from crewai import Agent, Task, Crew, Process, LLM
llm = LLM(model="azure/gpt-4o-mini")

debater = Agent(role="A compelling debater", goal="Argue the motion: {motion}",
                backstory="...", llm=llm)
propose = Task(description="Argue FOR {motion}", expected_output="...", agent=debater)
crew = Crew(agents=[debater, judge], tasks=[propose, oppose, decide],
            process=Process.sequential)
crew.kickoff(inputs={"motion": "..."})
```
- You **declare** agents (role/goal/backstory) and tasks; CrewAI runs them.
- `Process.sequential` (in order) vs `Process.hierarchical` (a manager delegates).
- Each agent can use a **different model/provider**. The course also uses YAML config
  files (`agents.yaml`, `tasks.yaml`) instead of inline Python.

---

## 4.5 Production-depth patterns (Demos 6–10) — the senior track

Foundations tell you *what the categories are*. These five tell you *how to operate one in
production*. The throughline: **the hard parts live in the orchestration layer, not in the
prompt.**

### 4.5a Resilience — tools fail (Demo 6)
Never ask the model "should I retry?". Wrap the tool in code:
```python
def call_with_retry(provider, *a):
    for attempt in range(1, MAX+1):
        try: return provider(*a)
        except PermanentError: raise            # 4xx/declined → fail fast, do NOT retry
        except TransientError:                  # 5xx/timeout → back off and retry
            if attempt == MAX: raise
            time.sleep(base * 2**(attempt-1))   # exponential backoff (+ jitter)
# orchestration: try primary → on failure fail over to secondary → else ESCALATE (never drop)
```
- **Classify errors by type** — transient (retry) vs permanent (fail fast). This is the key decision.
- **Fallback** then **escalate** to a durable queue; a dropped request is the worst outcome.

### 4.5b Eval & trace — "is it actually any good?" (Demo 7)
A single happy-path run tells you nothing. You need:
- a **trace** per run (latency, tokens, raw output) → your observability data;
- an **eval set** (inputs + gold labels) scored two ways: a **deterministic check** (free, reliable)
  anchored by an **LLM-as-judge** (catches quality a string match can't);
- a **scorecard** (accuracy, p50/p95 latency, $, judge avg) you **diff across changes and run in CI.**
> If you change a prompt or model and can't show the scorecard moved, you're guessing.

### 4.5c Touching real data safely (Demo 8)
The moment an agent can hit a datastore, add guardrails at the **tool boundary**:
- **Read** via a tool restricted to a single read-only `SELECT` (no DDL/DML, no `;` stacking).
- **Write** only through **narrow, typed, parameterised** tools (`record_refund(order_id)`), never
  a "run arbitrary SQL" tool. The model chooses *what*, your code owns *how*. That keeps
  `DROP TABLE` impossible by construction.

### 4.5d Stateful control + human-in-the-loop — LangGraph (Demo 9)
When "call some tools" isn't enough, model the flow as a graph:
```python
g.add_conditional_edges("evaluate", route, {"generate": "generate", "gate": "gate"})  # retry-until-criteria
# gate node: decision = interrupt({...})   ← graph PAUSES, state is checkpointed
graph = g.compile(checkpointer=MemorySaver())
# resume later, possibly from another process:  graph.invoke(Command(resume="approve"), config)
```
- **Cycles with a max-iteration cap** = evaluator-optimizer that can't loop forever.
- **`interrupt()` + checkpointer** = a real human approval gate before consequential actions.

### 4.5e Failure modes + guards (Demo 10) — what pages you at 2am
| Failure | Guard (engineering, not prompting) |
|---|---|
| **Cost blowup** (runaway loop/tokens) | a cumulative **token/cost budget** checked every turn → abort |
| **Infinite loop** (impossible/oscillating goal) | **max-turn cap** + **cycle detector** (revisited state ⇒ stop) |
| **Prompt injection via tool output** | treat tool output as **untrusted DATA**, never instructions |
| **Destructive action** | gate dangerous tools behind an **out-of-band allowlist** the model can't grant |
> Defense in depth: even if the model is fooled into *requesting* a destructive action, the
> orchestration refuses it. Safety is a property of your code, not the model's goodwill.

---

## 5. Cheat-sheets (bonus frameworks — for going further)

### 5a. LangGraph — agents as state machines
```python
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

class State(TypedDict):
    messages: Annotated[list, add_messages]

g = StateGraph(State)
g.add_node("chatbot", lambda s: {"messages": [llm_with_tools.invoke(s["messages"])]})
g.add_node("tools", ToolNode(tools))
g.add_conditional_edges("chatbot", tools_condition)   # branch: tool call? → tools
g.add_edge("tools", "chatbot")
g.add_edge(START, "chatbot")
graph = g.compile(checkpointer=MemorySaver())         # persistent memory per thread_id
```
- You draw the control flow as a **graph**: nodes (steps) + edges (transitions),
  including **conditional** edges and **cycles**.
- **Checkpointing** gives memory across turns; supports human-in-the-loop pauses.
- Best when you need explicit, testable, branching/looping control — e.g. a
  worker→tools→evaluator loop that retries until success criteria are met.

### 5b. Microsoft AutoGen — conversational agent teams
```python
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination

writer = AssistantAgent("writer", model_client=client, tools=[...])
critic = AssistantAgent("critic", model_client=client,
                        system_message="Reply 'APPROVE' when satisfied.")
team = RoundRobinGroupChat([writer, critic],
                           termination_condition=TextMentionTermination("APPROVE"))
await team.run(task="Write and refine a poem.")
```
- Agents **talk to each other** until a termination condition is met.
- `AgentChat` = high-level teams; `Core` = low-level message-passing / distributed agents.
- Best for free-form collaboration, generator/critic loops, simulations.

---

## 6. When to use which (decision guide)

```
Is the decision deterministic / a known playbook?  ──► native rule, NOT an LLM ($0)

Need reusable tools across many agents/clients?  ──► add MCP (under anything below)

Just learning, or want total control / minimal deps?  ──► raw loop

Production multi-agent, code-first, want handoffs & guardrails?  ──► OpenAI Agents SDK

Want to express "a team of role-playing specialists" fast?  ──► CrewAI

Need deterministic branching/looping, state, memory, human-in-the-loop?  ──► LangGraph

Want agents to collaborate via open-ended conversation?  ──► AutoGen
```
They mix: e.g. an OpenAI Agents SDK agent that consumes MCP tools (that's Demo 4).

---

## 7. Running on Azure OpenAI — the recipe

In Azure, the **model you call is the *deployment name*** you created in the portal
(not necessarily the base model name). Set these once in `.env`:
```
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
```

| Stack | How to point it at Azure |
|---|---|
| **OpenAI SDK** (Demo 1) | `AzureOpenAI(azure_endpoint=, api_key=, api_version=)`; `model=DEPLOYMENT` |
| **OpenAI Agents SDK** (Demos 2, 4) | `AsyncAzureOpenAI(...)` → `OpenAIChatCompletionsModel(model=DEPLOYMENT, openai_client=...)`; `set_tracing_disabled(True)` |
| **CrewAI** (Demo 3) | set `AZURE_API_KEY/AZURE_API_BASE/AZURE_API_VERSION`; `LLM(model="azure/<deployment>")` |
| **LangGraph** (bonus) | `AzureChatOpenAI(azure_endpoint=, api_key=, api_version=, model=DEPLOYMENT)` |
| **AutoGen** (bonus) | `AzureOpenAIChatCompletionClient(model=DEPLOYMENT, azure_endpoint=, api_key=, api_version=)` |

**Gotchas:**
- The Agents SDK's hosted **tracing** needs an OpenAI (not Azure) key → disable it.
- `WebSearchTool` and other OpenAI-*hosted* tools don't run on Azure → use function
  tools or MCP instead.
- Prefer `gpt-4o-mini` / `gpt-4.1-mini` for reliable tool-calling.

---

## 8. Glossary
- **Agent** — a system that loops with tools and decides when it's finished. The "brain" is usually an LLM, but can be plain code.
- **Native agent** — an agent whose decision logic is deterministic code (rules/policy), not an LLM. Zero token cost, instant, fully testable.
- **Hybrid agent** — native rules for the common cases, escalating to an LLM only for novel/ambiguous ones, to keep cost down.
- **Tool / function calling** — a function described to the model as JSON; the model
  requests it, your code runs it.
- **Agent-as-tool** — exposing an agent so another agent can call it like a function.
- **Handoff** — transferring control of a conversation from one agent to another.
- **Guardrail** — a validation step that can block unsafe input/output.
- **Structured output** — forcing the model to return JSON matching a schema (Pydantic).
- **State / checkpointing** — persisted conversation/graph state (LangGraph memory).
- **Crew / role-goal-backstory** — CrewAI's declarative way to define agents.
- **MCP (Model Context Protocol)** — an open standard for exposing tools/resources to
  any agent; "USB-C for AI tools."
- **MCP server / stdio transport** — a process that publishes tools; the agent talks
  to it over stdin/stdout (or HTTP/SSE).
- **Deployment (Azure)** — the named instance of a model you call by name.

---

## 9. Resources
- **Source course:** ed-donner/agents — <https://github.com/ed-donner/agents>
  (the full 6-week version, incl. LangGraph & AutoGen weeks)
- **Anthropic — Building Effective Agents:** <https://www.anthropic.com/engineering/building-effective-agents>
- **OpenAI Agents SDK docs:** <https://openai.github.io/openai-agents-python/>
- **CrewAI docs:** <https://docs.crewai.com/>
- **LangGraph docs:** <https://langchain-ai.github.io/langgraph/>
- **Microsoft AutoGen docs:** <https://microsoft.github.io/autogen/>
- **Model Context Protocol:** <https://modelcontextprotocol.io/>
- **Azure OpenAI docs:** <https://learn.microsoft.com/azure/ai-services/openai/>

---

## 10. Try it yourself (after the session)
1. **Demo 1:** add a third tool (e.g. a calculator) and give the agent a goal that needs it.
2. **Demo 2:** add an `input_guardrail` that blocks emails mentioning a competitor.
3. **Demo 3:** change the `motion`; give the judge a different deployment.
4. **Demo 4:** add a `get_share_price` tool to the MCP server and ask the agent to
   value Alice's portfolio. Notice you changed *only the server* — the agent code is untouched.
