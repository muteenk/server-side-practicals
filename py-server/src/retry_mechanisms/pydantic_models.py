from pydantic import BaseModel, Field


class UnreliableCallResponse(BaseModel):
    status: str = "ok"
    message: str
    attempt_hint: str = Field(
        description="Use this in the client to correlate retries in logs or demos",
    )


class FailureOutcome(BaseModel):
    """Describes what the simulator can return (for docs / GET /outcomes)."""

    http_status: int
    label: str
    retryable: bool
