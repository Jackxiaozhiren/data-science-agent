from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from dsa_evaluation.runner import _evaluation_variant, _execution_metadata


def test_execution_metadata_records_real_model_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.setenv("DSA_LLM_PROVIDER", "openai")
    monkeypatch.setenv("DSA_OPENAI_MODEL", "test-model")
    monkeypatch.setenv("DSA_INPUT_COST_PER_MILLION", "2.0")
    monkeypatch.setenv("DSA_OUTPUT_COST_PER_MILLION", "10.0")
    monkeypatch.setenv("DSA_GIT_COMMIT", "abc123")
    monkeypatch.delenv("DSA_EVIDENCE_CRITIC", raising=False)
    monkeypatch.delenv("DSA_EVALUATION_VARIANT", raising=False)

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
    assert metadata["evaluation_variant"] == "dsa"
    assert metadata["evidence_critic_enabled"] is True
    assert metadata["call_count"] == 2
    assert metadata["model_latency_ms"] == 200
    assert metadata["token_usage"] == {
        "input_tokens": 1500,
        "output_tokens": 300,
        "total_tokens": 1800,
    }
    assert metadata["cost_usd"] == pytest.approx(0.006)


def test_execution_metadata_records_no_critic_ablation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_EVIDENCE_CRITIC", "off")
    monkeypatch.delenv("DSA_EVALUATION_VARIANT", raising=False)

    metadata = _execution_metadata([])

    assert metadata["evaluation_variant"] == "dsa-no-critic"
    assert metadata["evidence_critic_enabled"] is False
    assert metadata["evidence_critic_setting"] == "off"


def test_execution_metadata_records_llm_tools_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_EVALUATION_VARIANT", "llm-tools")
    monkeypatch.setenv("DSA_BASELINE_PREVIEW_ROWS", "7")

    metadata = _execution_metadata([])

    assert metadata["evaluation_variant"] == "llm-tools"
    assert metadata["evidence_critic_enabled"] is None
    assert metadata["evidence_critic_setting"] == "not-applicable"
    assert metadata["baseline_config"]["prompt_version"] == "baseline-v1"
    assert metadata["baseline_config"]["preview_rows"] == 7


def test_evaluation_variant_rejects_mislabeled_ablation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_EVALUATION_VARIANT", "dsa-no-critic")
    monkeypatch.setenv("DSA_EVIDENCE_CRITIC", "on")

    with pytest.raises(RuntimeError, match="conflicts"):
        _evaluation_variant()


def test_execution_metadata_does_not_invent_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.delenv("DSA_EVALUATION_VARIANT", raising=False)
    monkeypatch.delenv("DSA_INPUT_COST_PER_MILLION", raising=False)
    monkeypatch.delenv("DSA_OUTPUT_COST_PER_MILLION", raising=False)

    metadata = _execution_metadata([])

    assert metadata["cost_usd"] is None
    assert metadata["pricing"]["source"] is None


# --- §143: the run manifest has to name the commit it ran from --------------------------------


def test_metadata_names_the_checkout_when_no_env_supplies_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RED before §143: `git_commit` read only `DSA_GIT_COMMIT`/`GITHUB_SHA`, so a local run wrote null.

    That is the field the frozen baseline was missing: `benchmarks/baseline/README.md` says nothing records
    which mode or which revision produced the stored numbers, and a run that leaves `git_commit: null` does
    not fix that claim just because a manifest file exists.
    """
    monkeypatch.delenv("DSA_GIT_COMMIT", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    metadata = _execution_metadata([])

    commit = metadata["git_commit"]
    assert commit is not None, "a run inside a checkout recorded no revision at all"
    assert re.fullmatch(r"[0-9a-f]{12}", str(commit)), commit


def test_an_explicit_commit_still_beats_the_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    """CI's own value must stay authoritative; the fallback is only for runs with no CI context."""
    monkeypatch.setenv("DSA_GIT_COMMIT", "abcdef1234567890")
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    assert _execution_metadata([])["git_commit"] == "abcdef1234567890"

    monkeypatch.delenv("DSA_GIT_COMMIT", raising=False)
    monkeypatch.setenv("GITHUB_SHA", "1234567890abcdef1234567890abcdef12345678")

    assert _execution_metadata([])["git_commit"] == "1234567890abcdef1234567890abcdef12345678"


def test_the_resolver_is_honest_outside_a_repository(tmp_path: Path) -> None:
    """No `.git` above the given root means no commit, not a guess and not an exception."""
    from dsa_evaluation.research_manifest import resolve_git_commit

    assert resolve_git_commit(tmp_path) is None


def test_the_resolver_agrees_whichever_copy_of_the_module_is_loaded() -> None:
    """The shipped `dsa` imports the vendored copy, so a fix in one file is inert until both agree.

    Both call sites resolve through `__file__`, and the two copies sit at different depths of the tree
    (`packages/evaluation/src/...` versus `src/data_science_agent/_vendor/...`), so this asserts the value
    rather than the path arithmetic: whatever the process bound, it must name the real HEAD.
    """
    import subprocess

    from dsa_evaluation.research_manifest import resolve_git_commit

    expected = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()[:12]

    assert resolve_git_commit() == expected


def test_the_manifest_a_real_run_writes_names_the_commit(tmp_path: Path) -> None:
    """The claim §143 exists for, checked end to end through the shipped command surface.

    `_execution_metadata` is a unit seam; the freeze is produced by `dsa`, which imports the vendored
    module. So this runs the real console script on one stub task into a temp directory and reads the
    manifest it wrote -- proving both that the field is filled and that the vendored copy got the fix.
    """
    repo = Path(__file__).resolve().parents[1]
    env = {k: v for k, v in os.environ.items() if k not in ("DSA_GIT_COMMIT", "GITHUB_SHA")}
    out = tmp_path / "bench"
    result = subprocess.run(
        ["uv", "run", "--frozen", "dsa", "--limit", "1", "--out", str(out)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    commit = manifest["execution"]["git_commit"]

    assert commit is not None, manifest["execution"]
    assert re.fullmatch(r"[0-9a-f]{12}", str(commit)), commit
    assert manifest["execution"]["llm_mode"] == "stub", manifest["execution"]
