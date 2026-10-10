"""
API key lookup. Keys are NEVER stored in this file, so it is safe to commit.

Order of precedence:
1. Environment variables / a `.env` file   (recommended)
2. An optional `config_local.py` next to this file (it is gitignored).
   Copy `config_local.example.py` to `config_local.py` and paste keys there.

Only the SerpApi key is required. The Anthropic key is optional: without it the
app uses its built-in rules-based extraction instead of Claude.
"""

import os

try:  # optional, gitignored
    import config_local as _local
except ImportError:
    _local = None


def _get(env_name: str, local_name: str):
    value = os.environ.get(env_name) or getattr(_local, local_name, "") or ""
    return value.strip() or None


def get_serpapi_key():
    return _get("SERPAPI_API_KEY", "SERPAPI_KEY")


def get_anthropic_key():
    return _get("ANTHROPIC_API_KEY", "ANTHROPIC_KEY")
