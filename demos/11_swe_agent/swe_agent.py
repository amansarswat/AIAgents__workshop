"""
FLAGSHIP DEMO — AUTONOMOUS SWE AGENT: fix a real bug, verified by a real test suite
===================================================================================
An agent with real tools, an objective success criterion, and guardrails — a mini
Claude-Code that fixes a real bug and proves it against a real test suite.

The agent is dropped into a real (sandboxed) Python project whose test suite is RED.
With nothing but tools — list files, read a file, edit a file, run the tests — it has
to investigate the failures, fix the **source code**, and re-run until the suite is
GREEN. Then it stops.

What makes this production-grade rather than a demo trick:

  • OBJECTIVE GROUND TRUTH — success is "pytest exits 0", checked by the harness. The
    agent does NOT get to *declare* victory; if it says "done" while tests are red, the
    harness pushes it back. No grading itself.
  • ANTI-REWARD-HACKING — the obvious cheat is to edit the failing tests. The tool layer
    REFUSES any write to `test_*.py`. The agent must fix the real bug, not the goalposts.
  • SANDBOXED FILE I/O — every path is resolved and confined to the workspace; traversal
    (`../../etc/...`) is rejected. Tests run in a subprocess with a timeout. No network.
  • BOUNDED — a hard iteration cap so a stuck agent can't loop (or bill) forever.
  • OBSERVABLE — every tool call, tokens and latency are traced; the run ends with the
    unified DIFF the agent produced and a before→after test scorecard.

The bug is realistic: a volume-discount pricing engine using `>` where the finance spec
says `>=`, so customers exactly on a tier boundary are silently under-discounted — the
kind of off-by-one that leaks revenue in production.

Run:  python demos/11_swe_agent/swe_agent.py     (needs your Azure .env + pytest)
"""

import os
import re
import sys
import json
import time
import shutil
import difflib
import subprocess
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
from openai import AzureOpenAI

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORKSPACE = HERE / "_workspace"
load_dotenv(ROOT / ".env")

client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
)
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
PRICE_IN, PRICE_OUT = 0.15 / 1_000_000, 0.60 / 1_000_000


# =====================================================================
# THE PROJECT UNDER REPAIR — written fresh into the sandbox on every run.
# A real module + a real pytest suite. The bug is in billing.py (`>` vs `>=`).
# =====================================================================
PROJECT_FILES = {
    "billing.py": '''\
"""Order billing — a volume-discount pricing engine.

Finance spec (authoritative):
  * Volume discount tiers apply AT OR ABOVE each threshold:
        subtotal >= 1000  -> 15% off
        subtotal >=  500  -> 10% off
        subtotal >=  100  ->  5% off
        otherwise         ->  no discount
  * The discount is applied to the subtotal first, THEN tax is applied to the
    discounted amount. Money is rounded to 2 decimals at the end.
"""


def line_total(unit_price, qty):
    return unit_price * qty


def discount_rate_for(subtotal):
    if subtotal > 1000:
        return 0.15
    if subtotal > 500:
        return 0.10
    if subtotal > 100:
        return 0.05
    return 0.0


def order_total(items, tax_rate):
    subtotal = sum(line_total(i["unit_price"], i["qty"]) for i in items)
    rate = discount_rate_for(subtotal)
    discounted = subtotal * (1 - rate)
    total = discounted * (1 + tax_rate)
    return round(total, 2)
''',
    "test_billing.py": '''\
import pytest
from billing import line_total, discount_rate_for, order_total


def test_line_total():
    assert line_total(9.99, 3) == pytest.approx(29.97)


@pytest.mark.parametrize("subtotal,expected", [
    (99.99, 0.0),
    (100.0, 0.05),    # boundary: AT the threshold gets the tier
    (250.0, 0.05),
    (500.0, 0.10),    # boundary
    (999.99, 0.10),
    (1000.0, 0.15),   # boundary
    (5000.0, 0.15),
])
def test_discount_tiers(subtotal, expected):
    assert discount_rate_for(subtotal) == expected


def test_order_total_no_discount():
    items = [{"unit_price": 10.0, "qty": 2}]          # subtotal 20 -> no discount
    assert order_total(items, tax_rate=0.08) == pytest.approx(21.60)


def test_order_total_on_tier_boundary():
    items = [{"unit_price": 100.0, "qty": 10}]        # subtotal 1000 -> 15% off
    # 1000 * 0.85 * 1.08 = 918.00
    assert order_total(items, tax_rate=0.08) == pytest.approx(918.00)
''',
}


