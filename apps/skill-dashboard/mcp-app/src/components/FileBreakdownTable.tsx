import type { FileTokenEntry } from "../types.js";

interface Props {
  files: FileTokenEntry[];
  totalTokens: number;
  budget: { warn: number; critical: number };
}

export function FileBreakdownTable({ files, totalTokens, budget }: Props) {
  let statusClass = "budget-ok";
  if (totalTokens >= budget.critical) statusClass = "budget-critical";
  else if (totalTokens >= budget.warn) statusClass = "budget-warn";

  return (
    <table className="file-table">
      <thead>
        <tr>
          <th style={{ textAlign: "left" }}>File</th>
          <th style={{ textAlign: "right", width: 60 }}>Tokens</th>
          <th style={{ width: 80 }}>%</th>
        </tr>
      </thead>
      <tbody>
        {files.map((f) => (
          <tr key={f.path}>
            <td className="file-path">{f.path}</td>
            <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
              {f.tokens.toLocaleString()}
            </td>
            <td>
              <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <div style={{ flex: 1, height: 4, background: "var(--color-background-secondary, rgba(128,128,128,0.15))", borderRadius: 2 }}>
                  <div
                    className="file-pct-bar"
                    style={{ width: `${f.pctOfTotal}%` }}
                  />
                </div>
                <span style={{ fontSize: 10, minWidth: 28, textAlign: "right", color: "var(--color-text-secondary, #888)" }}>
                  {f.pctOfTotal}%
                </span>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr style={{ borderTop: "1px solid var(--color-border, rgba(128,128,128,0.2))" }}>
          <td style={{ fontWeight: 600 }}>Total</td>
          <td style={{ textAlign: "right", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
            {totalTokens.toLocaleString()}
          </td>
          <td>
            <span className={`budget-label ${statusClass === "budget-ok" ? "" : "budget-label-over"}`} style={{ fontSize: 11 }}>
              {statusClass === "budget-ok"
                ? "ok"
                : statusClass === "budget-warn"
                  ? "warn"
                  : "critical"}
            </span>
          </td>
        </tr>
      </tfoot>
    </table>
  );
}
