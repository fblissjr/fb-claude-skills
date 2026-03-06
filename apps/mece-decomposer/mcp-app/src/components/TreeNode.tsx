import type { Node, BranchNode, AtomNode, CrossBranchDependency } from "../types.js";

interface TreeNodeProps {
  node: Node;
  expandedIds: Set<string>;
  selectedId: string | null;
  dependencies: CrossBranchDependency[];
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
}

export function TreeNodeComponent({
  node,
  expandedIds,
  selectedId,
  dependencies,
  onToggle,
  onSelect,
}: TreeNodeProps) {
  const isBranch = node.node_type === "branch";
  const isExpanded = isBranch && expandedIds.has(node.id);
  const isSelected = selectedId === node.id;

  // Check if this node is involved in any dependency
  const nodeDeps = dependencies.filter(
    (d) => d.from_id === node.id || d.to_id === node.id,
  );

  const badgeClass = isBranch
    ? "branch"
    : `atom-${(node as AtomNode).atom_spec.execution_type}`;

  const badgeLabel = isBranch
    ? "B"
    : (node as AtomNode).atom_spec.execution_type[0].toUpperCase();

  return (
    <div className="tree-node">
      <div
        className={`tree-node-row${isSelected ? " selected" : ""}`}
        onClick={() => onSelect(node.id)}
      >
        {isBranch ? (
          <span
            className="tree-toggle"
            onClick={(e) => {
              e.stopPropagation();
              onToggle(node.id);
            }}
          >
            {isExpanded ? "\u25BC" : "\u25B6"}
          </span>
        ) : (
          <span className="tree-toggle-placeholder" />
        )}

        <span className={`node-badge ${badgeClass}`}>{badgeLabel}</span>

        <span className="node-label" title={node.description}>
          {node.label}
        </span>

        {nodeDeps.map((d, i) => (
          <span
            key={i}
            className={`dep-badge ${d.dependency_type}`}
            title={`${d.dependency_type}: ${d.description}`}
          />
        ))}

        {isBranch && (
          <span className="node-orchestration">
            {(node as BranchNode).orchestration}
          </span>
        )}
      </div>

      {isBranch && isExpanded && (
        <div className="tree-children">
          {(node as BranchNode).children.map((child) => (
            <TreeNodeComponent
              key={child.id}
              node={child}
              expandedIds={expandedIds}
              selectedId={selectedId}
              dependencies={dependencies}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