def reset_workspace():
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)
    WORKSPACE.mkdir(parents=True)
    for name, content in PROJECT_FILES.items():
        (WORKSPACE / name).write_text(content, encoding="utf-8")


# =====================================================================
# GUARDED TOOLS — sandboxed, with the test files frozen.
# =====================================================================
def _safe(path: str) -> Path:
    p = (WORKSPACE / path).resolve()
    if os.path.commonpath([str(p), str(WORKSPACE.resolve())]) != str(WORKSPACE.resolve()):
        raise ValueError("path escapes the workspace sandbox")
    return p


def _is_test_file(path: str) -> bool:
    return re.match(r"(.*/)?test_.*\.py$", path.replace("\\", "/")) is not None


def list_files(_=None) -> str:
    return json.dumps(sorted(str(p.relative_to(WORKSPACE)) for p in WORKSPACE.rglob("*.py")))


def read_file(path: str) -> str:
    try:
        p = _safe(path)
    except ValueError as e:
        return f"ERROR: {e}"
    if not p.exists():
        return f"ERROR: no such file '{path}'."
    return p.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    if _is_test_file(path):
        return "REFUSED: the test files are frozen. Fix the source code, not the tests."
    try:
        p = _safe(path)
    except ValueError as e:
        return f"ERROR: {e}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote '{path}' ({len(content)} chars)."


def edit_file(path: str, find: str, replace: str) -> str:
    if _is_test_file(path):
        return "REFUSED: the test files are frozen. Fix the source code, not the tests."
    try:
        p = _safe(path)
    except ValueError as e:
        return f"ERROR: {e}"
    if not p.exists():
        return f"ERROR: no such file '{path}'."
    text = p.read_text(encoding="utf-8")
    n = text.count(find)
    if n == 0:
        return "ERROR: 'find' text not found — it must match the file exactly (incl. whitespace)."
    if n > 1:
        return f"ERROR: 'find' matches {n} places; include more context so it is unique."
    p.write_text(text.replace(find, replace), encoding="utf-8")
    return f"edited '{path}' (1 replacement)."


