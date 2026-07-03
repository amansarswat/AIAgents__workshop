# Setup Guide

Do this **before** the demo — ideally a day ahead so any install gremlins
are caught early. Total time: ~15 minutes (longer if CrewAI build tools are needed).

---

## 0. Prerequisites
- **Python 3.10–3.12** (`python --version`). This pack was built and tested on 3.10.
- **An Azure OpenAI resource** with a chat deployment. The demos default to a
  deployment named `gpt-4o-mini` (most reliable for tool-calling). `gpt-4.1-mini`
  also works. Reasoning models like `gpt-5-mini` work too but may need a newer API
  version — start with `gpt-4o-mini`.
- (Windows + CrewAI only) **Microsoft C++ Build Tools** — see step 5.

---

## 1. Rotate your Azure keys first 🔐
If your keys were ever shared (chat, email, a screenshot), regenerate them:
**Azure Portal → your Azure OpenAI resource → Keys and Endpoint → Regenerate Key**.
Use the new key below. Keys live only in `.env`, which is git-ignored.

---

## 2. Create a virtual environment
```bash
cd AIAgents__workshop
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate
```

---

## 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
This installs: `openai`, `openai-agents`, `crewai`, `litellm`, `azure-ai-inference`,
`mcp`, `python-dotenv`. (CrewAI 1.x needs `litellm` + `azure-ai-inference` present to
route Azure — the demo forces the LiteLLM path, which is the one verified to work
with `*.cognitiveservices.azure.com` endpoints.)

> If you only want the **clean core** (Demos 1, 2, 4) and want to skip CrewAI's
> heavier install, you can comment out the `crewai` line in `requirements.txt`.

---

## 4. Configure your `.env`
```bash
cp .env.example .env       # Windows: copy .env.example .env
```
Open `.env` and fill in (deployment = the name you gave it in the Azure portal):
```
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=your-rotated-key
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
```
The `cognitiveservices.azure.com` and `openai.azure.com` endpoint styles both work.

---

## 5. (Windows + CrewAI) Microsoft C++ Build Tools
CrewAI depends on `chromadb`, which compiles native code. If `pip install crewai`
errors with a `chroma` / build / `cl.exe` failure:
1. Download **Build Tools for Visual Studio** (Microsoft).
2. In the installer tick **"Desktop development with C++"**.
3. Reopen your terminal and re-run `pip install -r requirements.txt`.

If you'd rather not deal with this on the day, run Demos 1, 2, and 4 (which don't
need CrewAI) and *show* the CrewAI code + a pre-recorded run for Demo 3.

---

## 6. Smoke test (do this to confirm everything)
```bash
python smoke_test.py
```
Expected:
```
Endpoint  : https://...cognitiveservices.azure.com
Deployment: gpt-4o-mini
✅ Response: Azure OK
Azure OpenAI is reachable. You're ready for the demo.
```
If this passes, **all four demos will connect** — they share the same wiring.

---

## 7. Pre-run each demo once (recommended)
```bash
# Act 1 — Foundations
python demos/1_agent_loop/agent_loop.py
python demos/5_native_agents/native_agent.py   # no Azure needed ($0, deterministic)
python demos/5_native_agents/hybrid_agent.py   # native-first + LLM escalation, cost meter
python demos/2_openai_agents_sdk/sales_team.py
python demos/3_crewai_debate/debate.py        # skip if you didn't install CrewAI
python demos/4_mcp_trading/mcp_agent.py

# Act 2 — Production depth
python demos/6_resilient_agent/resilient_agent.py   # no Azure needed ($0, deterministic)
python demos/7_eval_trace/eval_trace.py
python demos/8_sqlite_agent/sqlite_agent.py
python demos/9_langgraph_workflow/langgraph_workflow.py
python demos/10_failure_modes/failure_modes.py
```
Pre-running warms caches, confirms tool-calling works on your deployment, and lets
you delete demo output (`sent_email.txt`, `accounts.json`, `shop.db`) for a clean live run.

Or skip the terminal entirely and drive everything from the UI: **`python app.py`**.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `DeploymentNotFound` / 404 | `AZURE_OPENAI_CHAT_DEPLOYMENT` must match the deployment name in the portal exactly. |
| `Unsupported API version` | Try `2024-10-21` (GA) or, for reasoning models, `2024-12-01-preview`. |
| Tool calls never happen | Use `gpt-4o-mini`/`gpt-4.1-mini`; some deployments/older API versions handle tools poorly. |
| Agents SDK tries to reach OpenAI | Confirm `set_tracing_disabled(True)` ran and each Agent has `model=model`. |
| CrewAI `chromadb` build error (Windows) | Install C++ Build Tools (step 5). On recent Python (3.10–3.12) chromadb ships prebuilt wheels and this usually doesn't happen. |
| CrewAI `Azure AI Inference native provider not available` | `pip install -r requirements.txt` again — `litellm` and `azure-ai-inference` must both be installed. |
| CrewAI pauses with "view execution traces? [y/N]" | Already disabled in `debate.py` and `.env.example` (`CREWAI_TRACING_ENABLED=false`). |
| MCP demo hangs on Windows | Ensure you run with the venv's Python; the server is launched via `sys.executable`. Delete `accounts.json` and retry. |
| Emoji `UnicodeEncodeError` on Windows console | The scripts force UTF-8 stdout; if a custom shell still errors, run `set PYTHONUTF8=1` first. |
| `KeyError: 'AZURE_OPENAI_ENDPOINT'` | `.env` not found/filled. Run from the project root, confirm `.env` exists. |
