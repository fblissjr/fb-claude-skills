import type { RepoCheckResult } from "../types.js";
import { StatusDot } from "./StatusDot.js";

interface Props {
  checks: RepoCheckResult[];
}

export function RepoChecks({ checks }: Props) {
  return (
    <div className="repo-checks">
      {checks.map((check) => (
        <div key={check.check} className="repo-check-row">
          <StatusDot passed={check.passed} />
          <span className="repo-check-label">{check.check}</span>
          {check.detail && (
            <span className="repo-check-detail">{check.detail}</span>
          )}
        </div>
      ))}
    </div>
  );
}
