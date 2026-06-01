import random
from dataclasses import dataclass

from fastapi import HTTPException


@dataclass(frozen=True, slots=True)
class SimulatedFailure:
    status_code: int
    detail: str
    retry_after_seconds: int | None = None


# Weighted toward transient / rate-limit errors clients typically retry.
_FAILURE_POOL: tuple[SimulatedFailure, ...] = (
    SimulatedFailure(429, "Too many requests — slow down and retry", retry_after_seconds=2),
    SimulatedFailure(429, "Rate limit exceeded", retry_after_seconds=5),
    SimulatedFailure(500, "Upstream internal error"),
    SimulatedFailure(502, "Bad gateway from dependency"),
    SimulatedFailure(503, "Service temporarily unavailable"),
    SimulatedFailure(504, "Gateway timeout"),
)


class FlakyUpstreamService:
    """Stand-in for an external API that fails unpredictably."""

    def call(
        self,
        *,
        failure_rate: float,
        seed: int | None = None,
        force_status: int | None = None,
        message: str,
        attempt_hint: str,
    ) -> dict:
        if force_status is not None:
            self._raise_for_status(force_status, message)
            return self._success(message, attempt_hint)

        rng = random.Random(seed) if seed is not None else random
        if rng.random() >= failure_rate:
            return self._success(message, attempt_hint)

        failure = rng.choice(_FAILURE_POOL)
        self._raise_simulated(failure)

    @staticmethod
    def list_outcomes() -> list[dict]:
        seen: set[int] = set()
        rows = []
        for f in _FAILURE_POOL:
            if f.status_code in seen:
                continue
            seen.add(f.status_code)
            rows.append(
                {
                    "http_status": f.status_code,
                    "label": f.detail,
                    "retryable": f.status_code in (429, 502, 503, 504),
                }
            )
        rows.append(
            {
                "http_status": 200,
                "label": "Success",
                "retryable": False,
            }
        )
        return sorted(rows, key=lambda r: r["http_status"])

    @staticmethod
    def _success(message: str, attempt_hint: str) -> dict:
        return {
            "status": "ok",
            "message": message,
            "attempt_hint": attempt_hint,
        }

    def _raise_for_status(self, status_code: int, message: str) -> None:
        if status_code == 200:
            return
        matching = next((f for f in _FAILURE_POOL if f.status_code == status_code), None)
        if matching:
            self._raise_simulated(matching)
        raise HTTPException(
            status_code=status_code,
            detail={"message": message, "simulated": True},
        )

    @staticmethod
    def _raise_simulated(failure: SimulatedFailure) -> None:
        headers = {}
        if failure.retry_after_seconds is not None:
            headers["Retry-After"] = str(failure.retry_after_seconds)
        raise HTTPException(
            status_code=failure.status_code,
            detail={"message": failure.detail, "simulated": True},
            headers=headers or None,
        )
