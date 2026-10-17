"""R-05: the settings surface that lets a private instance keep a model credential, and the hosted one refuse.

Three rules, each of which is the whole point of the requirement rather than a detail of it.

**The secret goes in, and never comes out.** `GET` reports the provider, model, endpoint and whether a
credential is present -- not the credential, not a masked fragment. A browser that can display a value can
log it, screenshot it and send it onward, and the plan's rule is that a hosted page must not ask a stranger to
paste a key into a box she cannot audit. The stored file is written 0600 and lives in the data directory the
user already controls, not in the database, which gets copied and backed up.

**A merge, not a replace.** Because the browser cannot read the key back, a form that submitted "the rest of
the settings" without it would silently delete it. So `PUT` merges onto what is stored: omit `api_key` to keep
it, send an empty string to remove it. That is the only shape in which "never echoes the secret" and "the form
is honest" can both hold.

**Hosted mode refuses, and says why.** A deployment that was not started by `dsa ui` has nowhere to put a
secret, so `DSA_PROVIDER_CONFIG` is unset and the write routes answer 403 with the reason and the command to
run instead. Partial support -- accept the key, keep it in memory, lose it on restart -- is what the requirement
tells this not to do.

The write is also refused when the caller is not on this machine and no `DSA_AUTH_TOKEN` is configured, because
an open endpoint that overwrites the operator's API key is an invitation to spend their credit on someone
else's runs.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from dsa_api.core.config import settings
from dsa_llm import provider_store
from dsa_llm.providers import resolve_llm_mode

router = APIRouter(prefix="/api/v1/provider", tags=["settings"])

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}

_REFUSAL = (
    "This instance has nowhere to keep a credential, so it does not accept one. Run the product on your own "
    "machine with `dsa ui`, which stores settings in the data directory you chose and never sends the key "
    "anywhere."
)

_REMOTE_WRITE_REFUSAL = (
    "This instance accepts credentials from the machine it runs on only, and the request did not arrive "
    "from there. Set DSA_AUTH_TOKEN if you mean to allow a remote operator; on a personal machine, run "
    "`dsa ui` and open the settings page there."
)


class ProviderBody(BaseModel):
    """The settings a user may change. `api_key` is write-only: no response ever carries it back."""

    mode: str | None = None
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


def _is_local(client_host: str | None) -> bool:
    return client_host in _LOOPBACK


def _merged(body: ProviderBody) -> dict[str, Any]:
    """What the store would hold if this form were saved: existing settings, with the sent fields applied.

    An explicit empty `api_key` removes it; leaving the field out keeps it. The distinction has to be the
    value itself, because the response never repeats the key and so the form cannot resend it.
    """
    stored, _unreadable = provider_store.read()
    merged = dict(stored)
    for field in ("mode", "provider", "model", "base_url"):
        value = getattr(body, field)
        if value is not None:
            merged[field] = value
    if body.api_key is not None:
        merged["api_key"] = body.api_key
    return merged


@router.get("")
async def read_provider_settings() -> dict[str, Any]:
    """What this instance would use for the next run, and whether it may be changed here.

    The effective mode is the one R-02 made this function own, so the page cannot show a hoped-for provider
    while the process is about to answer with the deterministic planner.
    """
    stored, unreadable = provider_store.read()
    return {
        "local_settings": provider_store.local_settings_allowed(),
        "accepts_remote_writes": bool(settings.auth_token),
        "stored": provider_store.public_view(stored) if stored else {},
        "stored_problem": unreadable,
        "settings_file_readable_by_others": provider_store.world_readable(),
        "effective": resolve_llm_mode().as_dict(),
        "providers": list(provider_store.PROVIDERS),
        "suggestion": (
            "ollama is the free and local option: no key, nothing leaves the machine, and it needs "
            "`ollama serve` plus `ollama pull <model>`."
        ),
    }


@router.put("")
async def save_provider_settings(
    body: ProviderBody,
    request: Request,
) -> dict[str, Any]:
    """Validate and store the settings. The response carries the shape of the result, never its credential."""
    if not provider_store.local_settings_allowed():
        raise HTTPException(status_code=403, detail=_REFUSAL)
    if not settings.auth_token and not _is_local(request.client.host if request.client else None):
        raise HTTPException(status_code=403, detail=_REMOTE_WRITE_REFUSAL)
    merged = _merged(body)
    problem = provider_store.refusal(merged)
    if problem is not None:
        raise HTTPException(status_code=400, detail=problem)
    if not merged:
        raise HTTPException(
            status_code=400,
            detail="no settings were sent; send a mode and provider, or delete the stored settings",
        )
    provider_store.write(merged)
    return {
        "stored": provider_store.public_view(merged),
        "effective": resolve_llm_mode().as_dict(),
        "verified": False,
        "note": (
            "Saved and checked for shape only: this endpoint never contacts the provider, because a test "
            "call would spend your credit or send your data out without you asking."
        ),
    }


@router.delete("")
async def forget_provider_settings(request: Request) -> dict[str, Any]:
    """Delete the stored settings file. There is no other way to lose the credential."""
    if not provider_store.local_settings_allowed():
        raise HTTPException(status_code=403, detail=_REFUSAL)
    if not settings.auth_token and not _is_local(request.client.host if request.client else None):
        raise HTTPException(status_code=403, detail=_REMOTE_WRITE_REFUSAL)
    return {"cleared": provider_store.erase(), "effective": resolve_llm_mode().as_dict()}
