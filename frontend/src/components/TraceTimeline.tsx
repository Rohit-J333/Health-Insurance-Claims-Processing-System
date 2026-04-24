import { CheckCircle, XCircle, AlertTriangle, SkipForward } from "lucide-react";
import type { TraceStep } from "../types";

interface Props {
  steps: TraceStep[];
  confidence: number;
}

const statusConfig = {
  PASSED: { icon: CheckCircle, color: "text-green-600", bg: "bg-green-50", border: "border-green-200" },
  FAILED: { icon: XCircle, color: "text-red-600", bg: "bg-red-50", border: "border-red-200" },
  ERROR: { icon: AlertTriangle, color: "text-orange-600", bg: "bg-orange-50", border: "border-orange-200" },
  SKIPPED: { icon: SkipForward, color: "text-gray-400", bg: "bg-gray-50", border: "border-gray-200" },
};

export default function TraceTimeline({ steps, confidence }: Props) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Decision Trace</h3>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Confidence:</span>
          <span className={`text-sm font-bold ${confidence > 0.8 ? "text-green-600" : confidence > 0.6 ? "text-yellow-600" : "text-red-600"}`}>
            {(confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />

        {steps.map((step, i) => {
          const config = statusConfig[step.status];
          const Icon = config.icon;

          return (
            <div key={i} className="relative flex items-start gap-3 pb-3">
              <div className={`relative z-10 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${config.bg} border ${config.border}`}>
                <Icon className={`w-4 h-4 ${config.color}`} />
              </div>
              <div className={`flex-1 rounded-lg p-3 border ${config.border} ${config.bg}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-gray-500 bg-white/60 px-1.5 py-0.5 rounded">
                    {step.agent}
                  </span>
                  <span className="text-xs font-medium text-gray-700">
                    {step.check_name.replace(/_/g, " ")}
                  </span>
                  <span className={`text-xs font-bold ${config.color}`}>
                    {step.status}
                  </span>
                  {step.confidence_impact !== 0 && (
                    <span className="text-xs text-red-500 font-mono">
                      ({step.confidence_impact > 0 ? "+" : ""}{step.confidence_impact.toFixed(2)})
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600">{step.details}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
