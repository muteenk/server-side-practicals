from typing import Annotated

from fastapi import APIRouter, Header, Query

from src import dependencies

from .pydantic_models import FailureOutcome, UnreliableCallResponse


router = APIRouter(prefix="/retry-mechanisms", tags=["retry_mechanisms"])


@router.get("/outcomes", response_model=list[FailureOutcome])
def list_possible_outcomes(
    flaky: dependencies.FlakyUpstreamServiceDep,
) -> list[FailureOutcome]:
    """What the unreliable endpoint can return — useful when explaining which statuses to retry."""
    return [FailureOutcome(**row) for row in flaky.list_outcomes()]


@router.get("/unreliable", response_model=UnreliableCallResponse)
def unreliable_upstream_get(
    flaky: dependencies.FlakyUpstreamServiceDep,
    failure_rate: Annotated[
        float,
        Query(
            ge=0.0,
            le=1.0,
            description="Probability of a simulated failure (0 = always succeed, 1 = always fail)",
        ),
    ] = 0.7,
    seed: Annotated[
        int | None,
        Query(description="Optional RNG seed for repeatable demos"),
    ] = None,
    force_status: Annotated[
        int | None,
        Query(
            description="Force a specific HTTP status (e.g. 429, 503). Use 200 to force success.",
        ),
    ] = None,
    message: Annotated[str, Query()] = "Upstream call completed",
    x_attempt: Annotated[
        str | None,
        Header(description="Pass attempt number from client to correlate retries"),
    ] = None,
) -> UnreliableCallResponse:
    """
    Simulates an flaky dependency: random 429 / 5xx, or 200.

    Clients can practice retries, exponential backoff, and honoring `Retry-After` on 429.
    """
    hint = x_attempt or "no-attempt-header"
    result = flaky.call(
        failure_rate=failure_rate,
        seed=seed,
        force_status=force_status,
        message=message,
        attempt_hint=hint,
    )
    return UnreliableCallResponse(**result)