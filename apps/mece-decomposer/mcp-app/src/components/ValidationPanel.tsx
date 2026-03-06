import type { ValidationContent } from "../types.js";

interface ValidationPanelProps {
  report: ValidationContent["report"];
  onIssueClick?: (location: string) => void;
}

export function ValidationPanel({ report, onIssueClick }: ValidationPanelProps) {
  // Compute scores from the summary if available in the report
  // The report from validate_mece.py has a different shape than Decomposition.validation_summary
  const issues = report.issues || [];
  const sortedIssues = [...issues].sort((a, b) => {
    const order = { error: 0, warning: 1, info: 2 };
    return (order[a.severity] ?? 3) - (order[b.severity] ?? 3);
  });

  return (
    <div className="validation-panel">
      <div className="section-header">Validation</div>

      <div
        style={{
          padding: "8px 12px",
          borderRadius: "4px",
          background: report.valid
            ? "rgba(52, 168, 83, 0.1)"
            : "rgba(234, 67, 53, 0.1)",
          fontWeight: 600,
          fontSize: "13px",
          color: report.valid ? "#34a853" : "#ea4335",
        }}
      >
        {report.valid ? "PASS" : "FAIL"} -- {report.summary.errors} errors,{" "}
        {report.summary.warnings} warnings, {report.summary.info} info
      </div>

      <div style={{ fontSize: "12px", color: "var(--color-text-secondary, #888)" }}>
        {report.summary.total_nodes} nodes ({report.summary.total_atoms} atoms,{" "}
        {report.summary.total_branches} branches) | max depth:{" "}
        {report.summary.max_depth} | max fan-out: {report.summary.max_fan_out}
      </div>

      {sortedIssues.length > 0 && (
        <>
          <div className="section-header" style={{ marginTop: "8px" }}>
            Issues ({sortedIssues.length})
          </div>
          <div className="issues-list">
            {sortedIssues.map((issue, i) => (
              <div
                key={i}
                className="issue-item"
                onClick={() => onIssueClick?.(issue.location)}
              >
                <span className={`issue-severity ${issue.severity}`}>
                  {issue.severity}
                </span>
                <div>
                  <div style={{ fontWeight: 500 }}>{issue.location}</div>
                  <div style={{ color: "var(--color-text-secondary, #888)" }}>
                    {issue.message}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
