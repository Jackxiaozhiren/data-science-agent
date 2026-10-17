"""R-05: where a private instance keeps the model credential its operator chose inside the product.

The hosted demo must not have this at all, and the local one must not need it in a shell. Between those two
sits the actual design question, and three answers are load-bearing:

- **A file, not a table row.** The path comes from ``DSA_PROVIDER_CONFIG``, which ``dsa ui`` sets inside the
  data directory the user already chose, so the secret lives where their database and uploads live and is
  erased by deleting that directory. A credentials table would ride along in every database copy, backup and
  support bundle a user makes of ``dsa.db`` -- which is precisely the "never included in any serialized
  artifact" rule the requirement states.
- **The stored value wins over the environment, for the names it carries.** ``dsa ui`` defaults
  ``DSA_LLM_MODE`` to ``heuristic`` in the child's environment, so an env-first rule would mean a key
  configured through the interface could never take effect: the launcher's guess would outrank the person's
  explicit choice, forever and invisibly. ``resolve_llm_mode`` reports which one answered through ``source``,
  so nothing here is a guess a reader has to reverse-engineer.
- **Nothing ever reads the secret back out.** ``GET /api/v1/provider`` returns the provider, model, base URL
  and whether a key is present -- never the key, and not a fragment of it. A masked hint invites the next
  field to be masked too, and the browser is not where a credential belongs.

Validation returns a message instead of raising, because the settings route has to show the operator what
they got wrong rather than answer 500, and because the repository's exception-handler ceiling is a fixed
budget this module is not going to spend.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any

#: The environment variable naming the file. Unset means this instance has nowhere to keep a secret, which is
#: how the API tells a hosted deployment from a private one without a second flag to forget.
ENV_PATH = "DSA_PROVIDER_CONFIG"

#: Providers the interface can configure, in the order the product suggests them. `ollama` is first because it
#: is the free and local answer, and the plan says to make cost and privacy explicit rather than assuming a
#: visitor arrives with a hosted key.
PROVIDERS: tuple[str, ...] = ("ollama", "openai-compat", "openai")

STUB_MODES = frozenset({"stub", "offline", "heuristic"})
REAL_MODES = frozenset({"real", "openai"})

#: A key is opaque and short in practice; the ceiling is a shape guard, not a quota.
_MAX_SECRET_CHARS = 512
_MAX_FIELD_CHARS = 300


def config_path() -> Path | None:
    """Where this instance keeps its provider settings, or None when it is not a place that may hold secrets."""
    raw = os.getenv(ENV_PATH, "").strip()
    return Path(raw).expanduser() if raw else None


def local_settings_allowed() -> bool:
    """Whether this process may accept a credential at all: only when it has somewhere to put it."""
    return config_path() is not None


def read() -> tuple[dict[str, Any], str | None]:
    """The stored settings, and the reason they could not be read. Never raises, never half-applies.

    A hand-edited or truncated file must not silently change which provider a run reaches, so an unreadable
    file yields no settings and the message that explains them; the settings route shows both.
    """
    path = config_path()
    if path is None:
        return {}, f"{ENV_PATH} is not set, so this instance keeps no provider settings"
    if not path.is_file():
        return {}, None
    text = path.read_text(encoding="utf-8", errors="replace")
    loaded: Any = None
    # `suppress` rather than a handler: the ratchet budgets every handler in shipped code, and this one would
    # only re-state what the message below already says. The path is named, so the operator has the locator.
    with contextlib.suppress(ValueError):
        loaded = json.loads(text)
    if not isinstance(loaded, dict):
        return {}, (
            f"{path} is not one JSON object; fix or delete it"
            if loaded is None
            else f"{path} must contain one JSON object, not {type(loaded).__name__}"
        )
    problem = refusal(loaded)
    if problem is not None:
        return {}, f"{path} holds an unusable configuration: {problem}"
    return loaded, None


def write(settings: dict[str, Any]) -> Path:
    """Store `settings`, readable only by this user. Atomic, because a key must not half-write.

    The file is created with its mode already restricted: writing first and chmod-ing after leaves a window in
    which another local user could open it, which is the whole thing this module exists to prevent.
    """
    path = config_path()
    if path is None:
        raise RuntimeError(f"{ENV_PATH} is not set, so there is nowhere to store provider settings")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    descriptor = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(settings, sort_keys=True))
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)
    os.chmod(path, 0o600)
    return path


def world_readable() -> bool:
    """Whether the stored secret is readable by anyone else on this machine -- a fact the UI must show."""
    path = config_path()
    if path is None or not path.is_file():
        return False
    return bool(path.stat().st_mode & 0o077)


def erase() -> bool:
    """Forget the stored settings. Returns whether there was anything here to forget."""
    path = config_path()
    if path is None or not path.is_file():
        return False
    path.unlink()
    return True


def refusal(settings: dict[str, Any]) -> str | None:
    """Why `settings` cannot be used, or None when it can. Message-returning, never an exception.

    Checked against the shape rather than against a network: verifying a credential means spending the user's
    money or contacting a third party, and the plan's guard is that the product states that plainly instead
    of doing it silently on a save.
    """
    if not isinstance(settings, dict):
        return f"expected one JSON object, got {type(settings).__name__}"
    mode = str(settings.get("mode") or "").strip().lower()
    if mode and mode not in STUB_MODES | REAL_MODES:
        return f"unknown mode {mode!r}; expected one of {sorted(STUB_MODES | REAL_MODES)}"
    provider = str(settings.get("provider") or "").strip().lower()
    if provider and provider not in PROVIDERS:
        return f"unknown provider {provider!r}; expected one of {list(PROVIDERS)}"
    key = settings.get("api_key")
    if key is not None:
        if not isinstance(key, str):
            return "the credential must be a string"
        # An empty string is a removal, not a shape error: the response never repeats the key, so the only way
        # a form can say "forget it" is by sending a value that means nothing. Whether that is allowed is the
        # mode's decision, checked below -- a stub run with no credential is a normal configuration.
        if len(key) > _MAX_SECRET_CHARS:
            return (
                f"the credential is longer than {_MAX_SECRET_CHARS} characters, which is not a key"
            )
        if any(ord(char) < 32 for char in key):
            return "the credential contains control characters"
    for field in ("model", "base_url"):
        value = settings.get(field)
        if value is not None and (not isinstance(value, str) or len(value) > _MAX_FIELD_CHARS):
            return f"{field} must be a string of at most {_MAX_FIELD_CHARS} characters"
    base_url = str(settings.get("base_url") or "").strip()
    if base_url and not base_url.startswith(("http://", "https://")):
        return "the base URL must start with http:// or https://"
    if mode in REAL_MODES and provider in {"openai", "openai-compat"} and not key:
        return (
            f"mode {mode!r} with provider {provider!r} needs an API key, or the run will fail when it "
            "asks the model"
        )
    return None


def secret(settings: dict[str, Any], provider: str) -> str | None:
    """The credential stored for `provider`, or None. The only reader of it in the process."""
    if str(settings.get("provider") or "").strip().lower() != provider:
        return None
    key = settings.get("api_key")
    return key.strip() if isinstance(key, str) and key.strip() else None


def value(settings: dict[str, Any], field: str) -> str | None:
    """A non-secret setting (model, base URL, mode) as a stripped string, or None when absent."""
    raw = settings.get(field)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def public_view(settings: dict[str, Any]) -> dict[str, Any]:
    """What the browser is allowed to see: the shape of the configuration, never its credential.

    `api_key` is not simply omitted -- it is deleted from a copy, so a future field added to the stored file
    cannot reach a client by forgetting to be listed here. That makes the redaction a deny-by-default rule
    rather than a whitelist someone has to remember to extend, which is the difference between a filter and a
    leak that reads like one.
    """
    shown = dict(settings)
    shown.pop("api_key", None)
    shown["has_credential"] = bool(secret(settings, str(settings.get("provider") or "")))
    return shown
