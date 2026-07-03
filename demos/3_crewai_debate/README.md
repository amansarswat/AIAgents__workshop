# Demo 3 — CrewAI: a role-playing crew that debates

**Agent type:** declarative, role-based "crew" of collaborators.
**Source:** `ed-donner/agents` → `3_crew/debate`.

## The contrast with Demo 2
In the OpenAI SDK you **write orchestration code**. In CrewAI you **declare a cast**
— each agent has a `role`, `goal`, `backstory` — plus a list of tasks, and the
framework runs them. Less control, faster to express "a team of personas".

## What it shows live
Two agents, three sequential tasks:
```
debater  ─ task 1 ─►  argue FOR the motion
debater  ─ task 2 ─►  argue AGAINST the motion
judge    ─ task 3 ─►  read both, declare a winner
```
Run it and watch CrewAI's verbose log show each agent "thinking" in character.

## Run
```bash
python demos/3_crewai_debate/debate.py
```
Change the `motion` string at the bottom to debate anything.

## Azure notes
- CrewAI uses **LiteLLM** under the hood. For Azure it reads `AZURE_API_KEY`,
  `AZURE_API_BASE`, `AZURE_API_VERSION` — we translate those from your
  `AZURE_OPENAI_*` vars at the top of `debate.py`.
- The model string is **`azure/<deployment-name>`** (here `azure/gpt-4o-mini`).
- The original course gives the judge an Anthropic Claude model — a nice CrewAI
  feature (mix providers per agent). We use Azure for both since that's your key.

## ⚠️ Windows install gotcha
CrewAI pulls in `chromadb`, which needs **Microsoft C++ Build Tools** to compile.
If `pip install crewai` fails on Windows, install the Build Tools (see `SETUP.md`).
This is the only demo with a heavier install — Demos 1, 2, 4 are clean.

## Application
"Panel of experts" workflows: debate/red-team, research crews, content pipelines
(researcher → writer → editor), where you think in terms of roles, not code.
