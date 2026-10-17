import pytest

from claimguard.llm import client as cl
from claimguard.llm.client import LLMClient, LLMError
from claimguard.llm.fake import FakeLLM, RecordingLLM
from claimguard.llm.schemas import ExtractOut


class Fake429(Exception):
    status_code = 429


@pytest.fixture
def llm(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-not-real")
    monkeypatch.setenv("GEMINI_API_KEY", "test-not-real")
    monkeypatch.setattr(cl.time, "sleep", lambda s: None)
    return LLMClient()


def script(llm, monkeypatch, answers, seen):
    it = iter(answers)

    def call(provider, model, prompt):
        seen.append((provider, prompt))
        a = next(it)
        if isinstance(a, Exception):
            raise a
        return a
    monkeypatch.setattr(llm, "_call", call)


def test_valid_json(llm, monkeypatch):
    seen = []
    script(llm, monkeypatch, ['{"claims": []}'], seen)
    assert llm.json("claim_extractor", "p", ExtractOut).claims == []


def test_invalid_json_then_valid_feeds_error_back(llm, monkeypatch):
    seen = []
    script(llm, monkeypatch, ["not json", '{"claims": []}'], seen)
    llm.json("claim_extractor", "p", ExtractOut)
    assert seen[0][1] == "p" and "previous output was invalid" in seen[1][1]


def test_429_retry_then_fallback(llm, monkeypatch):
    seen = []
    script(llm, monkeypatch, [Fake429("rate limit"), Fake429("rate limit"), '{"claims": []}'], seen)
    llm.json("claim_extractor", "p", ExtractOut, step="extract")
    assert [p for p, _ in seen] == ["groq", "groq", "gemini"] and llm.usage.fallbacks == 1
    assert seen[1][1] == "p"                                   # network retry: no "invalid" note


def test_429_without_fallback_key_stops_cleanly(llm, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    seen = []
    script(llm, monkeypatch, [Fake429("rate limit"), Fake429("rate limit")], seen)
    with pytest.raises(LLMError, match="no fallback"):
        llm.json("claim_extractor", "p", ExtractOut, step="extract")


def test_no_key_gives_clear_error(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMError, match="No API key"):
        LLMClient()


def test_retry_after_header():
    e = Fake429("x")
    e.response = type("R", (), {"headers": {"x-ratelimit-reset-tokens": "1m2.5s"}})()
    assert cl._retry_after(e) == 60
    e.response.headers = {"retry-after": "7"}
    assert cl._retry_after(e) == 7


def test_fake_llm_handler_fixture_and_recording(tmp_path):
    fake = FakeLLM(handlers={"claim_extractor": lambda p: {"claims": [{"text": "x", "claim_type": "efficacy"}]}},
                   fixtures=tmp_path)
    assert fake.json("claim_extractor", "p", ExtractOut).claims[0].text == "x"
    rec = RecordingLLM(fake, fixtures=tmp_path)
    rec.json("claim_extractor", "prompt-2", ExtractOut)
    replay = FakeLLM(fixtures=tmp_path)
    assert replay.json("claim_extractor", "prompt-2", ExtractOut).claims[0].text == "x"
    with pytest.raises(LLMError):
        replay.json("claim_extractor", "unseen", ExtractOut)


def test_daily_quota_uses_backup_model_without_waiting(llm, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    seen, slept = [], []
    monkeypatch.setattr(cl.time, "sleep", slept.append)

    def call(provider, model, prompt):
        seen.append(model)
        if model == "openai/gpt-oss-120b":
            raise Fake429("Rate limit reached ... tokens per day (TPD): Limit 200000")
        return '{"claims": []}'
    monkeypatch.setattr(llm, "_call", call)
    llm.json("claim_extractor", "p", ExtractOut, step="extract")
    assert seen == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"] and slept == [] and llm.usage.fallbacks == 1
