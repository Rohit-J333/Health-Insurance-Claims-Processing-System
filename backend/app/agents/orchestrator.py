"""Orchestrator Agent — pipeline controller for claim processing.

Runs agents sequentially: Document Gate → Extraction → Adjudication.
Handles failures gracefully (TC011): wraps each agent in try/except,
logs errors to trace, reduces confidence, and continues processing.
"""

from __future__ import annotations

import logging

from app.agents.adjudication import AdjudicationAgent
from app.agents.document_gate import DocumentGateAgent
from app.agents.extraction import ExtractionAgent
from app.models.schemas import (
    ClaimDecision,
    ClaimSubmission,
    Decision,
)
from app.services.policy_loader import PolicyLoader
from app.services.trace_logger import TraceLogger

logger = logging.getLogger(__name__)

AGENT_NAME = "orchestrator"


class OrchestratorAgent:
    def __init__(self, policy: PolicyLoader):
        self.policy = policy

    async def process(self, submission: ClaimSubmission) -> ClaimDecision:
        import uuid
        claim_id = f"CLM-{submission.member_id}-{submission.treatment_date}-{uuid.uuid4().hex[:6]}"
        trace = TraceLogger(claim_id)

        decision = ClaimDecision(
            claim_id=claim_id,
            claimed_amount=submission.claimed_amount,
        )

        trace.passed(
            AGENT_NAME,
            "claim_received",
            f"Claim received: member={submission.member_id}, "
            f"category={submission.claim_category.value}, "
            f"amount=₹{submission.claimed_amount:,.0f}.",
        )

        # ── Stage 1: Document Gate ────────────────────────────────
        try:
            gate_agent = DocumentGateAgent(self.policy, trace)
            gate_result = await gate_agent.process(
                documents=submission.documents,
                claim_category=submission.claim_category,
                member_id=submission.member_id,
            )

            if not gate_result.passed:
                decision.document_errors = gate_result.errors
                decision.confidence_score = trace.confidence
                decision.trace = trace.trace
                decision.notes = [
                    "Claim processing stopped due to document issues. "
                    "Please resolve the errors and resubmit."
                ]
                return decision

        except Exception as e:
            logger.error(f"Document Gate failed: {e}")
            trace.error(
                AGENT_NAME,
                "document_gate_failure",
                f"Document Gate agent failed: {e}. Proceeding with caution.",
            )

        # ── Stage 2: Extraction ───────────────────────────────────
        extracted_docs = []
        try:
            if submission.simulate_component_failure:
                raise RuntimeError(
                    "Simulated component failure in Extraction Agent "
                    "(simulate_component_failure=true)"
                )

            extraction_agent = ExtractionAgent(trace)
            extracted_docs = await extraction_agent.process(submission.documents)

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            trace.error(
                AGENT_NAME,
                "extraction_failure",
                f"Extraction agent failed: {e}. "
                f"Proceeding with available data from document content fields.",
                confidence_impact=-0.20,
            )
            decision.notes.append(
                "Extraction component failed. Processing continued with "
                "limited data. Manual review is recommended."
            )
            # Fall back to minimal extraction from content fields
            extracted_docs = self._fallback_extraction(submission)

        # ── Stage 3: Adjudication ────────��────────────────────────
        try:
            adjudication_agent = AdjudicationAgent(self.policy, trace)
            adj_result = await adjudication_agent.process(
                claim_category=submission.claim_category,
                claimed_amount=submission.claimed_amount,
                treatment_date=submission.treatment_date,
                member_id=submission.member_id,
                hospital_name=submission.hospital_name,
                ytd_claims_amount=submission.ytd_claims_amount,
                claims_history=submission.claims_history,
                extracted_docs=extracted_docs,
            )

            decision.decision = adj_result.decision
            decision.approved_amount = adj_result.approved_amount
            decision.rejection_reasons = adj_result.rejection_reasons
            decision.line_item_decisions = adj_result.line_item_decisions
            decision.amount_breakdown = adj_result.amount_breakdown
            if adj_result.fraud_result:
                decision.fraud_signals = adj_result.fraud_result.signals
            decision.notes.extend(adj_result.notes)

        except Exception as e:
            logger.error(f"Adjudication failed: {e}")
            trace.error(
                AGENT_NAME,
                "adjudication_failure",
                f"Adjudication agent failed: {e}. "
                f"Routing to manual review.",
                confidence_impact=-0.20,
            )
            decision.decision = Decision.MANUAL_REVIEW
            decision.notes.append(
                f"Adjudication component failed: {e}. "
                f"Manual review required."
            )

        # ── Finalize ────���─────────────────────────────────────────
        decision.confidence_score = trace.confidence
        decision.trace = trace.trace

        # If component failed and we still got a decision, recommend manual review
        if submission.simulate_component_failure and decision.decision not in (
            Decision.MANUAL_REVIEW, None
        ):
            decision.notes.append(
                "Manual review recommended due to incomplete processing "
                "(one or more components experienced failures)."
            )

        return decision

    def _fallback_extraction(self, submission: ClaimSubmission) -> list:
        """Minimal extraction from document content fields when Extraction agent fails."""
        from app.models.schemas import ExtractedDocument, ExtractedLineItem

        docs = []
        for doc in submission.documents:
            if doc.content:
                line_items = [
                    ExtractedLineItem(
                        description=item["description"], amount=item["amount"]
                    )
                    for item in doc.content.get("line_items", [])
                ]
                docs.append(
                    ExtractedDocument(
                        file_id=doc.file_id,
                        document_type=doc.actual_type,
                        patient_name=doc.content.get("patient_name"),
                        doctor_name=doc.content.get("doctor_name"),
                        hospital_name=doc.content.get("hospital_name"),
                        diagnosis=doc.content.get("diagnosis"),
                        treatment=doc.content.get("treatment"),
                        medicines=doc.content.get("medicines", []),
                        tests_ordered=doc.content.get("tests_ordered", []),
                        line_items=line_items,
                        total_amount=doc.content.get("total"),
                        date=doc.content.get("date"),
                        confidence=0.5,
                    )
                )
        return docs
