"""
Smoke test — run this FIRST to confirm your Azure OpenAI connection works.

    python smoke_test.py

A pass means every demo's Azure wiring will work, since they all use the same
endpoint / key / deployment from your .env.
"""

import os
import sys
from pathlib import Path

# Windows legacy consoles default to cp1252 and crash on emoji — force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
key = os.getenv("AZURE_OPENAI_API_KEY")
version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")

print("Endpoint  :", endpoint)
print("API ver   :", version)
print("Deployment:", deployment)

if not endpoint or not key or key.startswith("PASTE_"):
    print("\n❌ .env is not filled in. Copy .env.example to .env and add your rotated keys.")
    sys.exit(1)

client = AzureOpenAI(azure_endpoint=endpoint, api_key=key, api_version=version)

try:
    resp = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": "Reply with exactly: Azure OK"}],
        max_tokens=10,
    )
    print("\n✅ Response:", resp.choices[0].message.content)
    print("Azure OpenAI is reachable. You're ready for the masterclass.")
except Exception as e:
    print("\n❌ Call failed:", repr(e))
    print("Common fixes: check the deployment name matches the Azure portal, "
          "and that AZURE_OPENAI_API_VERSION is supported by that deployment.")
    sys.exit(1)
