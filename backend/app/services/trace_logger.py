"""Trace logger — accumulates trace steps for a single claim processing run.

Every agent appends steps to the trace via this logger. The final trace
is included in the ClaimDecision output.
"""

from __future__ import annotations

from datetime import datetime

from app.models.schemas import ClaimTrace, TraceStatus, TraceStep


class TraceLogger:
    def __init__(self, claim_id: str):
        self.trace = ClaimTrace(claim_id=claim_id)

    def add_step(
        self,
        agent: str,
        check_name: str,
        status: TraceStatus,
        details: str,
        confidence_impact: float = 0.0,
    ) -> None:
        step = TraceStep(
            agent=agent,
            check_name=check_name,
            status=status,
            details=details,
            timestamp=datetime.utcnow(),
            confidence_impact=confidence_impact,
        )
        self.trace.steps.append(step)
        self.trace.overall_confidence = max(
            0.30, self.trace.overall_confidence + confidence_impact
        )

    def passed(self, agent: str, check_name: str, details: str) -> None:
        self.add_step(agent, check_name, TraceStatus.PASSED, details)

    def failed(self, agent: str, check_name: str, details: str, confidence_impact: float = 0.0) -> None:
        self.add_step(agent, check_name, TraceStatus.FAILED, details, confidence_impact)

    def error(self, agent: str, check_name: str, details: str, confidence_impact: float = -0.20) -> None:
        self.add_step(agent, check_name, TraceStatus.ERROR, details, confidence_impact)

    def skipped(self, agent: str, check_name: str, details: str) -> None:
        self.add_step(agent, check_name, TraceStatus.SKIPPED, details)

    @property
    def confidence(self) -> float:
        return self.trace.overall_confidence
