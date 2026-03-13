import { useState, useEffect } from "react";
import type { ViewProps } from "./mcp-app-wrapper.js";
import type {
  QualityCheckContent,
  SkillMeasureContent,
  SkillVerifyContent,
} from "./types.js";
import { SummaryBar } from "./components/SummaryBar.js";
import { SkillTable } from "./components/SkillTable.js";
import { PluginTable } from "./components/PluginTable.js";
import { RepoChecks } from "./components/RepoChecks.js";
import { SkillSidebar } from "./components/SkillSidebar.js";

export default function SkillDashboardApp(props: ViewProps) {
  const { toolResult, callServerTool } = props;

  const [data, setData] = useState<QualityCheckContent | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [measureResult, setMeasureResult] =
    useState<SkillMeasureContent | null>(null);
  const [measureLoading, setMeasureLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifiedDate, setVerifiedDate] = useState<string | null>(null);

  // Route tool results by type
  useEffect(() => {
    if (!toolResult || !("structuredContent" in toolResult)) return;
    const sc = (toolResult as Record<string, unknown>).structuredContent;
    if (!sc || typeof sc !== "object") return;

    const content = sc as Record<string, unknown>;
    switch (content.type) {
      case "quality-check":
        setData(sc as QualityCheckContent);
        break;
      case "skill-measure":
        setMeasureResult(sc as SkillMeasureContent);
        setMeasureLoading(false);
        break;
      case "skill-verify": {
        const verify = sc as SkillVerifyContent;
        setVerifiedDate(verify.newDate);
        setVerifying(false);
        // Refresh quality data
        callServerTool({
          name: "skill-quality-check",
          arguments: {},
        });
        break;
      }
    }
  }, [toolResult, callServerTool]);

  const handleSelectSkill = (name: string) => {
    if (name === selectedSkill) {
      // Toggle off
      setSelectedSkill(null);
      setMeasureResult(null);
      setVerifiedDate(null);
      return;
    }
    setSelectedSkill(name);
    setMeasureResult(null);
    setMeasureLoading(true);
    setVerifiedDate(null);
    setVerifying(false);
    callServerTool({
      name: "skill-measure",
      arguments: { skillName: name },
    });
  };

  const handleVerify = () => {
    if (!selectedSkill) return;
    setVerifying(true);
    callServerTool({
      name: "skill-verify",
      arguments: { skillName: selectedSkill },
    });
  };

  const handleCloseSidebar = () => {
    setSelectedSkill(null);
    setMeasureResult(null);
    setVerifiedDate(null);
    setVerifying(false);
  };

  if (!data) {
    return (
      <div className="dashboard-app">
        <div className="dashboard-empty">
          Waiting for quality check results...
        </div>
      </div>
    );
  }

  const hasSidebar = selectedSkill !== null;

  return (
    <div className="dashboard-app">
      <div className="dashboard-header">
        <h2>Skill Dashboard</h2>
        <span className="dashboard-timestamp">{data.meta.generatedAt}</span>
      </div>

      <SummaryBar summary={data.summary} />

      <div className={`dashboard-panels ${hasSidebar ? "has-sidebar" : ""}`}>
        <div className="dashboard-main">
          {data.skills.length > 0 && (
            <section>
              <div className="section-header">
                Skills ({data.skills.length})
              </div>
              <SkillTable
                skills={data.skills}
                meta={data.meta}
                selectedSkill={selectedSkill}
                onSelect={handleSelectSkill}
              />
            </section>
          )}

          {data.plugins.length > 0 && (
            <section>
              <div className="section-header">
                Plugins ({data.plugins.length})
              </div>
              <PluginTable plugins={data.plugins} />
            </section>
          )}

          {data.repo.length > 0 && (
            <section>
              <div className="section-header">Repo Hygiene</div>
              <RepoChecks checks={data.repo} />
            </section>
          )}
        </div>

        {hasSidebar && (
          <SkillSidebar
            skillName={selectedSkill}
            measureResult={measureResult}
            loading={measureLoading}
            verifying={verifying}
            verifiedDate={verifiedDate}
            meta={data.meta}
            onClose={handleCloseSidebar}
            onVerify={handleVerify}
          />
        )}
      </div>
    </div>
  );
}
