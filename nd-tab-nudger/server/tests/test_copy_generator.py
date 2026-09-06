import json
from types import SimpleNamespace

from nudging import copy_generator, session_state


def setup_function(_):
    session_state.reset()


class _FakeModels:
    def __init__(self, response_text):
        self.response_text = response_text
        self.last_kwargs = None

    def generate_content(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(text=self.response_text)


class _FakeClient:
    def __init__(self, response_text):
        self.models = _FakeModels(response_text)


def test_no_candidates_returns_static_line():
    lines, overlay = copy_generator.generate_copy([])
    assert lines == []
    assert "vibes" in overlay


def test_generate_copy_happy_path(monkeypatch):
    fake = _FakeClient(json.dumps({"card_lines": ["do the thing"], "overlay_line": "hey"}))
    monkeypatch.setattr(copy_generator, "get_client", lambda: fake)

    lines, overlay = copy_generator.generate_copy(
        [{"title": "Q3 doc", "domain": "docs.google.com", "label": "work"}]
    )

    assert lines == ["do the thing"]
    assert overlay == "hey"


def test_generate_copy_falls_back_on_malformed_json(monkeypatch):
    fake = _FakeClient("not json at all")
    monkeypatch.setattr(copy_generator, "get_client", lambda: fake)

    lines, overlay = copy_generator.generate_copy(
        [{"title": "Q3 doc", "domain": "docs.google.com", "label": "work"}]
    )

    assert len(lines) == 1
    assert overlay == copy_generator.FALLBACK_OVERLAY_LINE


def test_generate_copy_falls_back_on_line_count_mismatch(monkeypatch):
    fake = _FakeClient(json.dumps({"card_lines": ["one", "two"], "overlay_line": "hey"}))
    monkeypatch.setattr(copy_generator, "get_client", lambda: fake)

    lines, overlay = copy_generator.generate_copy(
        [{"title": "Q3 doc", "domain": "docs.google.com", "label": "work"}]
    )

    assert len(lines) == 1
    assert overlay == copy_generator.FALLBACK_OVERLAY_LINE


def test_generate_copy_passes_high_pressure_to_prompt(monkeypatch):
    monkeypatch.setattr(copy_generator, "HIGH_PRESSURE_VISIT_THRESHOLD", 1)
    session_state.record_distraction_visit("reddit.com")

    fake = _FakeClient(json.dumps({"card_lines": ["x"], "overlay_line": "y"}))
    monkeypatch.setattr(copy_generator, "get_client", lambda: fake)

    copy_generator.generate_copy([{"title": "Q3 doc", "domain": "docs.google.com", "label": "work"}])

    sent_payload = json.loads(fake.models.last_kwargs["contents"])
    assert sent_payload["pressure"] == "high"


def test_generate_copy_requests_json_schema_config(monkeypatch):
    fake = _FakeClient(json.dumps({"card_lines": ["x"], "overlay_line": "y"}))
    monkeypatch.setattr(copy_generator, "get_client", lambda: fake)

    copy_generator.generate_copy([{"title": "Q3 doc", "domain": "docs.google.com", "label": "work"}])

    config = fake.models.last_kwargs["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema == copy_generator.RESPONSE_SCHEMA
