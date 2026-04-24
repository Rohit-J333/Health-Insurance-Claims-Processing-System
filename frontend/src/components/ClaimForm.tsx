import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { submitClaim } from "../api";
import type { ClaimDecision, ClaimSubmission, DocumentInput } from "../types";
import { CLAIM_CATEGORIES, DOCUMENT_TYPES } from "../types";

const DOC_REQUIREMENTS: Record<string, { required: string[]; optional: string[] }> = {
  CONSULTATION: { required: ["PRESCRIPTION", "HOSPITAL_BILL"], optional: ["LAB_REPORT", "DIAGNOSTIC_REPORT"] },
  DIAGNOSTIC: { required: ["PRESCRIPTION", "LAB_REPORT", "HOSPITAL_BILL"], optional: ["DISCHARGE_SUMMARY"] },
  PHARMACY: { required: ["PRESCRIPTION", "PHARMACY_BILL"], optional: [] },
  DENTAL: { required: ["HOSPITAL_BILL"], optional: ["PRESCRIPTION", "DENTAL_REPORT"] },
  VISION: { required: ["PRESCRIPTION", "HOSPITAL_BILL"], optional: [] },
  ALTERNATIVE_MEDICINE: { required: ["PRESCRIPTION", "HOSPITAL_BILL"], optional: [] },
};

interface Props {
  onResult?: (decision: ClaimDecision) => void;
}

export default function ClaimForm({ onResult }: Props) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [memberId, setMemberId] = useState("EMP001");
  const [category, setCategory] = useState<string>("CONSULTATION");
  const [treatmentDate, setTreatmentDate] = useState("2024-11-01");
  const [claimedAmount, setClaimedAmount] = useState(1500);
  const [hospitalName, setHospitalName] = useState("");
  const [ytdAmount, setYtdAmount] = useState(0);
  const [simulateFailure, setSimulateFailure] = useState(false);

  const [documents, setDocuments] = useState<DocumentInput[]>([
    { file_id: "F001", file_name: "prescription.jpg", actual_type: "PRESCRIPTION" },
    { file_id: "F002", file_name: "hospital_bill.jpg", actual_type: "HOSPITAL_BILL" },
  ]);

  const reqs = DOC_REQUIREMENTS[category];

  function addDocument() {
    setDocuments((prev) => [
      ...prev,
      {
        file_id: `F${String(prev.length + 1).padStart(3, "0")}`,
        file_name: "",
        actual_type: "PRESCRIPTION",
      },
    ]);
  }

  function removeDocument(index: number) {
    setDocuments((prev) => prev.filter((_, i) => i !== index));
  }

  function updateDocument(index: number, field: string, value: string) {
    setDocuments((prev) =>
      prev.map((doc, i) =>
        i === index ? { ...doc, [field]: value } : doc
      )
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const submission: ClaimSubmission = {
      member_id: memberId,
      policy_id: "PLUM_GHI_2024",
      claim_category: category,
      treatment_date: treatmentDate,
      claimed_amount: claimedAmount,
      hospital_name: hospitalName || undefined,
      ytd_claims_amount: ytdAmount,
      documents,
      simulate_component_failure: simulateFailure,
    };

    try {
      const decision = await submitClaim(submission);
      onResult?.(decision);
      navigate(`/claims/${decision.claim_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Submission failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
          {error}
        </div>
      )}

      {/* Member & Category */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Member ID</label>
          <input
            type="text"
            value={memberId}
            onChange={(e) => setMemberId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Claim Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {CLAIM_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat.replace("_", " ")}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Amount & Date */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Claimed Amount (INR)</label>
          <input
            type="number"
            value={claimedAmount}
            onChange={(e) => setClaimedAmount(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
            min={0}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Treatment Date</label>
          <input
            type="date"
            value={treatmentDate}
            onChange={(e) => setTreatmentDate(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">YTD Claims Amount</label>
          <input
            type="number"
            value={ytdAmount}
            onChange={(e) => setYtdAmount(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            min={0}
          />
        </div>
      </div>

      {/* Hospital */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Hospital Name (optional)</label>
        <input
          type="text"
          value={hospitalName}
          onChange={(e) => setHospitalName(e.target.value)}
          placeholder="e.g., Apollo Hospitals"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Document Requirements Info */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
        <span className="font-medium text-blue-800">Required for {category}: </span>
        <span className="text-blue-700">{reqs.required.join(", ")}</span>
        {reqs.optional.length > 0 && (
          <>
            <span className="text-blue-600"> | Optional: </span>
            <span className="text-blue-500">{reqs.optional.join(", ")}</span>
          </>
        )}
      </div>

      {/* Documents */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">Documents</label>
          <button
            type="button"
            onClick={addDocument}
            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
          >
            <Plus className="w-4 h-4" /> Add Document
          </button>
        </div>
        <div className="space-y-2">
          {documents.map((doc, i) => (
            <div key={i} className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg border">
              <input
                type="text"
                value={doc.file_name || ""}
                onChange={(e) => updateDocument(i, "file_name", e.target.value)}
                placeholder="File name"
                className="flex-1 px-2 py-1 text-sm border rounded"
              />
              <select
                value={doc.actual_type}
                onChange={(e) => updateDocument(i, "actual_type", e.target.value)}
                className="px-2 py-1 text-sm border rounded"
              >
                {DOCUMENT_TYPES.map((t) => (
                  <option key={t} value={t}>{t.replace("_", " ")}</option>
                ))}
              </select>
              <select
                value={doc.quality || "GOOD"}
                onChange={(e) => updateDocument(i, "quality", e.target.value)}
                className="px-2 py-1 text-sm border rounded"
              >
                <option value="GOOD">Good Quality</option>
                <option value="UNREADABLE">Unreadable</option>
              </select>
              <button
                type="button"
                onClick={() => removeDocument(i)}
                className="p-1 text-red-400 hover:text-red-600"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Simulate Failure */}
      <label className="flex items-center gap-2 text-sm text-gray-600">
        <input
          type="checkbox"
          checked={simulateFailure}
          onChange={(e) => setSimulateFailure(e.target.checked)}
          className="rounded border-gray-300"
        />
        Simulate component failure (for testing graceful degradation)
      </label>

      {/* Submit */}
      <button
        type="submit"
        disabled={loading}
        className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" /> Processing Claim...
          </>
        ) : (
          "Submit Claim"
        )}
      </button>
    </form>
  );
}
