# Eval Report

**Result: 12/12 test cases passed**

| Case | Name | Status | Decision | Approved | Confidence |
|------|------|--------|----------|----------|------------|
| TC001 | Wrong Document Uploaded | PASS | None | None | 1.00 |
| TC002 | Unreadable Document | PASS | None | None | 0.85 |
| TC003 | Documents Belong to Different Patients | PASS | None | None | 1.00 |
| TC004 | Clean Consultation â€” Full Approval | PASS | APPROVED | 1350.0 | 1.00 |
| TC005 | Waiting Period â€” Diabetes | PASS | REJECTED | None | 1.00 |
| TC006 | Dental Partial Approval â€” Cosmetic Exclusion | PASS | PARTIAL | 8000.0 | 1.00 |
| TC007 | MRI Without Pre-Authorization | PASS | REJECTED | None | 1.00 |
| TC008 | Per-Claim Limit Exceeded | PASS | REJECTED | None | 1.00 |
| TC009 | Fraud Signal â€” Multiple Same-Day Claims | PASS | MANUAL_REVIEW | None | 1.00 |
| TC010 | Network Hospital â€” Discount Applied | PASS | APPROVED | 3240.0 | 1.00 |
| TC011 | Component Failure â€” Graceful Degradation | PASS | APPROVED | 4000.0 | 0.80 |
| TC012 | Excluded Treatment | PASS | REJECTED | None | 1.00 |

## Detailed Results

### TC001: Wrong Document Uploaded — PASS

- **Decision:** None
- **Approved Amount:** None
- **Confidence:** 1.00
- **Notes:**
  - Claim processing stopped due to document issues. Please resolve the errors and resubmit.

**Document Errors:**

- `DocumentErrorType.MISSING_REQUIRED`: You uploaded 2 PRESCRIPTION, but the following required document(s) are missing for a CONSULTATION claim: HOSPITAL_BILL. Please upload the missing document(s) to proceed.

**Checks:**

  - [+] `stopped_early`: expected=`True`, actual=`True`

