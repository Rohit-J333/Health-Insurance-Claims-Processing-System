"""Tests for the Document Gate Agent."""

import pytest

from app.agents.document_gate import DocumentGateAgent
from app.models.schemas import ClaimCategory, DocumentErrorType, DocumentInput


@pytest.mark.asyncio
async def test_tc001_wrong_document_type(policy, trace):
    """TC001: Two prescriptions uploaded, no hospital bill."""
    agent = DocumentGateAgent(policy, trace)
    docs = [
        DocumentInput(file_id="F001", file_name="dr_sharma_prescription.jpg", actual_type="PRESCRIPTION"),
        DocumentInput(file_id="F002", file_name="another_prescription.jpg", actual_type="PRESCRIPTION"),
    ]
    result = await agent.process(docs, ClaimCategory.CONSULTATION, "EMP001")

    assert not result.passed
    assert len(result.errors) >= 1
    err = result.errors[0]
    assert err.error_type == DocumentErrorType.MISSING_REQUIRED
    assert "HOSPITAL_BILL" in err.message
    assert "PRESCRIPTION" in err.message


@pytest.mark.asyncio
async def test_tc002_unreadable_document(policy, trace):
    """TC002: Blurry pharmacy bill — ask re-upload, don't reject."""
    agent = DocumentGateAgent(policy, trace)
    docs = [
        DocumentInput(file_id="F003", file_name="prescription.jpg", actual_type="PRESCRIPTION", quality="GOOD"),
        DocumentInput(file_id="F004", file_name="blurry_bill.jpg", actual_type="PHARMACY_BILL", quality="UNREADABLE"),
    ]
    result = await agent.process(docs, ClaimCategory.PHARMACY, "EMP004")

    assert not result.passed
    assert any(e.error_type == DocumentErrorType.UNREADABLE for e in result.errors)
    unreadable_err = [e for e in result.errors if e.error_type == DocumentErrorType.UNREADABLE][0]
    assert "blurry_bill.jpg" in unreadable_err.message
    assert "re-upload" in unreadable_err.message.lower()


@pytest.mark.asyncio
async def test_tc003_different_patient_names(policy, trace):
    """TC003: Documents for different patients."""
    agent = DocumentGateAgent(policy, trace)
    docs = [
        DocumentInput(
            file_id="F005", file_name="prescription_rajesh.jpg",
            actual_type="PRESCRIPTION", patient_name_on_doc="Rajesh Kumar",
        ),
        DocumentInput(
            file_id="F006", file_name="bill_arjun.jpg",
            actual_type="HOSPITAL_BILL", patient_name_on_doc="Arjun Mehta",
        ),
    ]
    result = await agent.process(docs, ClaimCategory.CONSULTATION, "EMP001")

    assert not result.passed
    assert any(e.error_type == DocumentErrorType.NAME_MISMATCH for e in result.errors)
    name_err = [e for e in result.errors if e.error_type == DocumentErrorType.NAME_MISMATCH][0]
    assert "Rajesh Kumar" in name_err.message
    assert "Arjun Mehta" in name_err.message


@pytest.mark.asyncio
async def test_valid_documents_pass(policy, trace):
    """Happy path: correct documents pass the gate."""
    agent = DocumentGateAgent(policy, trace)
    docs = [
        DocumentInput(
            file_id="F007", actual_type="PRESCRIPTION",
            content={"patient_name": "Rajesh Kumar"},
        ),
        DocumentInput(
            file_id="F008", actual_type="HOSPITAL_BILL",
            content={"patient_name": "Rajesh Kumar"},
        ),
    ]
    result = await agent.process(docs, ClaimCategory.CONSULTATION, "EMP001")
    assert result.passed
    assert len(result.errors) == 0
