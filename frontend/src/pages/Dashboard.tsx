import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, Plus, PlayCircle, Loader2 } from "lucide-react";
import { listClaims, runAllTests } from "../api";
import type { ClaimSummary } from "../types";
import DecisionBadge from "../components/DecisionBadge";

export default function Dashboard() {
  const [claims, setClaims] = useState<ClaimSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [testRunning, setTestRunning] = useState(false);
  const [testResult, setTestResult] = useState<{ summary: string; results: Array<{ case_id: string; case_name: string; passed: boolean; decision?: { claim_id: string } }> } | null>(null);

  useEffect(() => {
    listClaims()
      .then(setClaims)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function handleRunTests() {
    setTestRunning(true);
    setTestResult(null);
    try {
      const result = await runAllTests();
      setTestResult(result);
      // Refresh claims list
      const updated = await listClaims();
      setClaims(updated);
    } catch (err) {
      console.error(err);
    } finally {
      setTestRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Claims Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Plum Health Insurance Claims Processing System
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleRunTests}
            disabled={testRunning}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            {testRunning ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <PlayCircle className="w-4 h-4" />
            )}
            Run All Test Cases
          </button>
          <Link
            to="/submit"
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" /> New Claim
          </Link>
        </div>
      </div>

      {/* Test Results */}
      {testResult && (
        <div className="p-4 bg-gray-50 border rounded-lg">
          <h3 className="font-semibold text-gray-900 mb-3">{testResult.summary}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {testResult.results.map((r) => {
              const inner = (
                <>
                  <span className="font-mono">{r.case_id}</span>
                  <span className="ml-1">{r.passed ? "PASS" : "FAIL"}</span>
                  <p className="text-xs opacity-75 truncate">{r.case_name}</p>
                </>
              );
              const cls = `p-2 rounded text-sm ${
                r.passed
                  ? "bg-green-50 border border-green-200 text-green-800"
                  : "bg-red-50 border border-red-200 text-red-800"
              }`;
              return r.decision?.claim_id ? (
                <Link key={r.case_id} to={`/claims/${r.decision.claim_id}`} className={`${cls} hover:opacity-80 block`}>
                  {inner}
                </Link>
              ) : (
                <div key={r.case_id} className={cls}>{inner}</div>
              );
            })}
          </div>
        </div>
      )}

      {/* Claims Table */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      ) : claims.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No claims processed yet.</p>
          <Link to="/submit" className="text-blue-600 text-sm hover:underline mt-1 inline-block">
            Submit your first claim
          </Link>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left">
                <th className="py-3 px-4 text-gray-500 font-medium">Claim ID</th>
                <th className="py-3 px-4 text-gray-500 font-medium">Member</th>
                <th className="py-3 px-4 text-gray-500 font-medium">Category</th>
                <th className="py-3 px-4 text-gray-500 font-medium">Claimed</th>
                <th className="py-3 px-4 text-gray-500 font-medium">Approved</th>
                <th className="py-3 px-4 text-gray-500 font-medium">Decision</th>
                <th className="py-3 px-4 text-gray-500 font-medium">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => (
                <tr key={claim.claim_id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4">
                    <Link
                      to={`/claims/${claim.claim_id}`}
                      className="text-blue-600 hover:underline font-mono text-xs"
                    >
                      {claim.claim_id}
                    </Link>
                  </td>
                  <td className="py-3 px-4 text-gray-900">{claim.member_id}</td>
                  <td className="py-3 px-4 text-gray-600">{claim.claim_category}</td>
                  <td className="py-3 px-4 font-mono">
                    ₹{claim.claimed_amount.toLocaleString("en-IN")}
                  </td>
                  <td className="py-3 px-4 font-mono">
                    {claim.approved_amount != null
                      ? `₹${claim.approved_amount.toLocaleString("en-IN")}`
                      : "—"}
                  </td>
                  <td className="py-3 px-4">
                    <DecisionBadge decision={claim.decision} size="sm" />
                  </td>
                  <td className="py-3 px-4">
                    {claim.confidence_score != null ? (
                      <span className={`font-mono text-xs ${claim.confidence_score > 0.8 ? "text-green-600" : claim.confidence_score > 0.6 ? "text-yellow-600" : "text-red-600"}`}>
                        {(claim.confidence_score * 100).toFixed(0)}%
                      </span>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
