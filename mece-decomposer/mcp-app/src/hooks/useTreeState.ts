import { useState, useCallback } from "react";
import type { Node } from "../types.js";

export interface TreeState {
  expandedIds: Set<string>;
  selectedId: string | null;
  toggle: (id: string) => void;
  select: (id: string | null) => void;
  expandAll: () => void;
  collapseAll: () => void;
}

/**
 * Manage expand/collapse and selection state for a tree.
 * By default, L0 and L1 nodes are expanded, L2+ collapsed.
 */
export function useTreeState(root: Node | null): TreeState {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => {
    if (!root) return new Set<string>();
    return computeDefaultExpanded(root);
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const toggle = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const select = useCallback((id: string | null) => {
    setSelectedId(id);
  }, []);

  const expandAll = useCallback(() => {
    if (!root) return;
    const all = new Set<string>();
    collectBranchIds(root, all);
    setExpandedIds(all);
  }, [root]);

  const collapseAll = useCallback(() => {
    setExpandedIds(new Set());
  }, []);

  return { expandedIds, selectedId, toggle, select, expandAll, collapseAll };
}

function computeDefaultExpanded(node: Node): Set<string> {
  const expanded = new Set<string>();
  collectDefaultExpanded(node, expanded);
  return expanded;
}

function collectDefaultExpanded(node: Node, expanded: Set<string>): void {
  if (node.node_type === "branch") {
    if (node.depth <= 1) {
      expanded.add(node.id);
    }
    for (const child of node.children) {
      collectDefaultExpanded(child, expanded);
    }
  }
}

function collectBranchIds(node: Node, ids: Set<string>): void {
  if (node.node_type === "branch") {
    ids.add(node.id);
    for (const child of node.children) {
      collectBranchIds(child, ids);
    }
  }
}
