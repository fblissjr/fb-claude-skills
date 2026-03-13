import type { QualitySummary } from "../types.js";

interface Props {
  summary: QualitySummary;
}

export function SummaryBar({ summary }: Props) {
  const passRate =
    summary.total > 0
      ? Math.round((summary.passed / summary.total) * 100)
      : 0;

  return (
    <div className="summary-bar">
      <div className="summary-badge summary-passed">
        {summary.passed} passed
      </div>
      <div className="summary-badge summary-failed">
        {summary.failed} failed
      </div>
      <div className="summary-badge summary-total">
        {summary.total} total
      </div>
      <div className="summary-rate">{passRate}%</div>
    </div>
  );
}
