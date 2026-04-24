"""Extraction Agent — extracts structured data from medical documents.

Dual-path design:
- If document has `content` (test cases), parse it directly.
- If document is a real file, send to LLM vision for extraction.
"""

from __future__ import annotations

from app.models.schemas import (
    DocumentInput,
    ExtractedDocument,
    ExtractedLineItem,
)
from app.services.trace_logger import TraceLogger

AGENT_NAME = "extraction"


class ExtractionAgent:
    def __init__(self, trace: TraceLogger):
        self.trace = trace

    async def process(
        self,
        documents: list[DocumentInput],
    ) -> list[ExtractedDocument]:
        extracted: list[ExtractedDocument] = []

        for doc in documents:
            try:
                if doc.content:
                    result = self._extract_from_content(doc)
                else:
                    result = await self._extract_from_file(doc)

                extracted.append(result)
                self.trace.passed(
                    AGENT_NAME,
                    f"extract_{doc.actual_type.lower()}",
                    f"Extracted data from {doc.actual_type}: "
                    f"patient={result.patient_name}, "
                    f"total={result.total_amount}, "
                    f"{len(result.line_items)} line items.",
                )
            except Exception as e:
                self.trace.error(
                    AGENT_NAME,
                    f"extract_{doc.actual_type.lower()}",
                    f"Failed to extract {doc.actual_type} ({doc.file_id}): {e}",
                    confidence_impact=-0.10,
                )
                # Return a minimal extracted doc so pipeline can continue
                extracted.append(
                    ExtractedDocument(
                        file_id=doc.file_id,
                        document_type=doc.actual_type,
                        confidence=0.3,
                    )
                )

        return extracted

    def _extract_from_content(self, doc: DocumentInput) -> ExtractedDocument:
        """Parse structured content from test case data."""
        content = doc.content or {}

        line_items = [
            ExtractedLineItem(description=item["description"], amount=item["amount"])
            for item in content.get("line_items", [])
        ]

        return ExtractedDocument(
            file_id=doc.file_id,
            document_type=doc.actual_type,
            patient_name=content.get("patient_name"),
            doctor_name=content.get("doctor_name"),
            doctor_registration=content.get("doctor_registration"),
            hospital_name=content.get("hospital_name"),
            diagnosis=content.get("diagnosis"),
            treatment=content.get("treatment"),
            medicines=content.get("medicines", []),
            tests_ordered=content.get("tests_ordered", []),
            line_items=line_items,
            total_amount=content.get("total"),
            date=content.get("date"),
            confidence=1.0,
            raw_content=content,
        )

    async def _extract_from_file(self, doc: DocumentInput) -> ExtractedDocument:
        """Extract data from a real document file using LLM vision."""
        from app.services.llm_client import extract_document_data

        file_path = doc.file_name or doc.file_id
        data = await extract_document_data(
            image_path=file_path,
            document_type=doc.actual_type,
        )

        line_items = [
            ExtractedLineItem(description=item["description"], amount=item["amount"])
            for item in data.get("line_items", [])
        ]

        readability = data.get("readability_score", 0.8)
        confidence = min(1.0, readability)

        return ExtractedDocument(
            file_id=doc.file_id,
            document_type=doc.actual_type,
            patient_name=data.get("patient_name"),
            doctor_name=data.get("doctor_name"),
            doctor_registration=data.get("doctor_registration"),
            hospital_name=data.get("hospital_name"),
            diagnosis=data.get("diagnosis"),
            treatment=data.get("treatment"),
            medicines=data.get("medicines", []),
            tests_ordered=data.get("tests_ordered", []),
            line_items=line_items,
            total_amount=data.get("total_amount"),
            date=data.get("date"),
            confidence=confidence,
            raw_content=data,
        )
