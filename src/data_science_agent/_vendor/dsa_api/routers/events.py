"""R-15: the relay that lets the browser report the one funnel link only it can observe.

``arrival`` is a page view. No server code can know it, so the client has to say it -- and that is the whole
reason this file exists as its own boundary rather than a call into the emitter: an unauthenticated POST is
allowed to hand over a record, and nothing about the payload contract loosens to let it. The vocabulary, the
prohibited key classes, the declared choices and the value rule are the same ones the in-process emitter
applies, checked by ``client_event_refusal`` and then applied again by ``record_client_event`` on the way in.

A caller cannot reach the API's own events. ``run_started``, ``run_completed``, ``export_taken`` and
``starter_question_used`` are recorded where the server observes them, and the emitter's ownership check
refuses them here -- which is what stops this route from being a way to inflate a conversion rate.

When this instance does not count, the answer is the same and nothing is written. That is deliberate: a route
that answered differently would be a probe for whether the operator chose to count visitors.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from dsa_api.services.telemetry import client_event_refusal, record_client_event

router = APIRouter(prefix="/api/v1/events", tags=["events"])


class ClientEventBody(BaseModel):
    event: str = Field(
        description="a name the published vocabulary declares as emitted by the web client"
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="the keys that event declares, and only those; see product_events.json",
    )


@router.post("", status_code=202)
async def record_arrival(body: ClientEventBody) -> dict[str, int]:
    """Accept one browser-observed event. The refusal message is the vocabulary's own wording."""
    problem = client_event_refusal(body.event, body.payload)
    if problem is not None:
        raise HTTPException(status_code=400, detail=problem)
    record_client_event(body.event, body.payload)
    return {"accepted": 1}
