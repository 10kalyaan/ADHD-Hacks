"""
Test-only setup. `actian-vectorai-client` isn't installable outside the
hackathon's Docker/VectorAI DB setup, but ranking.py/vectordb/client.py
import it at module scope — so tests stub it out in sys.modules before
anything under test gets imported. Individual tests still monkeypatch the
specific functions they exercise (query_tabs, scroll_all_tabs, ...).
"""

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if "actian_vectorai_client" not in sys.modules:
    fake_module = types.ModuleType("actian_vectorai_client")

    class _FakeVectorAIClient:
        def __init__(self, *args, **kwargs):
            pass

    fake_module.VectorAIClient = _FakeVectorAIClient
    sys.modules["actian_vectorai_client"] = fake_module
