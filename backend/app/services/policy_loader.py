"""Loads and provides typed access to policy_terms.json.

All policy rules are read from the JSON file — nothing is hardcoded.
"""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import POLICY_TERMS_PATH
from app.models.schemas import CategoryRules, MemberInfo


class PolicyLoader:
    def __init__(self, path: Path | None = None):
        self._path = path or POLICY_TERMS_PATH
        with open(self._path, "r") as f:
            self._data: dict[str, Any] = json.load(f)

    @property
    def raw(self) -> dict[str, Any]:
        return self._data

    @property
    def policy_id(self) -> str:
        return self._data["policy_id"]

    @property
    def policy_start_date(self) -> date:
        return date.fromisoformat(self._data["policy_holder"]["policy_start_date"])

    @property
    def policy_end_date(self) -> date:
        return date.fromisoformat(self._data["policy_holder"]["policy_end_date"])

    # ── Coverage ───────────────────────────────────────────────────

    @property
    def sum_insured(self) -> float:
        return self._data["coverage"]["sum_insured_per_employee"]

    @property
    def annual_opd_limit(self) -> float:
        return self._data["coverage"]["annual_opd_limit"]

    @property
    def per_claim_limit(self) -> float:
        return self._data["coverage"]["per_claim_limit"]

    # ── Category Rules ─────────────────────────────────────────────

    def get_category_rules(self, category: str) -> CategoryRules:
        key = category.lower()
        if key not in self._data["opd_categories"]:
            raise ValueError(f"Unknown category: {category}")
        return CategoryRules(**self._data["opd_categories"][key])

    # ── Document Requirements ──────────────────────────────────────

    def get_required_documents(self, category: str) -> list[str]:
        reqs = self._data.get("document_requirements", {})
        cat_reqs = reqs.get(category.upper(), {})
        return cat_reqs.get("required", [])

    def get_optional_documents(self, category: str) -> list[str]:
        reqs = self._data.get("document_requirements", {})
        cat_reqs = reqs.get(category.upper(), {})
        return cat_reqs.get("optional", [])

    # ── Waiting Periods ────────────────────────────────────────────

    @property
    def initial_waiting_period_days(self) -> int:
        return self._data["waiting_periods"]["initial_waiting_period_days"]

    @property
    def pre_existing_conditions_days(self) -> int:
        return self._data["waiting_periods"]["pre_existing_conditions_days"]

    def get_condition_waiting_period(self, condition: str) -> int | None:
        """Return waiting period in days for a specific condition, or None.

        Uses word-boundary matching to avoid false positives
        (e.g. 'hernia' must not match 'herniation').
        """
        import re
        specific = self._data["waiting_periods"].get("specific_conditions", {})
        if condition in specific:
            return specific[condition]
        condition_lower = condition.lower()

        # Aliases for common abbreviations/synonyms
        aliases = {
            "diabetes": ["diabetes", "diabetic", "t2dm", "t1dm"],
            "hypertension": ["hypertension", "htn", "high blood pressure"],
            "thyroid_disorders": ["thyroid", "hypothyroid", "hyperthyroid"],
            "joint_replacement": ["joint replacement", "knee replacement", "hip replacement"],
            "maternity": ["maternity", "pregnancy", "delivery", "childbirth"],
            "mental_health": ["mental health", "depression", "anxiety"],
            "obesity_treatment": ["obesity", "bariatric", "weight loss"],
            "hernia": ["hernia repair", "hernia surgery", "inguinal hernia", "umbilical hernia"],
            "cataract": ["cataract"],
        }

        for key, days in specific.items():
            patterns = aliases.get(key, [key.replace("_", " ")])
            for pattern in patterns:
                # Word boundary match
                if re.search(r"\b" + re.escape(pattern) + r"\b", condition_lower):
                    return days
        return None

    # ── Exclusions ─────────────────────────────────────────────────

    @property
    def exclusions(self) -> list[str]:
        return self._data["exclusions"]["conditions"]

    @property
    def dental_exclusions(self) -> list[str]:
        return self._data["exclusions"].get("dental_exclusions", [])

    @property
    def vision_exclusions(self) -> list[str]:
        return self._data["exclusions"].get("vision_exclusions", [])

    def is_excluded(self, diagnosis: str, line_item_desc: str | None = None) -> tuple[bool, str | None]:
        """Check if a diagnosis or line item is excluded. Returns (is_excluded, matching_exclusion)."""
        check_text = f"{diagnosis} {line_item_desc or ''}".lower()
        for excl in self.exclusions:
            excl_lower = excl.lower()
            # Check various keywords from the exclusion
            keywords = [w for w in excl_lower.split() if len(w) > 3]
            if any(kw in check_text for kw in keywords):
                return True, excl
        return False, None

    def is_dental_excluded(self, procedure: str) -> tuple[bool, str | None]:
        """Check if a dental procedure is excluded."""
        proc_lower = procedure.lower()
        # Check excluded_procedures from category
        cat_rules = self.get_category_rules("DENTAL")
        for excl in cat_rules.excluded_procedures:
            if excl.lower() in proc_lower or proc_lower in excl.lower():
                return True, excl
        # Also check dental_exclusions from exclusions section
        for excl in self.dental_exclusions:
            if excl.lower() in proc_lower or proc_lower in excl.lower():
                return True, excl
        return False, None

    def is_dental_covered(self, procedure: str) -> bool:
        """Check if a dental procedure is in the covered list."""
        cat_rules = self.get_category_rules("DENTAL")
        proc_lower = procedure.lower()
        for covered in cat_rules.covered_procedures:
            if covered.lower() in proc_lower or proc_lower in covered.lower():
                return True
        return False

    # ── Pre-Authorization ──────────────────────────────────────────

    @property
    def pre_auth_required_for(self) -> list[str]:
        return self._data["pre_authorization"]["required_for"]

    def requires_pre_auth(self, test_name: str, amount: float) -> bool:
        """Check if a test/procedure requires pre-authorization."""
        test_lower = test_name.lower()
        cat_rules = self.get_category_rules("DIAGNOSTIC")
        for test in cat_rules.high_value_tests_requiring_pre_auth:
            if test.lower() in test_lower:
                threshold = cat_rules.pre_auth_threshold or 10000
                return amount > threshold
        return False

    # ── Network Hospitals ──────────────────────────────────────────

    @property
    def network_hospitals(self) -> list[str]:
        return self._data["network_hospitals"]

    def is_network_hospital(self, hospital_name: str) -> bool:
        if not hospital_name:
            return False
        name_lower = hospital_name.lower()
        return any(h.lower() in name_lower or name_lower in h.lower()
                    for h in self.network_hospitals)

    # ── Fraud Thresholds ───────────────────────────────────────────

    @property
    def same_day_claims_limit(self) -> int:
        return self._data["fraud_thresholds"]["same_day_claims_limit"]

    @property
    def monthly_claims_limit(self) -> int:
        return self._data["fraud_thresholds"]["monthly_claims_limit"]

    @property
    def high_value_claim_threshold(self) -> float:
        return self._data["fraud_thresholds"]["high_value_claim_threshold"]

    @property
    def auto_manual_review_above(self) -> float:
        return self._data["fraud_thresholds"]["auto_manual_review_above"]

    # ── Submission Rules ───────────────────────────────────────────

    @property
    def submission_deadline_days(self) -> int:
        return self._data["submission_rules"]["deadline_days_from_treatment"]

    @property
    def minimum_claim_amount(self) -> float:
        return self._data["submission_rules"]["minimum_claim_amount"]

    # ── Members ────────────────────────────────────────────────────

    def get_member(self, member_id: str) -> MemberInfo | None:
        for m in self._data["members"]:
            if m["member_id"] == member_id:
                return MemberInfo(**m)
        return None

    def get_member_join_date(self, member_id: str) -> date | None:
        member = self.get_member(member_id)
        if member and member.join_date:
            return date.fromisoformat(member.join_date)
        # Check if it's a dependent — use primary member's join date
        if member and member.primary_member_id:
            primary = self.get_member(member.primary_member_id)
            if primary and primary.join_date:
                return date.fromisoformat(primary.join_date)
        return None


@lru_cache(maxsize=1)
def get_policy() -> PolicyLoader:
    return PolicyLoader()
