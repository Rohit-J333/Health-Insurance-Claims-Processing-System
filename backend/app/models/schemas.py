"""Pydantic models for the claims processing system.

Defines all input, output, trace, and intermediate data structures
used across agents and API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────

class ClaimCategory(str, Enum):
    CONSULTATION = "CONSULTATION"
    DIAGNOSTIC = "DIAGNOSTIC"
    PHARMACY = "PHARMACY"
    DENTAL = "DENTAL"
    VISION = "VISION"
    ALTERNATIVE_MEDICINE = "ALTERNATIVE_MEDICINE"


class Decision(str, Enum):
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class TraceStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class DocumentErrorType(str, Enum):
    MISSING_REQUIRED = "MISSING_REQUIRED"
    UNREADABLE = "UNREADABLE"
    NAME_MISMATCH = "NAME_MISMATCH"
    WRONG_TYPE = "WRONG_TYPE"


# ── Input Models ───────────────────────────────────────────────────────

class ClaimHistoryItem(BaseModel):
    claim_id: str
    date: str
    amount: float
    provider: str | None = None


class DocumentInput(BaseModel):
    file_id: str
    file_name: str | None = None
    actual_type: str
    quality: str | None = None  # GOOD, UNREADABLE
    patient_name_on_doc: str | None = None
    content: dict[str, Any] | None = None  # Structured content for test cases


class ClaimSubmission(BaseModel):
    member_id: str
    policy_id: str = "PLUM_GHI_2024"
    claim_category: ClaimCategory
    treatment_date: date
    claimed_amount: float
    hospital_name: str | None = None
    ytd_claims_amount: float = 0
    claims_history: list[ClaimHistoryItem] = []
    documents: list[DocumentInput] = []
    simulate_component_failure: bool = False


# ── Trace Models ───────────────────────────────────────────────────────

class TraceStep(BaseModel):
    agent: str
    check_name: str
    status: TraceStatus
    details: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence_impact: float = 0.0  # negative = reduced


class ClaimTrace(BaseModel):
    claim_id: str
    steps: list[TraceStep] = []
    overall_confidence: float = 1.0


# ── Extraction Models ──────────────────────────────────────────────────

class ExtractedLineItem(BaseModel):
    description: str
    amount: float


class ExtractedDocument(BaseModel):
    file_id: str
    document_type: str
    patient_name: str | None = None
    doctor_name: str | None = None
    doctor_registration: str | None = None
    hospital_name: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medicines: list[str] = []
    tests_ordered: list[str] = []
    line_items: list[ExtractedLineItem] = []
    total_amount: float | None = None
    date: str | None = None
    confidence: float = 1.0
    raw_content: dict[str, Any] | None = None


# ── Document Gate Models ───────────────────────────────────────────────

class DocumentError(BaseModel):
    document_id: str | None = None
    error_type: DocumentErrorType
    message: str  # Specific, actionable message


class DocumentGateResult(BaseModel):
    passed: bool
    errors: list[DocumentError] = []


# ── Adjudication Models ───────────────────────────────────────────────

class LineItemDecision(BaseModel):
    description: str
    amount: float
    status: Literal["APPROVED", "REJECTED"]
    reason: str | None = None


class FraudSignal(BaseModel):
    flag: str
    details: str


class FraudResult(BaseModel):
    signals: list[FraudSignal] = []
    should_manual_review: bool = False


class AmountBreakdown(BaseModel):
    original_amount: float
    after_exclusions: float | None = None
    network_discount_applied: float | None = None
    after_network_discount: float | None = None
    copay_percent: float | None = None
    copay_amount: float | None = None
    after_copay: float | None = None
    sub_limit_cap: float | None = None
    per_claim_limit_cap: float | None = None
    annual_limit_cap: float | None = None
    final_approved: float


# ── Final Output ───────────────────────────────────────────────────────

class ClaimDecision(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"CLM-{uuid.uuid4().hex[:8].upper()}")
    decision: Decision | None = None
    approved_amount: float | None = None
    claimed_amount: float
    rejection_reasons: list[str] = []
    confidence_score: float = 1.0
    line_item_decisions: list[LineItemDecision] = []
    amount_breakdown: AmountBreakdown | None = None
    document_errors: list[DocumentError] = []
    fraud_signals: list[FraudSignal] = []
    trace: ClaimTrace | None = None
    notes: list[str] = []


# ── Database Model ─────────────────────────────────────────────────────

class ClaimSummary(BaseModel):
    claim_id: str
    member_id: str
    claim_category: str
    treatment_date: date
    claimed_amount: float
    decision: str | None = None
    approved_amount: float | None = None
    confidence_score: float | None = None
    created_at: datetime


# ── Policy Models (for typed access) ──────────────────────────────────

class CategoryRules(BaseModel):
    sub_limit: float
    copay_percent: float
    network_discount_percent: float = 0
    requires_prescription: bool = False
    requires_pre_auth: bool = False
    pre_auth_threshold: float | None = None
    high_value_tests_requiring_pre_auth: list[str] = []
    covered: bool = True
    covered_procedures: list[str] = []
    excluded_procedures: list[str] = []
    covered_items: list[str] = []
    excluded_items: list[str] = []
    branded_drug_copay_percent: float | None = None
    generic_mandatory: bool = False
    requires_dental_report: bool = False
    requires_registered_practitioner: bool = False
    max_sessions_per_year: int | None = None
    covered_systems: list[str] = []


class MemberInfo(BaseModel):
    member_id: str
    name: str
    date_of_birth: str
    gender: str
    relationship: str
    join_date: str | None = None
    dependents: list[str] = []
    primary_member_id: str | None = None
