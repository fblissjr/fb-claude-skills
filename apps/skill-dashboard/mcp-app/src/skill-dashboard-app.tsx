import type { ViewProps } from "./mcp-app-wrapper.js";
import type { QualityCheckContent } from "./types.js";
import { SummaryBar } from "./components/SummaryBar.js";
import { SkillTable } from "./components/SkillTable.js";
import { PluginTable } from "./components/PluginTable.js";
import { RepoChecks } from "./components/RepoChecks.js";

export default function SkillDashboardApp(props: ViewProps) {
  const { toolResult } = props;

  // Extract structured content from tool result
  let data: QualityCheckContent | null = null;
  if (toolResult && "structuredContent" in toolResult) {
    const sc = (toolResult as Record<string, unknown>).structuredContent;
    if (sc && typeof sc === "object" && (sc as Record<string, unknown>).type === "quality-check") {
      data = sc as QualityCheckContent;
    }
  }

  if (!data) {
    return (
      <div className="dashboard-app">
        <div className="dashboard-empty">
          Waiting for quality check results...
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-app">
      <div className="dashboard-header">
        <h2>Skill Dashboard</h2>
        <span className="dashboard-timestamp">{data.meta.generatedAt}</span>
      </div>

      <SummaryBar summary={data.summary} />

      {data.skills.length > 0 && (
        <section>
          <div className="section-header">Skills ({data.skills.length})</div>
          <SkillTable skills={data.skills} meta={data.meta} />
        </section>
      )}

      {data.plugins.length > 0 && (
        <section>
          <div className="section-header">Plugins ({data.plugins.length})</div>
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
  );
}