def run_tests(_=None):
    """Run the suite in the sandbox. Returns (output, all_passed). Ground truth."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=str(WORKSPACE), capture_output=True, text=True, timeout=90,
        )
        out = (proc.stdout + proc.stderr).strip()
        return out, proc.returncode == 0
    except subprocess.TimeoutExpired:
        return "ERROR: test run timed out (90s).", False
    except Exception as e:
        return f"ERROR running tests: {e!r}", False


TOOL_FUNCS = {"list_files": list_files, "read_file": read_file,
              "write_file": write_file, "edit_file": edit_file}

TOOLS = [
    {"type": "function", "function": {"name": "list_files",
        "description": "List the Python files in the project.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "read_file",
        "description": "Read the full contents of a file.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                       "required": ["path"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "edit_file",
        "description": "Replace an exact, unique snippet in a file with new text. Preferred for small fixes.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "find": {"type": "string"}, "replace": {"type": "string"}},
            "required": ["path", "find", "replace"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "write_file",
        "description": "Overwrite a file with new full contents. Use when an edit is too large for edit_file.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "run_tests",
        "description": "Run the test suite and see the results. This is the source of truth for whether you are done.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
]


def _summary(pytest_output: str) -> str:
    m = re.search(r"(\d+)\s+passed", pytest_output)
    f = re.search(r"(\d+)\s+failed", pytest_output)
    passed = int(m.group(1)) if m else 0
    failed = int(f.group(1)) if f else 0
    return f"{passed} passed, {failed} failed"


def run_agent(task: str, max_turns: int = 14) -> dict:
    system = (
        "You are an autonomous software engineer working in a sandboxed Python project whose "
        "test suite is failing. Use the tools to investigate (list_files, read_file), then FIX "
        "THE SOURCE CODE (edit_file / write_file) and run_tests until ALL tests pass. "
        "The test files are frozen — you may not modify them; fix the real bug. "
        "You are NOT finished until run_tests shows everything passing; do not claim success otherwise."
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": task}]
    in_tok = out_tok = 0
    last_test_output = ""

    for turn in range(1, max_turns + 1):
        resp = client.chat.completions.create(
            model=DEPLOYMENT, messages=messages, tools=TOOLS, temperature=0, max_tokens=900)
        in_tok += resp.usage.prompt_tokens
        out_tok += resp.usage.completion_tokens
        choice = resp.choices[0]

        if choice.finish_reason != "tool_calls":
            # The model thinks it's done — VERIFY against ground truth before believing it.
            out, passed = run_tests()
            last_test_output = out
            if passed:
                print(f"\n─── turn {turn}: agent reports done — VERIFIED green ✅ ───")
                return {"solved": True, "turns": turn, "in_tok": in_tok, "out_tok": out_tok,
                        "test_output": out}
            print(f"\n─── turn {turn}: agent claimed done but tests are RED — pushing back ───")
            messages.append({"role": "assistant", "content": choice.message.content or ""})
            messages.append({"role": "user", "content":
                             f"Not done — the tests are still failing:\n{out}\nKeep fixing the source."})
            continue

        print(f"\n─── turn {turn} ───")
        messages.append(choice.message)
        turn_went_green = False
        for call in choice.message.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            if name == "run_tests":
                out, passed = run_tests()
                last_test_output = out
                turn_went_green = turn_went_green or passed
                result = out[:2000]
                print(f"   🔧 run_tests() → {_summary(out)}")
            else:
                label = args.get("path", "")
                if name == "edit_file":
                    label += f"  find={args.get('find','')[:40]!r}→{args.get('replace','')[:40]!r}"
                result = TOOL_FUNCS[name](**args)
                print(f"   🔧 {name}({label}) → {str(result)[:90]}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})

        if turn_went_green:
            print(f"\n─── turn {turn}: tests are GREEN ✅ ───")
            return {"solved": True, "turns": turn, "in_tok": in_tok, "out_tok": out_tok,
                    "test_output": last_test_output}

    return {"solved": False, "turns": max_turns, "in_tok": in_tok, "out_tok": out_tok,
            "test_output": last_test_output}


def show_diff():
    print("\n" + "─" * 70)
    print("DIFF — what the agent changed (tests untouched, as enforced):")
    print("─" * 70)
    any_change = False
    for name, original in PROJECT_FILES.items():
        current = (WORKSPACE / name).read_text(encoding="utf-8")
        if current != original:
            any_change = True
            diff = difflib.unified_diff(original.splitlines(), current.splitlines(),
                                        fromfile=f"a/{name}", tofile=f"b/{name}", lineterm="")
            print("\n".join(diff))
    if not any_change:
        print("(no files changed)")


if __name__ == "__main__":
    reset_workspace()
    task = os.getenv("DEMO_TASK") or (
        "The billing test suite is failing. Investigate, fix the bug in the source code, "
        "and make every test pass. Do not modify the tests."
    )
    max_turns = int(os.getenv("DEMO_MAX_TURNS", "14"))

    print(f"Model deployment: {DEPLOYMENT}")
    print(f"Workspace       : {WORKSPACE}")
    print(f"TASK            : {task}\n")

    before_out, before_pass = run_tests()
    print(f"[before] tests: {_summary(before_out)}  →  {'GREEN' if before_pass else 'RED'}")

    t0 = time.perf_counter()
    result = run_agent(task, max_turns=max_turns)
    secs = time.perf_counter() - t0

    show_diff()
    after_out, after_pass = run_tests()

    print("\n" + "=" * 70)
    print("RUN REPORT")
    print("=" * 70)
    print(f"  outcome        : {'✅ FIXED — suite green' if after_pass else '❌ not fixed'}")
    print(f"  tests          : {_summary(before_out)}  →  {_summary(after_out)}")
    print(f"  turns used     : {result['turns']} / {max_turns}")
    print(f"  tokens         : {result['in_tok']} in + {result['out_tok']} out")
    cost = result["in_tok"] * PRICE_IN + result["out_tok"] * PRICE_OUT
    print(f"  cost           : ${cost:.6f}")
    print(f"  wall time      : {secs:.1f}s")
    print("\nThe agent never graded itself — pytest did, and it could not modify the tests.")
