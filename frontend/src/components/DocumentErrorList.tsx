import { AlertCircle, FileWarning, UserX } from "lucide-react";
import type { DocumentError } from "../types";

interface Props {
  errors: DocumentError[];
}

const errorIcons: Record<string, typeof AlertCircle> = {
  MISSING_REQUIRED: FileWarning,
  UNREADABLE: AlertCircle,
  NAME_MISMATCH: UserX,
  WRONG_TYPE: FileWarning,
};

export default function DocumentErrorList({ errors }: Props) {
  if (errors.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-red-800">Document Issues</h3>
      {errors.map((error, i) => {
        const Icon = errorIcons[error.error_type] || AlertCircle;
        return (
          <div
            key={i}
            className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg"
          >
            <Icon className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <span className="text-xs font-mono text-red-600 bg-red-100 px-1.5 py-0.5 rounded">
                {error.error_type}
              </span>
              <p className="text-sm text-red-800 mt-1">{error.message}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
