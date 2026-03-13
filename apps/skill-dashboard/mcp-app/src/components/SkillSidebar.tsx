import type { QualityMeta, SkillMeasureContent } from "../types.js";
import { FileBreakdownTable } from "./FileBreakdownTable.js";
import { TokenBudgetBar } from "./TokenBudgetBar.js";

interface Props {
  skillName: string;
  measureResult: SkillMeasureContent | null;
  loading: boolean;
  verifying: boolean;
  verifiedDate: string | null;
  meta: QualityMeta;
  onClose: () => void;
  onVerify: () => void;
}

export function SkillSidebar({
  skillName,
  measureResult,
  loading,
  verifying,
  verifiedDate,
  meta,
  onClose,
  onVerify,
}: Props) {
  return (
    <div className="dashboard-sidebar">
      <div className="sidebar-header">
        <h3 style={{ margin: 0, fontSize: 14 }}>{skillName}</h3>
        <button className="sidebar-close" onClick={onClose} title="Close">
          x
        </button>
      </div>

      {loading && (
        <div style={{ color: "var(--color-text-secondary, #888)", fontSize: 13 }}>
          Loading file breakdown...
        </div>
      )}

      {!loading && measureResult && (
        <>
          <div style={{ fontSize: 11, color: "var(--color-text-secondary, #888)" }}>
            {measureResult.skillDir}
          </div>

          <FileBreakdownTable
            files={measureResult.files}
            totalTokens={measureResult.totalTokens}
            budget={measureResult.budget}
          />

          <div style={{ marginTop: 4 }}>
            <TokenBudgetBar
              detail={measureResult.totalTokens.toLocaleString()}
              passed={measureResult.totalTokens < meta.budgetWarn}
              budgetWarn={meta.budgetWarn}
              budgetCritical={meta.budgetCritical}
            />
          </div>
        </>
      )}

      <div style={{ marginTop: 8 }}>
        {verifiedDate ? (
          <span className="verify-confirmed">
            Verified: last_verified set to {verifiedDate}
          </span>
        ) : (
          <button
            className="verify-btn"
            onClick={onVerify}
            disabled={verifying}
          >
            {verifying ? "Verifying..." : "Mark Verified"}
          </button>
        )}
      </div>
    </div>
  );
}
