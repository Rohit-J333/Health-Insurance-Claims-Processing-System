import axios from "axios";
import type { ClaimDecision, ClaimSubmission, ClaimSummary } from "./types";

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/+$/, "")}/api`
  : "/api";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

export async function uploadDocument(file: File): Promise<{ file_id: string; file_path: string }> {
  const formData = new FormData();
  formData.append("file", file);
  // Use raw axios so browser sets Content-Type with multipart boundary
  const { data } = await axios.post<{ file_id: string; file_path: string }>(
    `${API_BASE}/claims/upload`,
    formData,
  );
  return data;
}

export async function submitClaim(
  submission: ClaimSubmission
): Promise<ClaimDecision> {
  const { data } = await api.post<ClaimDecision>("/claims/submit", submission);
  return data;
}

export async function listClaims(): Promise<ClaimSummary[]> {
  const { data } = await api.get<ClaimSummary[]>("/claims");
  return data;
}

export async function getClaim(claimId: string): Promise<ClaimDecision> {
  const { data } = await api.get<ClaimDecision>(`/claims/${claimId}`);
  return data;
}

export async function getPolicy(): Promise<Record<string, unknown>> {
  const { data } = await api.get("/policy");
  return data;
}

export async function runAllTests(): Promise<{
  summary: string;
  results: Array<{
    case_id: string;
    case_name: string;
    passed: boolean;
    checks?: Array<{ check: string; passed: boolean; expected?: unknown; actual?: unknown }>;
    decision?: ClaimDecision;
    error?: string;
  }>;
}> {
  const { data } = await api.post("/test/run-all");
  return data;
}
