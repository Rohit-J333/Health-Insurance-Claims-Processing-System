"""Tests for the Adjudication Agent."""

import pytest
from datetime import date

from app.agents.adjudication import AdjudicationAgent
from app.models.schemas import (
    ClaimCategory,
    Decision,
    ExtractedDocument,
    ExtractedLineItem,
)


@pytest.mark.asyncio
async def test_tc004_clean_approval(policy, trace):
    """TC004: Clean consultation, ₹1500, 10% copay = ₹1350 approved."""
    agent = AdjudicationAgent(policy, trace)
    docs = [
        ExtractedDocument(
            file_id="F007", document_type="PRESCRIPTION",
            patient_name="Rajesh Kumar", diagnosis="Viral Fever",
            doctor_name="Dr. Arun Sharma",
        ),
        ExtractedDocument(
            file_id="F008", document_type="HOSPITAL_BILL",
            patient_name="Rajesh Kumar", hospital_name="City Clinic, Bengaluru",
            line_items=[
                ExtractedLineItem(description="Consultation Fee", amount=1000),
                ExtractedLineItem(description="CBC Test", amount=300),
                ExtractedLineItem(description="Dengue NS1 Test", amount=200),
            ],
            total_amount=1500,
        ),
    ]
    result = await agent.process(
        claim_category=ClaimCategory.CONSULTATION,
        claimed_amount=1500,
        treatment_date=date(2024, 11, 1),
        member_id="EMP001",
        hospital_name=None,
        ytd_claims_amount=5000,
        claims_history=[],
        extracted_docs=docs,
    )
    assert result.decision == Decision.APPROVED
    assert result.approved_amount == 1350  # 1500 * 0.90


@pytest.mark.asyncio
async def test_tc005_waiting_period_diabetes(policy, trace):
    """TC005: Diabetes claim within 90-day waiting period."""
    agent = AdjudicationAgent(policy, trace)
    docs = [
        ExtractedDocument(
            file_id="F009", document_type="PRESCRIPTION",
            patient_name="Vikram Joshi",
            diagnosis="Type 2 Diabetes Mellitus",
        ),
        ExtractedDocument(
            file_id="F010", document_type="HOSPITAL_BILL",
            total_amount=3000,
        ),
    ]
    result = await agent.process(
        claim_category=ClaimCategory.CONSULTATION,
        claimed_amount=3000,
        treatment_date=date(2024, 10, 15),
        member_id="EMP005",  # joined 2024-09-01
        hospital_name=None,
        ytd_claims_amount=0,
        claims_history=[],
        extracted_docs=docs,
    )
    assert result.decision == Decision.REJECTED
    assert "WAITING_PERIOD" in result.rejection_reasons


@pytest.mark.asyncio
async def test_tc006_dental_partial_approval(policy, trace):
    """TC006: Root canal (covered) + teeth whitening (excluded) = PARTIAL."""
    agent = AdjudicationAgent(policy, trace)
    docs = [
        ExtractedDocument(
            file_id="F011", document_type="HOSPITAL_BILL",
            patient_name="Priya Singh",
            hospital_name="Smile Dental Clinic",
            line_items=[
                ExtractedLineItem(description="Root Canal Treatment", amount=8000),
                ExtractedLineItem(description="Teeth Whitening", amount=4000),
            ],
            total_amount=12000,
        ),
    ]
    result = await agent.process(
        claim_category=ClaimCategory.DENTAL,
        claimed_amount=12000,
        treatment_date=date(2024, 10, 15),
        member_id="EMP002",
        hospital_name=None,
        ytd_claims_amount=0,
        claims_history=[],
        extracted_docs=docs,
    )
    assert result.decision == Decision.PARTIAL
    assert result.approved_amount == 8000
    approved_items = [li for li in result.line_item_decisions if li.status == "APPROVED"]
    rejected_items = [li for li in result.line_item_decisions if li.status == "REJECTED"]
    assert len(approved_items) == 1
    assert len(rejected_items) == 1
    assert approved_items[0].description == "Root Canal Treatment"
    assert rejected_items[0].description == "Teeth Whitening"


