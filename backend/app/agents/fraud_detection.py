"""Fraud Detection Agent — identifies suspicious claim patterns.

Checks:
- Same-day claims exceeding limit
- Monthly claims exceeding limit
- High-value claims above auto-review threshold
"""

from __future__ import annotations

from app.models.schemas import ClaimHistoryItem, FraudResult, FraudSignal
from app.services.policy_loader import PolicyLoader
from app.services.trace_logger import TraceLogger

AGENT_NAME = "fraud_detection"


class FraudDetectionAgent:
    def __init__(self, policy: PolicyLoader, trace: TraceLogger):
        self.policy = policy
        self.trace = trace

    async def process(
        self,
        member_id: str,
        claimed_amount: float,
        treatment_date: str,
        claims_history: list[ClaimHistoryItem],
    ) -> FraudResult:
        signals: list[FraudSignal] = []
        should_manual_review = False

        # Check 1: Same-day claims
        same_day_count = sum(
            1 for c in claims_history
            if c.date == treatment_date
        )
        limit = self.policy.same_day_claims_limit
        if same_day_count >= limit:
            signals.append(
                FraudSignal(
                    flag="SAME_DAY_CLAIMS_EXCEEDED",
                    details=(
                        f"Member {member_id} has {same_day_count} prior claims on "
                        f"{treatment_date} (limit: {limit}). This would be claim "
                        f"#{same_day_count + 1} on the same day."
                    ),
                )
            )
            should_manual_review = True
            self.trace.failed(
                AGENT_NAME,
                "same_day_claims",
                f"{same_day_count} prior claims on {treatment_date}, "
                f"exceeds limit of {limit}. Flagging for manual review.",
            )
        else:
            self.trace.passed(
                AGENT_NAME,
                "same_day_claims",
                f"{same_day_count} prior claims on {treatment_date}, "
                f"within limit of {limit}.",
            )

        # Check 2: Monthly claims
        if treatment_date:
            treatment_month = treatment_date[:7]  # YYYY-MM
            monthly_count = sum(
                1 for c in claims_history
                if c.date.startswith(treatment_month)
            )
            monthly_limit = self.policy.monthly_claims_limit
            if monthly_count >= monthly_limit:
                signals.append(
                    FraudSignal(
                        flag="MONTHLY_CLAIMS_EXCEEDED",
                        details=(
                            f"Member {member_id} has {monthly_count} claims in "
                            f"{treatment_month} (limit: {monthly_limit})."
                        ),
                    )
                )
                should_manual_review = True
                self.trace.failed(
                    AGENT_NAME,
                    "monthly_claims",
                    f"{monthly_count} claims in {treatment_month}, "
                    f"exceeds limit of {monthly_limit}.",
                )
            else:
                self.trace.passed(
                    AGENT_NAME,
                    "monthly_claims",
                    f"{monthly_count} claims in {treatment_month}, "
                    f"within limit of {monthly_limit}.",
                )

        # Check 3: High-value claim
        threshold = self.policy.auto_manual_review_above
        if claimed_amount > threshold:
            signals.append(
                FraudSignal(
                    flag="HIGH_VALUE_CLAIM",
                    details=(
                        f"Claimed amount ₹{claimed_amount:,.0f} exceeds "
                        f"auto-review threshold of ₹{threshold:,.0f}."
                    ),
                )
            )
            should_manual_review = True
            self.trace.failed(
                AGENT_NAME,
                "high_value_check",
                f"Amount ₹{claimed_amount:,.0f} exceeds ₹{threshold:,.0f} threshold.",
            )
        else:
            self.trace.passed(
                AGENT_NAME,
                "high_value_check",
                f"Amount ₹{claimed_amount:,.0f} within threshold ₹{threshold:,.0f}.",
            )

        return FraudResult(signals=signals, should_manual_review=should_manual_review)
