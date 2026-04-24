"""Adjudication Agent — applies policy rules to produce a claim decision.

Rule checks in order:
1. Exclusion check (global + category-specific line items)
2. Waiting period
3. Pre-authorization
4. Per-claim limit (on the working amount after exclusions)
5. Annual OPD limit
6. Fraud detection
7. Amount calculation (network discount BEFORE copay)
"""

from __future__ import annotations

from datetime import date

from app.agents.fraud_detection import FraudDetectionAgent
from app.models.schemas import (
    AmountBreakdown,
    ClaimCategory,
    ClaimHistoryItem,
    Decision,
    ExtractedDocument,
    ExtractedLineItem,
    FraudResult,
    LineItemDecision,
)
from app.services.policy_loader import PolicyLoader
from app.services.trace_logger import TraceLogger

AGENT_NAME = "adjudication"


class AdjudicationResult:
    def __init__(self):
        self.decision: Decision | None = None
        self.approved_amount: float | None = None
        self.rejection_reasons: list[str] = []
        self.line_item_decisions: list[LineItemDecision] = []
        self.amount_breakdown: AmountBreakdown | None = None
        self.fraud_result: FraudResult | None = None
        self.notes: list[str] = []


class AdjudicationAgent:
    def __init__(self, policy: PolicyLoader, trace: TraceLogger):
        self.policy = policy
        self.trace = trace

    async def process(
        self,
        claim_category: ClaimCategory,
        claimed_amount: float,
        treatment_date: date,
        member_id: str,
        hospital_name: str | None,
        ytd_claims_amount: float,
        claims_history: list[ClaimHistoryItem],
        extracted_docs: list[ExtractedDocument],
    ) -> AdjudicationResult:
        result = AdjudicationResult()
        cat_rules = self.policy.get_category_rules(claim_category.value)

        # Gather extracted info
        diagnosis = self._get_diagnosis(extracted_docs)
        all_line_items = self._get_all_line_items(extracted_docs, claimed_amount)
        hospital = hospital_name or self._get_hospital_name(extracted_docs)
        tests = self._get_tests(extracted_docs)

        # ── Check 1: Exclusion check ─────────────────────────────
        exclusion_result = self._check_exclusions(
            claim_category, diagnosis, all_line_items, result
        )
        if exclusion_result == "FULLY_EXCLUDED":
            return result

        # After exclusion filtering, determine working amount
        approved_items = [
            li for li in result.line_item_decisions if li.status == "APPROVED"
        ]
        has_line_decisions = len(result.line_item_decisions) > 0
        if has_line_decisions:
            working_amount = sum(li.amount for li in approved_items)
        else:
            working_amount = claimed_amount

        # ── Check 2: Waiting period ───────────────────────────────
        waiting_result = self._check_waiting_period(
            member_id, treatment_date, diagnosis
        )
        if waiting_result:
            result.decision = Decision.REJECTED
            result.rejection_reasons.append("WAITING_PERIOD")
            result.notes.append(waiting_result)
            return result

        # ── Check 3: Pre-authorization ────────────────────────────
        pre_auth_result = self._check_pre_auth(
            claim_category, tests, all_line_items, claimed_amount
        )
        if pre_auth_result:
            result.decision = Decision.REJECTED
            result.rejection_reasons.append("PRE_AUTH_MISSING")
            result.notes.append(pre_auth_result)
            return result

        # ── Check 4: Per-claim limit ──────────────────────────────
        # Effective limit = max(per_claim_limit, category_sub_limit).
        # Categories with higher sub-limits (dental 10k, diagnostic 10k,
        # pharmacy 15k) have their sub-limit as the effective cap.
        per_claim_limit = self.policy.per_claim_limit
        effective_limit = max(per_claim_limit, cat_rules.sub_limit)
        if working_amount > effective_limit:
            result.decision = Decision.REJECTED
            result.rejection_reasons.append("PER_CLAIM_EXCEEDED")
            result.notes.append(
                f"Amount ₹{working_amount:,.0f} exceeds the applicable limit "
                f"of ₹{effective_limit:,.0f} "
                f"(per-claim: ₹{per_claim_limit:,.0f}, "
                f"{claim_category.value.lower()} sub-limit: ₹{cat_rules.sub_limit:,.0f})."
            )
            self.trace.failed(
                AGENT_NAME,
                "per_claim_limit",
                f"Amount ₹{working_amount:,.0f} exceeds effective limit "
                f"of ₹{effective_limit:,.0f}. REJECTED.",
            )
            return result
        self.trace.passed(
            AGENT_NAME,
            "per_claim_limit",
            f"Amount ₹{working_amount:,.0f} within effective limit "
            f"of ₹{effective_limit:,.0f} "
            f"(per-claim: ₹{per_claim_limit:,.0f}, sub-limit: ₹{cat_rules.sub_limit:,.0f}).",
        )

        # ── Check 5: Annual OPD limit ────────────────────────────
        annual_limit = self.policy.annual_opd_limit
        remaining_annual = annual_limit - ytd_claims_amount
        if remaining_annual <= 0:
            result.decision = Decision.REJECTED
            result.rejection_reasons.append("ANNUAL_LIMIT_EXCEEDED")
            result.notes.append(
                f"Annual OPD limit of ₹{annual_limit:,.0f} already exhausted. "
                f"YTD claims: ₹{ytd_claims_amount:,.0f}."
            )
            self.trace.failed(
                AGENT_NAME,
                "annual_opd_limit",
                f"Annual limit ₹{annual_limit:,.0f} exhausted. "
                f"YTD: ₹{ytd_claims_amount:,.0f}. REJECTED.",
            )
            return result
        self.trace.passed(
            AGENT_NAME,
            "annual_opd_limit",
            f"YTD ₹{ytd_claims_amount:,.0f} + ₹{working_amount:,.0f} = "
            f"₹{ytd_claims_amount + working_amount:,.0f}, within annual "
            f"limit ₹{annual_limit:,.0f}.",
        )

        # ── Check 6: Fraud detection ──────────────────────────────
        fraud_agent = FraudDetectionAgent(self.policy, self.trace)
        fraud_result = await fraud_agent.process(
            member_id=member_id,
            claimed_amount=claimed_amount,
            treatment_date=str(treatment_date),
            claims_history=claims_history,
        )
        result.fraud_result = fraud_result

        if fraud_result.should_manual_review:
            result.decision = Decision.MANUAL_REVIEW
            result.notes.append(
                "Fraud signals detected. Routing to manual review."
            )
            for signal in fraud_result.signals:
                result.notes.append(f"Fraud flag: {signal.flag} — {signal.details}")
            return result

        # ── Check 7: Amount calculation ───────────────────────────
        breakdown = self._calculate_amount(
            working_amount=working_amount,
            claim_category=claim_category,
            hospital=hospital,
            ytd_claims_amount=ytd_claims_amount,
            cat_rules_copay=cat_rules.copay_percent,
            cat_rules_network_discount=cat_rules.network_discount_percent,
        )
        result.amount_breakdown = breakdown
        result.approved_amount = breakdown.final_approved

        # Determine final decision
        if has_line_decisions and any(
            li.status == "REJECTED" for li in result.line_item_decisions
        ):
            result.decision = Decision.PARTIAL
        else:
            result.decision = Decision.APPROVED

        self.trace.passed(
            AGENT_NAME,
            "final_decision",
            f"{result.decision.value} for ₹{result.approved_amount:,.0f}.",
        )

        return result

    def _get_diagnosis(self, docs: list[ExtractedDocument]) -> str | None:
        for doc in docs:
            if doc.diagnosis:
                return doc.diagnosis
            if doc.raw_content and "diagnosis" in doc.raw_content:
                return doc.raw_content["diagnosis"]
        # Fall back to treatment field
        for doc in docs:
            if doc.treatment:
                return doc.treatment
            if doc.raw_content and "treatment" in doc.raw_content:
                return doc.raw_content["treatment"]
        return None

    def _get_hospital_name(self, docs: list[ExtractedDocument]) -> str | None:
        for doc in docs:
            if doc.hospital_name:
                return doc.hospital_name
        return None

    def _get_tests(self, docs: list[ExtractedDocument]) -> list[str]:
        tests = []
        for doc in docs:
            tests.extend(doc.tests_ordered)
            if doc.raw_content and "test_name" in doc.raw_content:
                tests.append(doc.raw_content["test_name"])
            if doc.raw_content and "tests_ordered" in doc.raw_content:
                tests.extend(doc.raw_content["tests_ordered"])
        return list(set(tests))

    def _get_all_line_items(
        self,
        docs: list[ExtractedDocument],
        claimed_amount: float,
    ) -> list[ExtractedLineItem]:
        items = []
        for doc in docs:
            items.extend(doc.line_items)
        # Deduplicate by description
        seen = set()
        unique = []
        for item in items:
            if item.description not in seen:
                seen.add(item.description)
                unique.append(item)
        return unique

    def _check_exclusions(
        self,
        claim_category: ClaimCategory,
        diagnosis: str | None,
        line_items: list[ExtractedLineItem],
        result: AdjudicationResult,
    ) -> str | None:
        """Check exclusions. Returns 'FULLY_EXCLUDED' if entire claim is excluded."""

        # Check global exclusions against diagnosis
        if diagnosis:
            is_excluded, matching = self.policy.is_excluded(diagnosis)
            if is_excluded:
                result.decision = Decision.REJECTED
                result.rejection_reasons.append("EXCLUDED_CONDITION")
                result.notes.append(
                    f"The diagnosis/treatment '{diagnosis}' falls under "
                    f"the policy exclusion: '{matching}'."
                )
                self.trace.failed(
                    AGENT_NAME,
                    "exclusion_check",
                    f"Diagnosis '{diagnosis}' excluded under: '{matching}'. REJECTED.",
                )
                return "FULLY_EXCLUDED"

        # Also check line items against global exclusions
        if line_items and diagnosis:
            for item in line_items:
                is_excluded, matching = self.policy.is_excluded(diagnosis, item.description)
                if is_excluded and not any(
                    r == "EXCLUDED_CONDITION" for r in result.rejection_reasons
                ):
                    result.decision = Decision.REJECTED
                    result.rejection_reasons.append("EXCLUDED_CONDITION")
                    result.notes.append(
                        f"Line item '{item.description}' with diagnosis '{diagnosis}' "
                        f"falls under the policy exclusion: '{matching}'."
                    )
                    self.trace.failed(
                        AGENT_NAME,
                        "exclusion_check",
                        f"'{item.description}' excluded under: '{matching}'. REJECTED.",
                    )
                    return "FULLY_EXCLUDED"

        # For dental claims, check line items against covered/excluded procedures
        if claim_category == ClaimCategory.DENTAL and line_items:
            has_excluded = False
            has_approved = False

            for item in line_items:
                is_excl, excl_match = self.policy.is_dental_excluded(item.description)
                if is_excl:
                    has_excluded = True
                    result.line_item_decisions.append(
                        LineItemDecision(
                            description=item.description,
                            amount=item.amount,
                            status="REJECTED",
                            reason=f"Excluded procedure: {excl_match}",
                        )
                    )
                    self.trace.failed(
                        AGENT_NAME,
                        f"exclusion_line_item",
                        f"'{item.description}' is an excluded dental procedure ({excl_match}).",
                    )
                else:
                    has_approved = True
                    result.line_item_decisions.append(
                        LineItemDecision(
                            description=item.description,
                            amount=item.amount,
                            status="APPROVED",
                            reason="Covered procedure",
                        )
                    )
                    self.trace.passed(
                        AGENT_NAME,
                        f"exclusion_line_item",
                        f"'{item.description}' is a covered dental procedure.",
                    )

            if has_excluded and not has_approved:
                result.decision = Decision.REJECTED
                result.rejection_reasons.append("EXCLUDED_CONDITION")
                return "FULLY_EXCLUDED"

            if not has_excluded:
                self.trace.passed(
                    AGENT_NAME,
                    "exclusion_check",
                    "No excluded procedures found in dental claim.",
                )
        else:
            self.trace.passed(
                AGENT_NAME,
                "exclusion_check",
                f"Diagnosis '{diagnosis or 'N/A'}' is not an excluded condition.",
            )

        return None

    def _check_waiting_period(
        self,
        member_id: str,
        treatment_date: date,
        diagnosis: str | None,
    ) -> str | None:
        """Returns rejection note if in waiting period, None otherwise."""
        join_date = self.policy.get_member_join_date(member_id)
        if not join_date:
            self.trace.passed(
                AGENT_NAME,
                "waiting_period",
                "Member join date not found; skipping waiting period check.",
            )
            return None

        days_since_join = (treatment_date - join_date).days

        # Check initial waiting period
        initial = self.policy.initial_waiting_period_days
        if days_since_join < initial:
            msg = (
                f"Member joined on {join_date}. Treatment date {treatment_date} "
                f"is only {days_since_join} days after joining, within the "
                f"{initial}-day initial waiting period."
            )
            self.trace.failed(AGENT_NAME, "waiting_period", msg)
            return msg

        # Check condition-specific waiting period
        if diagnosis:
            condition_days = self.policy.get_condition_waiting_period(diagnosis)
            if condition_days and days_since_join < condition_days:
                eligible_date = date.fromordinal(
                    join_date.toordinal() + condition_days
                )
                msg = (
                    f"Member joined on {join_date}. Treatment for '{diagnosis}' "
                    f"on {treatment_date} is only {days_since_join} days after "
                    f"joining. The waiting period for this condition is "
                    f"{condition_days} days. The member will be eligible from "
                    f"{eligible_date}."
                )
                self.trace.failed(AGENT_NAME, "waiting_period", msg)
                return msg

        self.trace.passed(
            AGENT_NAME,
            "waiting_period",
            f"Member joined {join_date}, treatment {treatment_date} "
            f"({days_since_join} days). No applicable waiting period.",
        )
        return None

    def _check_pre_auth(
        self,
        claim_category: ClaimCategory,
        tests: list[str],
        line_items: list[ExtractedLineItem],
        claimed_amount: float,
    ) -> str | None:
        """Returns rejection note if pre-auth is required but missing."""
        if claim_category != ClaimCategory.DIAGNOSTIC:
            self.trace.passed(
                AGENT_NAME,
                "pre_auth_check",
                f"Pre-authorization not required for {claim_category.value}.",
            )
            return None

        # Check if any test requires pre-auth
        all_test_names = tests[:]
        for item in line_items:
            all_test_names.append(item.description)

        for test_name in all_test_names:
            if self.policy.requires_pre_auth(test_name, claimed_amount):
                msg = (
                    f"Pre-authorization is required for '{test_name}' when "
                    f"the amount exceeds ₹10,000 (claimed: ₹{claimed_amount:,.0f}). "
                    f"No pre-authorization was provided. Please obtain "
                    f"pre-authorization and resubmit the claim."
                )
                self.trace.failed(AGENT_NAME, "pre_auth_check", msg)
                return msg

        self.trace.passed(
            AGENT_NAME,
            "pre_auth_check",
            "No tests requiring pre-authorization, or amounts within threshold.",
        )
        return None

    def _calculate_amount(
        self,
        working_amount: float,
        claim_category: ClaimCategory,
        hospital: str | None,
        ytd_claims_amount: float,
        cat_rules_copay: float,
        cat_rules_network_discount: float,
    ) -> AmountBreakdown:
        """Calculate the final approved amount.

        Order: network discount (BEFORE copay) → copay → annual limit cap.
        """
        current = working_amount

        breakdown = AmountBreakdown(
            original_amount=working_amount,
            final_approved=0,
        )
        breakdown.after_exclusions = current

        # Network discount (BEFORE copay) — this is critical for TC010
        is_network = self.policy.is_network_hospital(hospital) if hospital else False
        if is_network and cat_rules_network_discount > 0:
            discount_pct = cat_rules_network_discount
            discount_amount = current * (discount_pct / 100)
            after_discount = current - discount_amount
            breakdown.network_discount_applied = discount_pct
            breakdown.after_network_discount = after_discount
            self.trace.passed(
                AGENT_NAME,
                "network_discount",
                f"{hospital} is a network hospital. {discount_pct}% discount "
                f"applied: ₹{current:,.0f} → ₹{after_discount:,.0f}.",
            )
            current = after_discount
        else:
            reason = "not a network hospital" if hospital else "no hospital specified"
            self.trace.passed(
                AGENT_NAME,
                "network_discount",
                f"No network discount applied ({reason}).",
            )

        # Copay
        if cat_rules_copay > 0:
            copay_amount = current * (cat_rules_copay / 100)
            after_copay = current - copay_amount
            breakdown.copay_percent = cat_rules_copay
            breakdown.copay_amount = copay_amount
            breakdown.after_copay = after_copay
            self.trace.passed(
                AGENT_NAME,
                "copay",
                f"{cat_rules_copay}% co-pay applied: ₹{current:,.0f} → "
                f"₹{after_copay:,.0f} (₹{copay_amount:,.0f} deducted).",
            )
            current = after_copay
        else:
            self.trace.passed(
                AGENT_NAME,
                "copay",
                "No co-pay for this category.",
            )

        # Annual limit remaining cap
        remaining = self.policy.annual_opd_limit - ytd_claims_amount
        if current > remaining:
            current = remaining
            breakdown.annual_limit_cap = remaining
            self.trace.passed(
                AGENT_NAME,
                "annual_limit_cap",
                f"Capped at remaining annual limit: ₹{remaining:,.0f}.",
            )

        breakdown.final_approved = round(current, 2)
        return breakdown
