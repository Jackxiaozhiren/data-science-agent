from __future__ import annotations

import dsa_evaluation.verify_release as release_verifier


def test_release_verifier_blocks_non_allowlisted_command(monkeypatch) -> None:
    def unexpected_subprocess_run(*args, **kwargs):
        raise AssertionError("subprocess.run must not be reached for an unapproved command")

    monkeypatch.setattr(release_verifier.subprocess, "run", unexpected_subprocess_run)

    ok, message = release_verifier._run(["bash", "-lc", "echo should-not-run"])

    assert ok is False
    assert "Blocked non-allowlisted release command" in message
