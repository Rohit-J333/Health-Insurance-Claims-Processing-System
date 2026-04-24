import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import ClaimForm from "../components/ClaimForm";

export default function SubmitClaim() {
  return (
    <div className="max-w-3xl mx-auto">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Dashboard
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-1">Submit a Claim</h1>
      <p className="text-sm text-gray-500 mb-6">
        Fill in the claim details and upload required documents for processing.
      </p>

      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <ClaimForm />
      </div>
    </div>
  );
}
