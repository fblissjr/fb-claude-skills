/**
 * Map a 0-1 score to a CSS color string.
 *
 * >= 0.85: green
 * 0.70 - 0.84: amber
 * 0.50 - 0.69: red-orange
 * < 0.50: red
 */
export function scoreColor(score: number): string {
  if (score >= 0.85) return "#34a853";
  if (score >= 0.7) return "#f9ab00";
  if (score >= 0.5) return "#e37400";
  return "#ea4335";
}

/**
 * Map a dependency type to a badge color.
 */
export function dependencyColor(
  type: "data" | "sequencing" | "resource" | "approval",
): string {
  switch (type) {
    case "data":
      return "#3b82f6";
    case "sequencing":
      return "#eab308";
    case "resource":
      return "#f97316";
    case "approval":
      return "#ef4444";
  }
}
