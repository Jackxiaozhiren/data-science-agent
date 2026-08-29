from __future__ import annotations

import pytest

from dsa_evaluation.runner import _execution_metadata


def test_execution_metadata_records_real_model_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.setenv("DSA_LLM_PROVIDER", "openai")
    monkeypatch.setenv("DSA_OPENAI_MODEL", "test-model")
    monkeypatch.setenv("DSA_INPUT_COST_PER_MILLION", "2.0")
    monkeypatch.setenv("DSA_OUTPUT_COST_PER_MILLION", "10.0")
    monkeypatch.setenv("DSA_GIT_COMMIT", "abc123")

    metadata = _execution_metadata(
        [
            {
                "provider": "openai",
                "model": "test-model",
                "latency_ms": 120,
                "usage": {"input_tokens": 1000, "output_tokens": 200, "total_tokens": 1200},
            },
            {
                "provider": "openai",
                "model": "test-model",
                "latency_ms": 80,
                "usage": {"input_tokens": 500, "output_tokens": 100, "total_tokens": 600},
            },
        ]
    )

    assert metadata["provider"] == "openai"
    assert metadata["model"] == "test-model"
    assert metadata["git_commit"] == "abc123"
    assert metadata["call_count"] == 2
    assert metadata["model_latency_ms"] == 200
    assert metadata["token_usage"] == {
        "input_tokens": 1500,
        "output_tokens": 300,
        "total_tokens": 1800,
    }
    assert metadata["cost_usd"] == pytest.approx(0.006)


def test_execution_metadata_does_not_invent_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.delenv("DSA_INPUT_COST_PER_MILLION", raising=False)
    monkeypatch.delenv("DSA_OUTPUT_COST_PER_MILLION", raising=False)

    metadata = _execution_metadata([])

    assert metadata["cost_usd"] is None
    assert metadata["pricing"]["source"] is None
