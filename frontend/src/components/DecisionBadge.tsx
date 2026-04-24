interface Props {
  decision: string | null;
  size?: "sm" | "md" | "lg";
}

const colors: Record<string, string> = {
  APPROVED: "bg-green-100 text-green-800 border-green-300",
  PARTIAL: "bg-yellow-100 text-yellow-800 border-yellow-300",
  REJECTED: "bg-red-100 text-red-800 border-red-300",
  MANUAL_REVIEW: "bg-orange-100 text-orange-800 border-orange-300",
};

const sizeClasses = {
  sm: "text-xs px-2 py-0.5",
  md: "text-sm px-3 py-1",
  lg: "text-base px-4 py-1.5",
};

export default function DecisionBadge({ decision, size = "md" }: Props) {
  if (!decision) {
    return (
      <span className={`inline-flex items-center rounded-full border bg-gray-100 text-gray-600 border-gray-300 font-medium ${sizeClasses[size]}`}>
        PENDING
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center rounded-full border font-medium ${colors[decision] || colors.MANUAL_REVIEW} ${sizeClasses[size]}`}>
      {decision.replace("_", " ")}
    </span>
  );
}
