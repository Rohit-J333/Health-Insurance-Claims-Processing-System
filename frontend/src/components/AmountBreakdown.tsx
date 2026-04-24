import { ArrowDown } from "lucide-react";
import type { AmountBreakdown as AmountBreakdownType } from "../types";

interface Props {
  breakdown: AmountBreakdownType;
}

function fmt(n: number): string {
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export default function AmountBreakdown({ breakdown }: Props) {
  const steps: { label: string; amount: number; note?: string }[] = [];

  steps.push({ label: "Original Amount", amount: breakdown.original_amount });

  if (breakdown.after_exclusions !== null && breakdown.after_exclusions !== breakdown.original_amount) {
    steps.push({
      label: "After Exclusions",
      amount: breakdown.after_exclusions,
      note: `Excluded items removed`,
    });
  }

  if (breakdown.sub_limit_cap !== null) {
    steps.push({
      label: "Sub-limit Cap",
      amount: breakdown.sub_limit_cap,
      note: `Capped at category sub-limit`,
    });
  }

  if (breakdown.network_discount_applied !== null) {
    steps.push({
      label: "After Network Discount",
      amount: breakdown.after_network_discount!,
      note: `${breakdown.network_discount_applied}% network hospital discount`,
    });
  }

  if (breakdown.copay_percent !== null && breakdown.copay_percent > 0) {
    steps.push({
      label: "After Co-pay",
      amount: breakdown.after_copay!,
      note: `${breakdown.copay_percent}% co-pay (${fmt(breakdown.copay_amount!)} deducted)`,
    });
  }

  if (breakdown.annual_limit_cap !== null) {
    steps.push({
      label: "Annual Limit Cap",
      amount: breakdown.annual_limit_cap,
      note: "Capped at remaining annual limit",
    });
  }

  steps.push({ label: "Final Approved", amount: breakdown.final_approved });

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-3">Amount Breakdown</h3>
      <div className="space-y-2">
        {steps.map((step, i) => (
          <div key={i}>
            {i > 0 && (
              <div className="flex justify-center py-1">
                <ArrowDown className="w-4 h-4 text-gray-300" />
              </div>
            )}
            <div className={`flex items-center justify-between p-2 rounded ${i === steps.length - 1 ? "bg-green-50 border border-green-200" : "bg-gray-50"}`}>
              <div>
                <span className={`text-sm font-medium ${i === steps.length - 1 ? "text-green-800" : "text-gray-700"}`}>
                  {step.label}
                </span>
                {step.note && (
                  <p className="text-xs text-gray-500">{step.note}</p>
                )}
              </div>
              <span className={`text-sm font-bold font-mono ${i === steps.length - 1 ? "text-green-700" : "text-gray-900"}`}>
                {fmt(step.amount)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
