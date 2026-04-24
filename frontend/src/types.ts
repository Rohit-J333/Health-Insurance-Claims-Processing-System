export interface TraceStep {
  agent: string;
  check_name: string;
  status: "PASSED" | "FAILED" | "SKIPPED" | "ERROR";
  details: string;
  timestamp: string;
  confidence_impact: number;
}

export interface ClaimTrace {
  claim_id: string;
  steps: TraceStep[];
  overall_confidence: number;
}

export interface LineItemDecision {
  description: string;
  amount: number;
  status: "APPROVED" | "REJECTED";
  reason: string | null;
}

export interface DocumentError {
  document_id: string | null;
  error_type: string;
  message: string;
}

export interface FraudSignal {
  flag: string;
  details: string;
}

export interface AmountBreakdown {
  original_amount: number;
  after_exclusions: number | null;
  network_discount_applied: number | null;
  after_network_discount: number | null;
  copay_percent: number | null;
  copay_amount: number | null;
  after_copay: number | null;
  sub_limit_cap: number | null;
  per_claim_limit_cap: number | null;
  annual_limit_cap: number | null;
  final_approved: number;
}

export interface ClaimDecision {
  claim_id: string;
  decision: "APPROVED" | "PARTIAL" | "REJECTED" | "MANUAL_REVIEW" | null;
  approved_amount: number | null;
  claimed_amount: number;
  rejection_reasons: string[];
  confidence_score: number;
  line_item_decisions: LineItemDecision[];
  amount_breakdown: AmountBreakdown | null;
  document_errors: DocumentError[];
  fraud_signals: FraudSignal[];
  trace: ClaimTrace | null;
  notes: string[];
}

export interface ClaimSummary {
  claim_id: string;
  member_id: string;
  claim_category: string;
  treatment_date: string;
  claimed_amount: number;
  decision: string | null;
  approved_amount: number | null;
  confidence_score: number | null;
  created_at: string;
}

export interface DocumentInput {
  file_id: string;
  file_name?: string;
  actual_type: string;
  quality?: string;
  patient_name_on_doc?: string;
  content?: Record<string, unknown>;
}

export interface ClaimSubmission {
  member_id: string;
  policy_id: string;
  claim_category: string;
  treatment_date: string;
  claimed_amount: number;
  hospital_name?: string;
  ytd_claims_amount?: number;
  claims_history?: Array<{
    claim_id: string;
    date: string;
    amount: number;
    provider?: string;
  }>;
  documents: DocumentInput[];
  simulate_component_failure?: boolean;
}

export const CLAIM_CATEGORIES = [
  "CONSULTATION",
  "DIAGNOSTIC",
  "PHARMACY",
  "DENTAL",
  "VISION",
  "ALTERNATIVE_MEDICINE",
] as const;

export const DOCUMENT_TYPES = [
  "PRESCRIPTION",
  "HOSPITAL_BILL",
  "LAB_REPORT",
  "PHARMACY_BILL",
  "DIAGNOSTIC_REPORT",
  "DENTAL_REPORT",
  "DISCHARGE_SUMMARY",
] as const;
