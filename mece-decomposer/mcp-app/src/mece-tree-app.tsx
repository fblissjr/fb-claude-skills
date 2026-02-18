import { useState, useEffect, useCallback } from "react";
import type { ViewProps } from "./mcp-app-wrapper.js";
import type {
  Decomposition,
  Node,
  StructuredContent,
  ValidationContent,
} from "./types.js";
import { useTreeState } from "./hooks/useTreeState.js";
import { useStreamingTree } from "./hooks/useStreamingTree.js";
import { TreeView } from "./components/TreeView.js";
import { MetadataPanel } from "./components/MetadataPanel.js";
import { NodeDetail } from "./components/NodeDetail.js";
import { ValidationPanel } from "./components/ValidationPanel.js";
import { ScoreGauge } from "./components/ScoreGauge.js";
import { ExportPreview } from "./components/ExportPreview.js";

type SidebarView = "metadata" | "node-detail" | "validation" | "export";

export default function MeceTreeApp({
  toolInputs,
  toolInputsPartial,
  toolResult,
  callServerTool,
}: ViewProps) {
  const [decomposition, setDecomposition] = useState<Decomposition | null>(
    null,
  );
  const [validationReport, setValidationReport] = useState<
    ValidationContent["report"] | null
  >(null);
  const [exportCode, setExportCode] = useState<{
    code: string;
    filename: string;
  } | null>(null);
  const [sidebarView, setSidebarView] = useState<SidebarView>("metadata");

  // Streaming tree parsing
  const streaming = useStreamingTree();

  // Feed partial inputs to streaming hook
  useEffect(() => {
    if (toolInputsPartial) {
      streaming.handlePartial(toolInputsPartial);
    }
  }, [toolInputsPartial]);

  // Feed complete inputs to streaming hook
  useEffect(() => {
    if (toolInputs) {
      streaming.handleComplete(toolInputs);
    }
  }, [toolInputs]);

  // Use streaming state if we don't have a final decomposition yet
  const activeDecomposition =
    decomposition ?? streaming.state.decomposition;

  // Process tool results
  useEffect(() => {
    if (!toolResult?.structuredContent) return;

    const content = toolResult.structuredContent as unknown as StructuredContent;

    switch (content.type) {
      case "decomposition":
        setDecomposition(content.decomposition);
        setSidebarView("metadata");
        setValidationReport(null);
        setExportCode(null);
        break;

      case "validation":
        setValidationReport(content.report);
        setSidebarView("validation");
        break;

      case "refinement":
        setDecomposition(content.decomposition);
        if (content.validation) {
          setValidationReport(content.validation);
        }
        break;

      case "export":
        setExportCode({ code: content.code, filename: content.filename });
        setSidebarView("export");
        break;
    }
  }, [toolResult]);

  // Tree state (expand/collapse/select)
  const treeState = useTreeState(activeDecomposition?.tree ?? null);

  // Handle node selection -> show detail
  const handleNodeSelect = useCallback(
    (id: string) => {
      treeState.select(id);
      setSidebarView("node-detail");
    },
    [treeState],
  );

  // Handle node refinement via app-only tool
  const handleRefineNode = useCallback(
    async (nodeId: string, updates: Record<string, unknown>) => {
      if (!activeDecomposition) return;
      try {
        await callServerTool({
          name: "mece-refine-node",
          arguments: {
            nodeId,
            updates,
            fullTree: JSON.stringify(activeDecomposition),
          },
        });
      } catch (e) {
        console.error("Refine node failed:", e);
      }
    },
    [activeDecomposition, callServerTool],
  );

  // Handle issue click -> select the node
  const handleIssueClick = useCallback(
    (location: string) => {
      // Location format: "node:1.2.1" or "metadata" etc.
      const match = location.match(/^node:(.+)$/);
      if (match) {
        treeState.select(match[1]);
        setSidebarView("node-detail");
      }
    },
    [treeState],
  );

  // Find selected node
  const selectedNode = activeDecomposition?.tree
    ? findNode(activeDecomposition.tree, treeState.selectedId)
    : null;

  // No data yet
  if (!activeDecomposition) {
    if (streaming.state.phase !== "idle") {
      return (
        <div className="mece-app">
          <div className="streaming-indicator">
            <span className="streaming-dot" />
            Loading decomposition...
          </div>
        </div>
      );
    }
    return (
      <div className="mece-app">
        <div className="loading">
          Waiting for decomposition data...
        </div>
      </div>
    );
  }

  return (
    <div className="mece-app">
      {/* Header */}
      <div className="mece-header">
        <h2>{activeDecomposition.metadata.scope}</h2>
        {streaming.state.phase !== "idle" &&
          streaming.state.phase !== "complete" && (
            <div className="streaming-indicator">
              <span className="streaming-dot" />
              Building tree...
            </div>
          )}
      </div>

      {/* Score summary bar */}
      {activeDecomposition.validation_summary && (
        <div style={{ display: "flex", gap: "16px" }}>
          <ScoreGauge
            label="ME"
            score={activeDecomposition.validation_summary.me_score}
          />
          <ScoreGauge
            label="CE"
            score={activeDecomposition.validation_summary.ce_score}
          />
          <ScoreGauge
            label="Overall"
            score={activeDecomposition.validation_summary.overall_score}
          />
        </div>
      )}

      {/* Main panels */}
      <div className="mece-panels">
        {/* Tree */}
        <div className="mece-main">
          <TreeView
            root={activeDecomposition.tree}
            expandedIds={treeState.expandedIds}
            selectedId={treeState.selectedId}
            dependencies={activeDecomposition.cross_branch_dependencies}
            onToggle={treeState.toggle}
            onSelect={handleNodeSelect}
            onExpandAll={treeState.expandAll}
            onCollapseAll={treeState.collapseAll}
          />
        </div>

        {/* Sidebar */}
        <div className="mece-sidebar">
          {/* Tab buttons */}
          <div
            style={{
              display: "flex",
              gap: "4px",
              marginBottom: "12px",
              flexWrap: "wrap",
            }}
          >
            <button
              className={`btn${sidebarView === "metadata" ? " btn-primary" : ""}`}
              onClick={() => setSidebarView("metadata")}
              type="button"
            >
              Meta
            </button>
            {selectedNode && (
              <button
                className={`btn${sidebarView === "node-detail" ? " btn-primary" : ""}`}
                onClick={() => setSidebarView("node-detail")}
                type="button"
              >
                Node
              </button>
            )}
            {validationReport && (
              <button
                className={`btn${sidebarView === "validation" ? " btn-primary" : ""}`}
                onClick={() => setSidebarView("validation")}
                type="button"
              >
                Validate
              </button>
            )}
            {exportCode && (
              <button
                className={`btn${sidebarView === "export" ? " btn-primary" : ""}`}
                onClick={() => setSidebarView("export")}
                type="button"
              >
                Export
              </button>
            )}
          </div>

          {/* Sidebar content */}
          {sidebarView === "metadata" && (
            <MetadataPanel metadata={activeDecomposition.metadata} />
          )}

          {sidebarView === "node-detail" && selectedNode && (
            <NodeDetail
              node={selectedNode}
              onApply={handleRefineNode}
              onClose={() => {
                treeState.select(null);
                setSidebarView("metadata");
              }}
            />
          )}

          {sidebarView === "validation" && validationReport && (
            <ValidationPanel
              report={validationReport}
              onIssueClick={handleIssueClick}
            />
          )}

          {sidebarView === "export" && exportCode && (
            <ExportPreview
              code={exportCode.code}
              filename={exportCode.filename}
            />
          )}
        </div>
      </div>

      {/* Status bar */}
      <div className="status-bar">
        <span className="status-item">
          {activeDecomposition.validation_summary.total_nodes} nodes
        </span>
        <span className="status-item">
          {activeDecomposition.validation_summary.total_atoms} atoms
        </span>
        <span className="status-item">
          {activeDecomposition.validation_summary.total_branches} branches
        </span>
        <span className="status-item">
          depth {activeDecomposition.validation_summary.max_depth}
        </span>
        <span className="status-item">
          {activeDecomposition.metadata.decomposition_dimension}
        </span>
      </div>
    </div>
  );
}

function findNode(node: Node, id: string | null): Node | null {
  if (!id) return null;
  if (node.id === id) return node;
  if (node.node_type === "branch") {
    for (const child of node.children) {
      const found = findNode(child, id);
      if (found) return found;
    }
  }
  return null;
}