@pytest.mark.asyncio
async def test_tc007_mri_without_preauth(policy, trace):
    """TC007: MRI ₹15,000 without pre-authorization."""
    agent = AdjudicationAgent(policy, trace)
    docs = [
        ExtractedDocument(
            file_id="F012", document_type="PRESCRIPTION",
            diagnosis="Suspected Lumbar Disc Herniation",
            tests_ordered=["MRI Lumbar Spine"],
        ),
        ExtractedDocument(
            file_id="F013", document_type="LAB_REPORT",
            raw_content={"test_name": "MRI Lumbar Spine"},
        ),
        ExtractedDocument(
            file_id="F014", document_type="HOSPITAL_BILL",
            line_items=[ExtractedLineItem(description="MRI Lumbar Spine", amount=15000)],
            total_amount=15000,
        ),
    ]
    result = await agent.process(
        claim_category=ClaimCategory.DIAGNOSTIC,
        claimed_amount=15000,
        treatment_date=date(2024, 11, 2),
        member_id="EMP007",
        hospital_name=None,
        ytd_claims_amount=0,
        claims_history=[],
        extracted_docs=docs,
    )
    assert result.decision == Decision.REJECTED
    assert "PRE_AUTH_MISSING" in result.rejection_reasons


@pytest.mark.asyncio
async def test_tc008_per_claim_limit_exceeded(policy, trace):
    """TC008: Claimed ₹7,500 exceeds per-claim limit of ₹5,000."""
    agent = AdjudicationAgent(policy, trace)
    docs = [
        ExtractedDocument(
            file_id="F015", document_type="PRESCRIPTION",
            diagnosis="Gastroenteritis",
        ),
        ExtractedDocument(
            file_id="F016", document_type="HOSPITAL_BILL",
            total_amount=7500,
        ),
    ]
    result = await agent.process(
        claim_category=ClaimCategory.CONSULTATION,
        claimed_amount=7500,
        treatment_date=date(2024, 10, 20),
        member_id="EMP003",
        hospital_name=None,
        ytd_claims_amount=10000,
        claims_history=[],
        extracted_docs=docs,
    )
    assert result.decision == Decision.REJECTED
    assert "PER_CLAIM_EXCEEDED" in result.rejection_reasons


@pytest.mark.asyncio
async def test_tc010_network_hospital_discount(policy, trace):
    """TC010: Apollo Hospitals — 20% discount then 10% copay = ₹3,240."""
    agent = AdjudicationAgent(policy, trace)
    docs = [
        ExtractedDocument(
            file_id="F019", document_type="PRESCRIPTION",
            patient_name="Deepak Shah", diagnosis="Acute Bronchitis",
        ),
        ExtractedDocument(
            file_id="F020", document_type="HOSPITAL_BILL",
            patient_name="Deepak Shah", hospital_name="Apollo Hospitals",
            line_items=[
                ExtractedLineItem(description="Consultation Fee", amount=1500),
                ExtractedLineItem(description="Medicines", amount=3000),
            ],
            total_amount=4500,
        ),
    ]
    result = await agent.process(
        claim_category=ClaimCategory.CONSULTATION,
        claimed_amount=4500,
        treatment_date=date(2024, 11, 3),
        member_id="EMP010",
        hospital_name="Apollo Hospitals",
        ytd_claims_amount=8000,
        claims_history=[],
        extracted_docs=docs,
    )
    assert result.decision == Decision.APPROVED
    assert result.approved_amount == 3240  # 4500 * 0.80 * 0.90
    assert result.amount_breakdown is not None
    assert result.amount_breakdown.network_discount_applied == 20
    assert result.amount_breakdown.copay_percent == 10


@pytest.mark.asyncio
async def test_tc012_excluded_treatment(policy, trace):
    """TC012: Obesity/bariatric treatment — excluded."""
    agent = AdjudicationAgent(policy, trace)
    docs = [
        ExtractedDocument(
            file_id="F023", document_type="PRESCRIPTION",
            diagnosis="Morbid Obesity — BMI 37",
            treatment="Bariatric Consultation and Customised Diet Plan",
        ),
        ExtractedDocument(
            file_id="F024", document_type="HOSPITAL_BILL",
            line_items=[
                ExtractedLineItem(description="Bariatric Consultation", amount=3000),
                ExtractedLineItem(description="Personalised Diet and Nutrition Program", amount=5000),
            ],
            total_amount=8000,
        ),
    ]
    result = await agent.process(
        claim_category=ClaimCategory.CONSULTATION,
        claimed_amount=8000,
        treatment_date=date(2024, 10, 18),
        member_id="EMP009",
        hospital_name=None,
        ytd_claims_amount=0,
        claims_history=[],
        extracted_docs=docs,
    )
    assert result.decision == Decision.REJECTED
    assert "EXCLUDED_CONDITION" in result.rejection_reasons
