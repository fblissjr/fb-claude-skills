import { useState } from "react";
import type {
  Node,
  BranchNode,
  AtomNode,
  Orchestration,
} from "../types.js";

interface NodeDetailProps {
  node: Node;
  onApply: (nodeId: string, updates: Record<string, unknown>) => void;
  onClose: () => void;
}

export function NodeDetail({ node, onApply, onClose }: NodeDetailProps) {
  const [label, setLabel] = useState(node.label);
  const [description, setDescription] = useState(node.description);
  const [orchestration, setOrchestration] = useState<Orchestration | "">(
    node.node_type === "branch" ? node.orchestration : "",
  );
  const [rationale, setRationale] = useState(
    node.node_type === "branch" ? node.orchestration_rationale : "",
  );

  const isBranch = node.node_type === "branch";
  const isAtom = node.node_type === "atom";

  const handleApply = () => {
    const updates: Record<string, unknown> = {};
    if (label !== node.label) updates.label = label;
    if (description !== node.description) updates.description = description;
    if (isBranch) {
      const b = node as BranchNode;
      if (orchestration && orchestration !== b.orchestration)
        updates.orchestration = orchestration;
      if (rationale !== b.orchestration_rationale)
        updates.orchestration_rationale = rationale;
    }
    if (Object.keys(updates).length > 0) {
      onApply(node.id, updates);
    }
  };

  return (
    <div className="node-detail">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3>
          Node {node.id}
          <span style={{ fontWeight: 400, color: "var(--color-text-secondary, #888)", marginLeft: "8px" }}>
            {node.node_type}
          </span>
        </h3>
        <button className="btn" onClick={onClose} type="button">
          Close
        </button>
      </div>

      <div className="detail-section">
        <span className="detail-label">Label</span>
        <input
          className="detail-field"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
        />
      </div>

      <div className="detail-section">
        <span className="detail-label">Description</span>
        <textarea
          className="detail-field"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />
      </div>

      {isBranch && (
        <>
          <div className="detail-section">
            <span className="detail-label">Orchestration</span>
            <select
              className="detail-field-select"
              value={orchestration}
              onChange={(e) =>
                setOrchestration(e.target.value as Orchestration)
              }
            >
              <option value="sequential">sequential</option>
              <option value="parallel">parallel</option>
              <option value="conditional">conditional</option>
              <option value="loop">loop</option>
            </select>
          </div>
          <div className="detail-section">
            <span className="detail-label">Orchestration Rationale</span>
            <textarea
              className="detail-field"
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              rows={2}
            />
          </div>
        </>
      )}

      {isAtom && (
        <>
          <div className="detail-section">
            <span className="detail-label">Execution Type</span>
            <span className="metadata-tag">
              {(node as AtomNode).atom_spec.execution_type}
            </span>
          </div>

          <div className="detail-section">
            <span className="detail-label">Inputs</span>
            <div className="detail-tags">
              {(node as AtomNode).atom_spec.inputs.map((inp) => (
                <span key={inp} className="detail-tag">
                  {inp}
                </span>
              ))}
            </div>
          </div>

          <div className="detail-section">
            <span className="detail-label">Outputs</span>
            <div className="detail-tags">
              {(node as AtomNode).atom_spec.outputs.map((out) => (
                <span key={out} className="detail-tag">
                  {out}
                </span>
              ))}
            </div>
          </div>

          <div className="detail-section">
            <span className="detail-label">Error Modes</span>
            <div className="detail-tags">
              {(node as AtomNode).atom_spec.error_modes.map((err) => (
                <span key={err} className="detail-tag">
                  {err}
                </span>
              ))}
            </div>
          </div>

          <div className="detail-section">
            <span className="detail-label">Duration</span>
            <span className="metadata-value">
              {(node as AtomNode).atom_spec.estimated_duration}
            </span>
          </div>
        </>
      )}

      <div style={{ display: "flex", gap: "8px", paddingTop: "8px" }}>
        <button className="btn btn-primary" onClick={handleApply} type="button">
          Apply
        </button>
        <button className="btn" onClick={onClose} type="button">
          Cancel
        </button>
      </div>
    </div>
  );
}
