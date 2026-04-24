import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Loader2, AlertTriangle } from "lucide-react";
import { getClaim } from "../api";
import type { ClaimDecision } from "../types";
import DecisionBadge from "../components/DecisionBadge";
import TraceTimeline from "../components/TraceTimeline";
import AmountBreakdown from "../components/AmountBreakdown";
import DocumentErrorList from "../components/DocumentErrorList";

export default function ClaimDetail() {
  const { id } = useParams<{ id: string }>();
  const [decision, setDecision] = useState<ClaimDecision | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getClaim(id)
      .then(setDecision)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error || !decision) {
    return (
      <div className="text-center py-20">
        <p className="text-red-600">Failed to load claim: {error}</p>
        <Link to="/" className="text-blue-600 text-sm hover:underline mt-2 inline-block">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Dashboard
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Claim {decision.claim_id}
          </h1>
          <p className="text-sm text-gray-500 font-mono mt-1">
            Claimed: ₹{decision.claimed_amount.toLocaleString("en-IN")}
          </p>
        </div>
        <DecisionBadge decision={decision.decision} size="lg" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: Decision + Details */}
        <div className="lg:col-span-1 space-y-4">
          {/* Summary Card */}
          <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
            <h3 className="font-semibold text-gray-900">Decision Summary</h3>

            {decision.approved_amount != null && (
              <div>
                <span className="text-xs text-gray-500">Approved Amount</span>
                <p className="text-xl font-bold text-green-700 font-mono">
                  ₹{decision.approved_amount.toLocaleString("en-IN")}
                </p>
              </div>
            )}

            <div>
              <span className="text-xs text-gray-500">Confidence</span>
              <p className={`text-lg font-bold ${decision.confidence_score > 0.8 ? "text-green-600" : decision.confidence_score > 0.6 ? "text-yellow-600" : "text-red-600"}`}>
                {(decision.confidence_score * 100).toFixed(0)}%
              </p>
            </div>

            {decision.rejection_reasons.length > 0 && (
              <div>
                <span className="text-xs text-gray-500">Rejection Reasons</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {decision.rejection_reasons.map((r, i) => (
                    <span key={i} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded font-mono">
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Notes */}
          {decision.notes.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-900 mb-2">Notes</h3>
              <ul className="space-y-1.5">
                {decision.notes.map((note, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                    <span className="text-gray-400 mt-1">-</span>
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Line Item Decisions */}
          {decision.line_item_decisions.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-900 mb-2">Line Items</h3>
              <div className="space-y-2">
                {decision.line_item_decisions.map((li, i) => (
                  <div
                    key={i}
                    className={`p-2 rounded text-sm border ${
                      li.status === "APPROVED"
                        ? "bg-green-50 border-green-200"
                        : "bg-red-50 border-red-200"
                    }`}
                  >
                    <div className="flex justify-between">
                      <span className="font-medium">{li.description}</span>
                      <span className="font-mono">₹{li.amount.toLocaleString("en-IN")}</span>
                    </div>
                    <div className="flex justify-between mt-0.5">
                      <span className={`text-xs ${li.status === "APPROVED" ? "text-green-600" : "text-red-600"}`}>
                        {li.status}
                      </span>
                      {li.reason && (
                        <span className="text-xs text-gray-500">{li.reason}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Amount Breakdown */}
          {decision.amount_breakdown && (
            <AmountBreakdown breakdown={decision.amount_breakdown} />
          )}

          {/* Fraud Signals */}
          {decision.fraud_signals.length > 0 && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <h3 className="font-semibold text-orange-800 flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4" /> Fraud Signals
              </h3>
              {decision.fraud_signals.map((s, i) => (
                <div key={i} className="text-sm text-orange-700 mb-1">
                  <span className="font-mono text-xs bg-orange-100 px-1 rounded">{s.flag}</span>
                  <p className="mt-0.5">{s.details}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right column: Document Errors + Trace */}
        <div className="lg:col-span-2 space-y-4">
          {/* Document Errors */}
          {decision.document_errors.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <DocumentErrorList errors={decision.document_errors} />
            </div>
          )}

          {/* Trace Timeline */}
          {decision.trace && decision.trace.steps.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <TraceTimeline
                steps={decision.trace.steps}
                confidence={decision.trace.overall_confidence}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