**Trace (4 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP001, category=CONSULTATION, amount=₹1,500. |
| document_gate | type_completeness | TraceStatus.FAILED | — | Missing required documents: HOSPITAL_BILL. Uploaded: 2 PRESCRIPTION. |
| document_gate | quality_check | TraceStatus.PASSED | — | All documents are readable. |
| document_gate | name_consistency | TraceStatus.PASSED | — | Not enough documents with patient names to cross-check (or all names come from a single document). |

---

### TC002: Unreadable Document — PASS

- **Decision:** None
- **Approved Amount:** None
- **Confidence:** 0.85
- **Notes:**
  - Claim processing stopped due to document issues. Please resolve the errors and resubmit.

**Document Errors:**

- `DocumentErrorType.UNREADABLE`: The pharmacy bill (blurry_bill.jpg) is not readable. Please re-upload a clearer photo or scan of this document.

**Checks:**

  - [+] `stopped_early`: expected=`True`, actual=`True`

**Trace (4 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP004, category=PHARMACY, amount=₹800. |
| document_gate | type_completeness | TraceStatus.PASSED | — | All required documents present: PRESCRIPTION, PHARMACY_BILL. |
| document_gate | quality_check | TraceStatus.FAILED | -0.15 | Document blurry_bill.jpg (PHARMACY_BILL) is unreadable. |
| document_gate | name_consistency | TraceStatus.PASSED | — | Not enough documents with patient names to cross-check (or all names come from a single document). |

---

### TC003: Documents Belong to Different Patients — PASS

- **Decision:** None
- **Approved Amount:** None
- **Confidence:** 1.00
- **Notes:**
  - Claim processing stopped due to document issues. Please resolve the errors and resubmit.

**Document Errors:**

- `DocumentErrorType.NAME_MISMATCH`: The uploaded documents appear to belong to different patients. 'prescription_rajesh.jpg' shows patient name 'Rajesh Kumar', but 'bill_arjun.jpg' shows patient name 'Arjun Mehta'. All documents must belong to the same patient. Please re-upload correct documents.

**Checks:**

  - [+] `stopped_early`: expected=`True`, actual=`True`

**Trace (4 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP001, category=CONSULTATION, amount=₹1,500. |
| document_gate | type_completeness | TraceStatus.PASSED | — | All required documents present: PRESCRIPTION, HOSPITAL_BILL. |
| document_gate | quality_check | TraceStatus.PASSED | — | All documents are readable. |
| document_gate | name_consistency | TraceStatus.FAILED | — | Patient name mismatch across documents: prescription_rajesh.jpg=Rajesh Kumar, bill_arjun.jpg=Arjun Mehta. |

---

### TC004: Clean Consultation â€” Full Approval — PASS

- **Decision:** APPROVED
- **Approved Amount:** 1350.0
- **Confidence:** 1.00

**Amount Breakdown:**

| Step | Value |
|------|-------|
| Original claimed | ₹1,500 |
| After exclusions | ₹1,500 |
| Copay (1000%) | ₹1,350 |
| **Final approved** | **₹1,350** |

**Checks:**

  - [+] `decision`: expected=`APPROVED`, actual=`APPROVED`
  - [+] `approved_amount`: expected=`1350`, actual=`1350.0`

**Trace (18 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP001, category=CONSULTATION, amount=₹1,500. |
| document_gate | type_completeness | TraceStatus.PASSED | — | All required documents present: PRESCRIPTION, HOSPITAL_BILL. |
| document_gate | quality_check | TraceStatus.PASSED | — | All documents are readable. |
| document_gate | name_consistency | TraceStatus.PASSED | — | Patient name 'Rajesh Kumar' consistent across all documents. |
| document_gate | document_gate_overall | TraceStatus.PASSED | — | All document checks passed. |
| extraction | extract_prescription | TraceStatus.PASSED | — | Extracted data from PRESCRIPTION: patient=Rajesh Kumar, total=None, 0 line items. |
| extraction | extract_hospital_bill | TraceStatus.PASSED | — | Extracted data from HOSPITAL_BILL: patient=Rajesh Kumar, total=1500.0, 3 line items. |
| adjudication | exclusion_check | TraceStatus.PASSED | — | Diagnosis 'Viral Fever' is not an excluded condition. |
| adjudication | waiting_period | TraceStatus.PASSED | — | Member joined 2024-04-01, treatment 2024-11-01 (214 days). No applicable waiting period. |
| adjudication | pre_auth_check | TraceStatus.PASSED | — | Pre-authorization not required for CONSULTATION. |
| adjudication | per_claim_limit | TraceStatus.PASSED | — | Amount ₹1,500 within effective limit of ₹5,000 (per-claim: ₹5,000, sub-limit: ₹2,000). |
| adjudication | annual_opd_limit | TraceStatus.PASSED | — | YTD ₹5,000 + ₹1,500 = ₹6,500, within annual limit ₹50,000. |
| fraud_detection | same_day_claims | TraceStatus.PASSED | — | 0 prior claims on 2024-11-01, within limit of 2. |
| fraud_detection | monthly_claims | TraceStatus.PASSED | — | 0 claims in 2024-11, within limit of 6. |
| fraud_detection | high_value_check | TraceStatus.PASSED | — | Amount ₹1,500 within threshold ₹25,000. |
| adjudication | network_discount | TraceStatus.PASSED | — | No network discount applied (not a network hospital). |
| adjudication | copay | TraceStatus.PASSED | — | 10.0% co-pay applied: ₹1,500 → ₹1,350 (₹150 deducted). |
| adjudication | final_decision | TraceStatus.PASSED | — | APPROVED for ₹1,350. |

---

### TC005: Waiting Period â€” Diabetes — PASS

- **Decision:** REJECTED
- **Approved Amount:** None
- **Confidence:** 1.00
- **Rejection Reasons:** WAITING_PERIOD
- **Notes:**
  - Member joined on 2024-09-01. Treatment for 'Type 2 Diabetes Mellitus' on 2024-10-15 is only 44 days after joining. The waiting period for this condition is 90 days. The member will be eligible from 2024-11-30.

**Checks:**

  - [+] `decision`: expected=`REJECTED`, actual=`REJECTED`
  - [+] `reason:WAITING_PERIOD`: expected=`True`, actual=`True`

**Trace (9 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP005, category=CONSULTATION, amount=₹3,000. |
| document_gate | type_completeness | TraceStatus.PASSED | — | All required documents present: PRESCRIPTION, HOSPITAL_BILL. |
| document_gate | quality_check | TraceStatus.PASSED | — | All documents are readable. |
| document_gate | name_consistency | TraceStatus.PASSED | — | Patient name 'Vikram Joshi' consistent across all documents. |
| document_gate | document_gate_overall | TraceStatus.PASSED | — | All document checks passed. |
| extraction | extract_prescription | TraceStatus.PASSED | — | Extracted data from PRESCRIPTION: patient=Vikram Joshi, total=None, 0 line items. |
| extraction | extract_hospital_bill | TraceStatus.PASSED | — | Extracted data from HOSPITAL_BILL: patient=Vikram Joshi, total=3000.0, 0 line items. |
| adjudication | exclusion_check | TraceStatus.PASSED | — | Diagnosis 'Type 2 Diabetes Mellitus' is not an excluded condition. |
| adjudication | waiting_period | TraceStatus.FAILED | — | Member joined on 2024-09-01. Treatment for 'Type 2 Diabetes Mellitus' on 2024-10-15 is only 44 days after joining. The w |

---

### TC006: Dental Partial Approval â€” Cosmetic Exclusion — PASS

- **Decision:** PARTIAL
- **Approved Amount:** 8000.0
- **Confidence:** 1.00

**Amount Breakdown:**

| Step | Value |
|------|-------|
| Original claimed | ₹8,000 |
| After exclusions | ₹8,000 |
| **Final approved** | **₹8,000** |

**Line Item Decisions:**

| Description | Amount | Status | Reason |
|-------------|--------|--------|--------|
| Root Canal Treatment | ₹8,000 | APPROVED | Covered procedure |
| Teeth Whitening | ₹4,000 | REJECTED | Excluded procedure: Teeth Whitening |

**Checks:**

  - [+] `decision`: expected=`PARTIAL`, actual=`PARTIAL`
  - [+] `approved_amount`: expected=`8000`, actual=`8000.0`

**Trace (18 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP002, category=DENTAL, amount=₹12,000. |
| document_gate | type_completeness | TraceStatus.PASSED | — | All required documents present: HOSPITAL_BILL. |
| document_gate | quality_check | TraceStatus.PASSED | — | All documents are readable. |
| document_gate | name_consistency | TraceStatus.PASSED | — | Not enough documents with patient names to cross-check (or all names come from a single document). |
| document_gate | document_gate_overall | TraceStatus.PASSED | — | All document checks passed. |
| extraction | extract_hospital_bill | TraceStatus.PASSED | — | Extracted data from HOSPITAL_BILL: patient=Priya Singh, total=12000.0, 2 line items. |
| adjudication | exclusion_line_item | TraceStatus.PASSED | — | 'Root Canal Treatment' is a covered dental procedure. |
| adjudication | exclusion_line_item | TraceStatus.FAILED | — | 'Teeth Whitening' is an excluded dental procedure (Teeth Whitening). |
| adjudication | waiting_period | TraceStatus.PASSED | — | Member joined 2024-04-01, treatment 2024-10-15 (197 days). No applicable waiting period. |
| adjudication | pre_auth_check | TraceStatus.PASSED | — | Pre-authorization not required for DENTAL. |
| adjudication | per_claim_limit | TraceStatus.PASSED | — | Amount ₹8,000 within effective limit of ₹10,000 (per-claim: ₹5,000, sub-limit: ₹10,000). |
| adjudication | annual_opd_limit | TraceStatus.PASSED | — | YTD ₹0 + ₹8,000 = ₹8,000, within annual limit ₹50,000. |
| fraud_detection | same_day_claims | TraceStatus.PASSED | — | 0 prior claims on 2024-10-15, within limit of 2. |
| fraud_detection | monthly_claims | TraceStatus.PASSED | — | 0 claims in 2024-10, within limit of 6. |
| fraud_detection | high_value_check | TraceStatus.PASSED | — | Amount ₹12,000 within threshold ₹25,000. |
| adjudication | network_discount | TraceStatus.PASSED | — | No network discount applied (not a network hospital). |
| adjudication | copay | TraceStatus.PASSED | — | No co-pay for this category. |
| adjudication | final_decision | TraceStatus.PASSED | — | PARTIAL for ₹8,000. |

---

### TC007: MRI Without Pre-Authorization — PASS

- **Decision:** REJECTED
- **Approved Amount:** None
- **Confidence:** 1.00
- **Rejection Reasons:** PRE_AUTH_MISSING
- **Notes:**
  - Pre-authorization is required for 'MRI Lumbar Spine' when the amount exceeds ₹10,000 (claimed: ₹15,000). No pre-authorization was provided. Please obtain pre-authorization and resubmit the claim.

**Checks:**

  - [+] `decision`: expected=`REJECTED`, actual=`REJECTED`
  - [+] `reason:PRE_AUTH_MISSING`: expected=`True`, actual=`True`

**Trace (11 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP007, category=DIAGNOSTIC, amount=₹15,000. |
| document_gate | type_completeness | TraceStatus.PASSED | — | All required documents present: PRESCRIPTION, LAB_REPORT, HOSPITAL_BILL. |
| document_gate | quality_check | TraceStatus.PASSED | — | All documents are readable. |
| document_gate | name_consistency | TraceStatus.PASSED | — | Not enough documents with patient names to cross-check (or all names come from a single document). |
| document_gate | document_gate_overall | TraceStatus.PASSED | — | All document checks passed. |
| extraction | extract_prescription | TraceStatus.PASSED | — | Extracted data from PRESCRIPTION: patient=None, total=None, 0 line items. |
| extraction | extract_lab_report | TraceStatus.PASSED | — | Extracted data from LAB_REPORT: patient=None, total=None, 0 line items. |
| extraction | extract_hospital_bill | TraceStatus.PASSED | — | Extracted data from HOSPITAL_BILL: patient=None, total=15000.0, 1 line items. |
| adjudication | exclusion_check | TraceStatus.PASSED | — | Diagnosis 'Suspected Lumbar Disc Herniation' is not an excluded condition. |
| adjudication | waiting_period | TraceStatus.PASSED | — | Member joined 2024-04-01, treatment 2024-11-02 (215 days). No applicable waiting period. |
| adjudication | pre_auth_check | TraceStatus.FAILED | — | Pre-authorization is required for 'MRI Lumbar Spine' when the amount exceeds ₹10,000 (claimed: ₹15,000). No pre-authoriz |

---

### TC008: Per-Claim Limit Exceeded — PASS

- **Decision:** REJECTED
- **Approved Amount:** None
- **Confidence:** 1.00
- **Rejection Reasons:** PER_CLAIM_EXCEEDED
- **Notes:**
  - Amount ₹7,500 exceeds the applicable limit of ₹5,000 (per-claim: ₹5,000, consultation sub-limit: ₹2,000).

**Checks:**

  - [+] `decision`: expected=`REJECTED`, actual=`REJECTED`
  - [+] `reason:PER_CLAIM_EXCEEDED`: expected=`True`, actual=`True`

**Trace (11 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP003, category=CONSULTATION, amount=₹7,500. |
| document_gate | type_completeness | TraceStatus.PASSED | — | All required documents present: PRESCRIPTION, HOSPITAL_BILL. |
| document_gate | quality_check | TraceStatus.PASSED | — | All documents are readable. |
| document_gate | name_consistency | TraceStatus.PASSED | — | Not enough documents with patient names to cross-check (or all names come from a single document). |
| document_gate | document_gate_overall | TraceStatus.PASSED | — | All document checks passed. |
| extraction | extract_prescription | TraceStatus.PASSED | — | Extracted data from PRESCRIPTION: patient=None, total=None, 0 line items. |
| extraction | extract_hospital_bill | TraceStatus.PASSED | — | Extracted data from HOSPITAL_BILL: patient=None, total=7500.0, 2 line items. |
| adjudication | exclusion_check | TraceStatus.PASSED | — | Diagnosis 'Gastroenteritis' is not an excluded condition. |
| adjudication | waiting_period | TraceStatus.PASSED | — | Member joined 2024-04-01, treatment 2024-10-20 (202 days). No applicable waiting period. |
| adjudication | pre_auth_check | TraceStatus.PASSED | — | Pre-authorization not required for CONSULTATION. |
| adjudication | per_claim_limit | TraceStatus.FAILED | — | Amount ₹7,500 exceeds effective limit of ₹5,000. REJECTED. |

---

### TC009: Fraud Signal â€” Multiple Same-Day Claims — PASS

- **Decision:** MANUAL_REVIEW
- **Approved Amount:** None
- **Confidence:** 1.00
- **Notes:**
  - Fraud signals detected. Routing to manual review.
  - Fraud flag: SAME_DAY_CLAIMS_EXCEEDED — Member EMP008 has 3 prior claims on 2024-10-30 (limit: 2). This would be claim #4 on the same day.

**Fraud Signals:**

- `SAME_DAY_CLAIMS_EXCEEDED`: Member EMP008 has 3 prior claims on 2024-10-30 (limit: 2). This would be claim #4 on the same day.

**Checks:**

  - [+] `decision`: expected=`MANUAL_REVIEW`, actual=`MANUAL_REVIEW`

**Trace (15 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP008, category=CONSULTATION, amount=₹4,800. |
| document_gate | type_completeness | TraceStatus.PASSED | — | All required documents present: PRESCRIPTION, HOSPITAL_BILL. |
| document_gate | quality_check | TraceStatus.PASSED | — | All documents are readable. |
| document_gate | name_consistency | TraceStatus.PASSED | — | Not enough documents with patient names to cross-check (or all names come from a single document). |
| document_gate | document_gate_overall | TraceStatus.PASSED | — | All document checks passed. |
| extraction | extract_prescription | TraceStatus.PASSED | — | Extracted data from PRESCRIPTION: patient=None, total=None, 0 line items. |
| extraction | extract_hospital_bill | TraceStatus.PASSED | — | Extracted data from HOSPITAL_BILL: patient=None, total=4800.0, 0 line items. |
| adjudication | exclusion_check | TraceStatus.PASSED | — | Diagnosis 'Migraine' is not an excluded condition. |
| adjudication | waiting_period | TraceStatus.PASSED | — | Member joined 2024-04-01, treatment 2024-10-30 (212 days). No applicable waiting period. |
| adjudication | pre_auth_check | TraceStatus.PASSED | — | Pre-authorization not required for CONSULTATION. |
| adjudication | per_claim_limit | TraceStatus.PASSED | — | Amount ₹4,800 within effective limit of ₹5,000 (per-claim: ₹5,000, sub-limit: ₹2,000). |
| adjudication | annual_opd_limit | TraceStatus.PASSED | — | YTD ₹0 + ₹4,800 = ₹4,800, within annual limit ₹50,000. |
| fraud_detection | same_day_claims | TraceStatus.FAILED | — | 3 prior claims on 2024-10-30, exceeds limit of 2. Flagging for manual review. |
| fraud_detection | monthly_claims | TraceStatus.PASSED | — | 3 claims in 2024-10, within limit of 6. |
| fraud_detection | high_value_check | TraceStatus.PASSED | — | Amount ₹4,800 within threshold ₹25,000. |

---

### TC010: Network Hospital â€” Discount Applied — PASS

- **Decision:** APPROVED
- **Approved Amount:** 3240.0
- **Confidence:** 1.00

**Amount Breakdown:**

| Step | Value |
|------|-------|
| Original claimed | ₹4,500 |
| After exclusions | ₹4,500 |
| Network discount (2000%) | ₹3,600 |
| Copay (1000%) | ₹3,240 |
| **Final approved** | **₹3,240** |

**Checks:**

  - [+] `decision`: expected=`APPROVED`, actual=`APPROVED`
  - [+] `approved_amount`: expected=`3240`, actual=`3240.0`

**Trace (18 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP010, category=CONSULTATION, amount=₹4,500. |
| document_gate | type_completeness | TraceStatus.PASSED | — | All required documents present: PRESCRIPTION, HOSPITAL_BILL. |
| document_gate | quality_check | TraceStatus.PASSED | — | All documents are readable. |
| document_gate | name_consistency | TraceStatus.PASSED | — | Patient name 'Deepak Shah' consistent across all documents. |
| document_gate | document_gate_overall | TraceStatus.PASSED | — | All document checks passed. |
| extraction | extract_prescription | TraceStatus.PASSED | — | Extracted data from PRESCRIPTION: patient=Deepak Shah, total=None, 0 line items. |
| extraction | extract_hospital_bill | TraceStatus.PASSED | — | Extracted data from HOSPITAL_BILL: patient=Deepak Shah, total=4500.0, 2 line items. |
| adjudication | exclusion_check | TraceStatus.PASSED | — | Diagnosis 'Acute Bronchitis' is not an excluded condition. |
| adjudication | waiting_period | TraceStatus.PASSED | — | Member joined 2024-04-01, treatment 2024-11-03 (216 days). No applicable waiting period. |
| adjudication | pre_auth_check | TraceStatus.PASSED | — | Pre-authorization not required for CONSULTATION. |
| adjudication | per_claim_limit | TraceStatus.PASSED | — | Amount ₹4,500 within effective limit of ₹5,000 (per-claim: ₹5,000, sub-limit: ₹2,000). |
| adjudication | annual_opd_limit | TraceStatus.PASSED | — | YTD ₹8,000 + ₹4,500 = ₹12,500, within annual limit ₹50,000. |
| fraud_detection | same_day_claims | TraceStatus.PASSED | — | 0 prior claims on 2024-11-03, within limit of 2. |
| fraud_detection | monthly_claims | TraceStatus.PASSED | — | 0 claims in 2024-11, within limit of 6. |
| fraud_detection | high_value_check | TraceStatus.PASSED | — | Amount ₹4,500 within threshold ₹25,000. |
| adjudication | network_discount | TraceStatus.PASSED | — | Apollo Hospitals is a network hospital. 20.0% discount applied: ₹4,500 → ₹3,600. |
| adjudication | copay | TraceStatus.PASSED | — | 10.0% co-pay applied: ₹3,600 → ₹3,240 (₹360 deducted). |
| adjudication | final_decision | TraceStatus.PASSED | — | APPROVED for ₹3,240. |

---

### TC011: Component Failure â€” Graceful Degradation — PASS

- **Decision:** APPROVED
- **Approved Amount:** 4000.0
- **Confidence:** 0.80
- **Notes:**
  - Extraction component failed. Processing continued with limited data. Manual review is recommended.
  - Manual review recommended due to incomplete processing (one or more components experienced failures).

**Amount Breakdown:**

| Step | Value |
|------|-------|
| Original claimed | ₹4,000 |
| After exclusions | ₹4,000 |
| **Final approved** | **₹4,000** |

**Checks:**

  - [+] `decision`: expected=`APPROVED`, actual=`APPROVED`

**Trace (17 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP006, category=ALTERNATIVE_MEDICINE, amount=₹4,000. |
| document_gate | type_completeness | TraceStatus.PASSED | — | All required documents present: PRESCRIPTION, HOSPITAL_BILL. |
| document_gate | quality_check | TraceStatus.PASSED | — | All documents are readable. |
| document_gate | name_consistency | TraceStatus.PASSED | — | Not enough documents with patient names to cross-check (or all names come from a single document). |
| document_gate | document_gate_overall | TraceStatus.PASSED | — | All document checks passed. |
| orchestrator | extraction_failure | TraceStatus.ERROR | -0.20 | Extraction agent failed: Simulated component failure in Extraction Agent (simulate_component_failure=true). Proceeding w |
| adjudication | exclusion_check | TraceStatus.PASSED | — | Diagnosis 'Chronic Joint Pain' is not an excluded condition. |
| adjudication | waiting_period | TraceStatus.PASSED | — | Member joined 2024-04-01, treatment 2024-10-28 (210 days). No applicable waiting period. |
| adjudication | pre_auth_check | TraceStatus.PASSED | — | Pre-authorization not required for ALTERNATIVE_MEDICINE. |
| adjudication | per_claim_limit | TraceStatus.PASSED | — | Amount ₹4,000 within effective limit of ₹8,000 (per-claim: ₹5,000, sub-limit: ₹8,000). |
| adjudication | annual_opd_limit | TraceStatus.PASSED | — | YTD ₹0 + ₹4,000 = ₹4,000, within annual limit ₹50,000. |
| fraud_detection | same_day_claims | TraceStatus.PASSED | — | 0 prior claims on 2024-10-28, within limit of 2. |
| fraud_detection | monthly_claims | TraceStatus.PASSED | — | 0 claims in 2024-10, within limit of 6. |
| fraud_detection | high_value_check | TraceStatus.PASSED | — | Amount ₹4,000 within threshold ₹25,000. |
| adjudication | network_discount | TraceStatus.PASSED | — | No network discount applied (not a network hospital). |
| adjudication | copay | TraceStatus.PASSED | — | No co-pay for this category. |
| adjudication | final_decision | TraceStatus.PASSED | — | APPROVED for ₹4,000. |

---

### TC012: Excluded Treatment — PASS

- **Decision:** REJECTED
- **Approved Amount:** None
- **Confidence:** 1.00
- **Rejection Reasons:** EXCLUDED_CONDITION
- **Notes:**
  - The diagnosis/treatment 'Morbid Obesity â€” BMI 37' falls under the policy exclusion: 'Obesity and weight loss programs'.

**Checks:**

  - [+] `decision`: expected=`REJECTED`, actual=`REJECTED`
  - [+] `reason:EXCLUDED_CONDITION`: expected=`True`, actual=`True`

**Trace (8 steps):**

| Agent | Check | Status | Confidence Δ | Details |
|-------|-------|--------|--------------|---------|
| orchestrator | claim_received | TraceStatus.PASSED | — | Claim received: member=EMP009, category=CONSULTATION, amount=₹8,000. |
| document_gate | type_completeness | TraceStatus.PASSED | — | All required documents present: PRESCRIPTION, HOSPITAL_BILL. |
| document_gate | quality_check | TraceStatus.PASSED | — | All documents are readable. |
| document_gate | name_consistency | TraceStatus.PASSED | — | Not enough documents with patient names to cross-check (or all names come from a single document). |
| document_gate | document_gate_overall | TraceStatus.PASSED | — | All document checks passed. |
| extraction | extract_prescription | TraceStatus.PASSED | — | Extracted data from PRESCRIPTION: patient=None, total=None, 0 line items. |
| extraction | extract_hospital_bill | TraceStatus.PASSED | — | Extracted data from HOSPITAL_BILL: patient=None, total=8000.0, 2 line items. |
| adjudication | exclusion_check | TraceStatus.FAILED | — | Diagnosis 'Morbid Obesity â€” BMI 37' excluded under: 'Obesity and weight loss programs'. REJECTED. |

---

