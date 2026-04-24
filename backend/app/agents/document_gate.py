"""Document Gate Agent — early validation before any claim processing.

Performs three checks:
1. Type completeness — are all required document types present?
2. Quality check — are all documents readable?
3. Name consistency — do all documents belong to the same patient?

If any check fails, processing stops and specific errors are returned.
"""

from __future__ import annotations

from collections import Counter

from app.models.schemas import (
    ClaimCategory,
    DocumentError,
    DocumentErrorType,
    DocumentGateResult,
    DocumentInput,
)
from app.services.policy_loader import PolicyLoader
from app.services.trace_logger import TraceLogger

AGENT_NAME = "document_gate"


class DocumentGateAgent:
    def __init__(self, policy: PolicyLoader, trace: TraceLogger):
        self.policy = policy
        self.trace = trace

    async def process(
        self,
        documents: list[DocumentInput],
        claim_category: ClaimCategory,
        member_id: str,
    ) -> DocumentGateResult:
        errors: list[DocumentError] = []

        # Check 1: Type completeness
        type_errors = self._check_type_completeness(documents, claim_category)
        errors.extend(type_errors)

        # Check 2: Quality
        quality_errors = self._check_quality(documents)
        errors.extend(quality_errors)

        # Check 3: Name consistency (only if we have at least 2 docs with names)
        name_errors = self._check_name_consistency(documents, member_id)
        errors.extend(name_errors)

        passed = len(errors) == 0
        if passed:
            self.trace.passed(
                AGENT_NAME,
                "document_gate_overall",
                "All document checks passed.",
            )

        return DocumentGateResult(passed=passed, errors=errors)

    def _check_type_completeness(
        self,
        documents: list[DocumentInput],
        claim_category: ClaimCategory,
    ) -> list[DocumentError]:
        errors: list[DocumentError] = []
        required = self.policy.get_required_documents(claim_category.value)
        uploaded_types = [d.actual_type for d in documents]
        uploaded_counts = Counter(uploaded_types)

        missing = []
        for req_type in required:
            if req_type not in uploaded_types:
                missing.append(req_type)

        if missing:
            # Build a specific error message
            uploaded_summary = ", ".join(
                f"{count} {dtype}" for dtype, count in uploaded_counts.items()
            )
            missing_list = ", ".join(missing)

            message = (
                f"You uploaded {uploaded_summary}, but the following required "
                f"document(s) are missing for a {claim_category.value} claim: "
                f"{missing_list}. Please upload the missing document(s) to proceed."
            )

            errors.append(
                DocumentError(
                    error_type=DocumentErrorType.MISSING_REQUIRED,
                    message=message,
                )
            )
            self.trace.failed(
                AGENT_NAME,
                "type_completeness",
                f"Missing required documents: {missing_list}. "
                f"Uploaded: {uploaded_summary}.",
            )
        else:
            self.trace.passed(
                AGENT_NAME,
                "type_completeness",
                f"All required documents present: {', '.join(required)}.",
            )

        return errors

    def _check_quality(
        self,
        documents: list[DocumentInput],
    ) -> list[DocumentError]:
        errors: list[DocumentError] = []
        all_readable = True

        for doc in documents:
            if doc.quality and doc.quality.upper() == "UNREADABLE":
                all_readable = False
                doc_name = doc.file_name or doc.file_id
                doc_type = doc.actual_type.replace("_", " ").lower()

                message = (
                    f"The {doc_type} ({doc_name}) is not readable. "
                    f"Please re-upload a clearer photo or scan of this document."
                )

                errors.append(
                    DocumentError(
                        document_id=doc.file_id,
                        error_type=DocumentErrorType.UNREADABLE,
                        message=message,
                    )
                )
                self.trace.failed(
                    AGENT_NAME,
                    "quality_check",
                    f"Document {doc_name} ({doc.actual_type}) is unreadable.",
                    confidence_impact=-0.15,
                )

        if all_readable:
            self.trace.passed(
                AGENT_NAME,
                "quality_check",
                "All documents are readable.",
            )

        return errors

    def _check_name_consistency(
        self,
        documents: list[DocumentInput],
        member_id: str,
    ) -> list[DocumentError]:
        errors: list[DocumentError] = []

        # Collect patient names from documents
        names_by_doc: dict[str, str] = {}
        for doc in documents:
            name = None
            if doc.patient_name_on_doc:
                name = doc.patient_name_on_doc
            elif doc.content and "patient_name" in doc.content:
                name = doc.content["patient_name"]
            if name:
                doc_label = doc.file_name or doc.file_id
                names_by_doc[doc_label] = name

        if len(names_by_doc) < 2:
            self.trace.passed(
                AGENT_NAME,
                "name_consistency",
                "Not enough documents with patient names to cross-check "
                "(or all names come from a single document).",
            )
            return errors

        unique_names = set(names_by_doc.values())
        if len(unique_names) > 1:
            # Build specific message listing each doc and its name
            parts = [
                f"'{doc_label}' shows patient name '{name}'"
                for doc_label, name in names_by_doc.items()
            ]
            details = ", but ".join(parts)

            message = (
                f"The uploaded documents appear to belong to different patients. "
                f"{details}. All documents must belong to the same patient. "
                f"Please re-upload correct documents."
            )

            errors.append(
                DocumentError(
                    error_type=DocumentErrorType.NAME_MISMATCH,
                    message=message,
                )
            )
            self.trace.failed(
                AGENT_NAME,
                "name_consistency",
                f"Patient name mismatch across documents: "
                f"{', '.join(f'{k}={v}' for k, v in names_by_doc.items())}.",
            )
        else:
            name = list(unique_names)[0]
            self.trace.passed(
                AGENT_NAME,
                "name_consistency",
                f"Patient name '{name}' consistent across all documents.",
            )

        return errors
