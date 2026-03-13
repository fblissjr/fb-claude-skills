interface Props {
  detail: string;
  passed: boolean;
  budgetWarn: number;
  budgetCritical: number;
}

export function TokenBudgetBar({
  detail,
  passed,
  budgetWarn,
  budgetCritical,
}: Props) {
  // Parse token count from detail string (e.g. "1,234" or "5,000 > 4,000")
  const tokenStr = detail.split(" ")[0].replace(/,/g, "");
  const tokens = parseInt(tokenStr, 10) || 0;
  const maxDisplay = budgetCritical * 1.5;
  const pct = Math.min((tokens / maxDisplay) * 100, 100);

  let colorClass = "budget-ok";
  if (tokens >= budgetCritical) colorClass = "budget-critical";
  else if (tokens >= budgetWarn) colorClass = "budget-warn";

  return (
    <div className="budget-bar-container" title={detail}>
      <div className="budget-bar">
        <div
          className={`budget-bar-fill ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`budget-label ${passed ? "" : "budget-label-over"}`}>
        {tokens.toLocaleString()}
      </span>
    </div>
  );
}
