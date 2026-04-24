"""Tests for the Orchestrator Agent — full pipeline integration tests."""

import pytest
from datetime import date

from app.agents.orchestrator import OrchestratorAgent
from app.models.schemas import (
    ClaimCategory,
    ClaimHistoryItem,
    ClaimSubmission,
    Decision,
    DocumentInput,
)
from app.services.policy_loader import PolicyLoader


@pytest.fixture
def orchestrator():
    return OrchestratorAgent(PolicyLoader())


@pytest.mark.asyncio
async def test_tc004_full_pipeline_approval(orchestrator):
    """TC004: Full pipeline — clean consultation approval."""
    submission = ClaimSubmission(
        member_id="EMP001",
        claim_category=ClaimCategory.CONSULTATION,
        treatment_date=date(2024, 11, 1),
        claimed_amount=1500,
        ytd_claims_amount=5000,
        documents=[
            DocumentInput(
                file_id="F007", actual_type="PRESCRIPTION",
                content={
                    "doctor_name": "Dr. Arun Sharma",
                    "patient_name": "Rajesh Kumar",
                    "diagnosis": "Viral Fever",
                    "date": "2024-11-01",
                },
            ),
            DocumentInput(
                file_id="F008", actual_type="HOSPITAL_BILL",
                content={
                    "hospital_name": "City Clinic, Bengaluru",
                    "patient_name": "Rajesh Kumar",
                    "date": "2024-11-01",
                    "line_items": [
                        {"description": "Consultation Fee", "amount": 1000},
                        {"description": "CBC Test", "amount": 300},
                        {"description": "Dengue NS1 Test", "amount": 200},
                    ],
                    "total": 1500,
                },
            ),
        ],
    )
    decision = await orchestrator.process(submission)

    assert decision.decision == Decision.APPROVED
    assert decision.approved_amount == 1350
    assert decision.confidence_score > 0.85
    assert decision.trace is not None
    assert len(decision.trace.steps) > 0


@pytest.mark.asyncio
async def test_tc001_document_gate_stops(orchestrator):
    """TC001: Wrong documents — pipeline stops at gate."""
    submission = ClaimSubmission(
        member_id="EMP001",
        claim_category=ClaimCategory.CONSULTATION,
        treatment_date=date(2024, 11, 1),
        claimed_amount=1500,
        documents=[
            DocumentInput(file_id="F001", file_name="dr_sharma_prescription.jpg", actual_type="PRESCRIPTION"),
            DocumentInput(file_id="F002", file_name="another_prescription.jpg", actual_type="PRESCRIPTION"),
        ],
    )
    decision = await orchestrator.process(submission)

    assert decision.decision is None
    assert len(decision.document_errors) > 0
    assert "HOSPITAL_BILL" in decision.document_errors[0].message


@pytest.mark.asyncio
async def test_tc011_graceful_degradation(orchestrator):
    """TC011: Simulated component failure — system continues."""
    submission = ClaimSubmission(
        member_id="EMP006",
        claim_category=ClaimCategory.ALTERNATIVE_MEDICINE,
        treatment_date=date(2024, 10, 28),
        claimed_amount=4000,
        simulate_component_failure=True,
        documents=[
            DocumentInput(
                file_id="F021", actual_type="PRESCRIPTION",
                content={
                    "doctor_name": "Vaidya T. Krishnan",
                    "diagnosis": "Chronic Joint Pain",
                    "treatment": "Panchakarma Therapy",
                },
            ),
            DocumentInput(
                file_id="F022", actual_type="HOSPITAL_BILL",
                content={
                    "hospital_name": "Ayur Wellness Centre",
                    "total": 4000,
                    "line_items": [
                        {"description": "Panchakarma Therapy (5 sessions)", "amount": 3000},
                        {"description": "Consultation", "amount": 1000},
                    ],
                },
            ),
        ],
    )
    decision = await orchestrator.process(submission)

    # Must not crash
    assert decision is not None
    # Should still reach a decision
    assert decision.decision is not None
    # Confidence should be reduced
    assert decision.confidence_score < 0.90
    # Should mention failure in notes or trace
    has_failure_note = any("fail" in n.lower() or "manual review" in n.lower() for n in decision.notes)
    assert has_failure_note


@pytest.mark.asyncio
async def test_tc009_fraud_manual_review(orchestrator):
    """TC009: Multiple same-day claims → MANUAL_REVIEW."""
    submission = ClaimSubmission(
        member_id="EMP008",
        claim_category=ClaimCategory.CONSULTATION,
        treatment_date=date(2024, 10, 30),
        claimed_amount=4800,
        claims_history=[
            ClaimHistoryItem(claim_id="CLM_0081", date="2024-10-30", amount=1200, provider="City Clinic A"),
            ClaimHistoryItem(claim_id="CLM_0082", date="2024-10-30", amount=1800, provider="City Clinic B"),
            ClaimHistoryItem(claim_id="CLM_0083", date="2024-10-30", amount=2100, provider="Wellness Center"),
        ],
        documents=[
            DocumentInput(
                file_id="F017", actual_type="PRESCRIPTION",
                content={"diagnosis": "Migraine", "doctor_name": "Dr. S. Khan"},
            ),
            DocumentInput(
                file_id="F018", actual_type="HOSPITAL_BILL",
                content={"total": 4800},
            ),
        ],
    )
    decision = await orchestrator.process(submission)

    assert decision.decision == Decision.MANUAL_REVIEW
    assert len(decision.fraud_signals) > 0
