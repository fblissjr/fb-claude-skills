import type { Node, CrossBranchDependency } from "../types.js";
import { TreeNodeComponent } from "./TreeNode.js";

interface TreeViewProps {
  root: Node;
  expandedIds: Set<string>;
  selectedId: string | null;
  dependencies: CrossBranchDependency[];
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
}

export function TreeView({
  root,
  expandedIds,
  selectedId,
  dependencies,
  onToggle,
  onSelect,
  onExpandAll,
  onCollapseAll,
}: TreeViewProps) {
  return (
    <div className="tree-container">
      <div style={{ display: "flex", gap: "6px", marginBottom: "8px" }}>
        <button className="btn" onClick={onExpandAll} type="button">
          Expand All
        </button>
        <button className="btn" onClick={onCollapseAll} type="button">
          Collapse All
        </button>
      </div>
      <TreeNodeComponent
        node={root}
        expandedIds={expandedIds}
        selectedId={selectedId}
        dependencies={dependencies}
        onToggle={onToggle}
        onSelect={onSelect}
      />
    </div>
  );
}
