"""Tests for the Fraud Detection Agent."""

import pytest

from app.agents.fraud_detection import FraudDetectionAgent
from app.models.schemas import ClaimHistoryItem


@pytest.mark.asyncio
async def test_tc009_same_day_claims(policy, trace):
    """TC009: 4th same-day claim triggers MANUAL_REVIEW."""
    agent = FraudDetectionAgent(policy, trace)
    history = [
        ClaimHistoryItem(claim_id="CLM_0081", date="2024-10-30", amount=1200, provider="City Clinic A"),
        ClaimHistoryItem(claim_id="CLM_0082", date="2024-10-30", amount=1800, provider="City Clinic B"),
        ClaimHistoryItem(claim_id="CLM_0083", date="2024-10-30", amount=2100, provider="Wellness Center"),
    ]
    result = await agent.process(
        member_id="EMP008",
        claimed_amount=4800,
        treatment_date="2024-10-30",
        claims_history=history,
    )
    assert result.should_manual_review
    assert any(s.flag == "SAME_DAY_CLAIMS_EXCEEDED" for s in result.signals)


@pytest.mark.asyncio
async def test_no_fraud_signals(policy, trace):
    """No fraud signals for normal claim."""
    agent = FraudDetectionAgent(policy, trace)
    result = await agent.process(
        member_id="EMP001",
        claimed_amount=1500,
        treatment_date="2024-11-01",
        claims_history=[],
    )
    assert not result.should_manual_review
    assert len(result.signals) == 0


@pytest.mark.asyncio
async def test_high_value_claim(policy, trace):
    """High-value claim triggers manual review."""
    agent = FraudDetectionAgent(policy, trace)
    result = await agent.process(
        member_id="EMP001",
        claimed_amount=30000,
        treatment_date="2024-11-01",
        claims_history=[],
    )
    assert result.should_manual_review
    assert any(s.flag == "HIGH_VALUE_CLAIM" for s in result.signals)
