import type { Metadata } from "../types.js";

interface MetadataPanelProps {
  metadata: Metadata;
}

export function MetadataPanel({ metadata }: MetadataPanelProps) {
  return (
    <div className="metadata-panel">
      <div className="section-header">Metadata</div>

      <div className="metadata-item">
        <span className="metadata-label">Scope</span>
        <span className="metadata-value">{metadata.scope}</span>
      </div>

      <div className="metadata-item">
        <span className="metadata-label">Trigger</span>
        <span className="metadata-value">{metadata.trigger}</span>
      </div>

      <div className="metadata-item">
        <span className="metadata-label">Completion</span>
        <span className="metadata-value">{metadata.completion_criteria}</span>
      </div>

      <div className="metadata-item">
        <span className="metadata-label">Dimension</span>
        <span className="metadata-value">
          <span className="metadata-tag">
            {metadata.decomposition_dimension}
          </span>
        </span>
      </div>

      <div className="metadata-item">
        <span className="metadata-label">Source</span>
        <span className="metadata-value">
          <span className="metadata-tag">{metadata.source_type}</span>
        </span>
      </div>

      {metadata.inclusions && metadata.inclusions.length > 0 && (
        <div className="metadata-item">
          <span className="metadata-label">Inclusions</span>
          <span className="metadata-value">
            {metadata.inclusions.map((inc) => (
              <span key={inc} className="metadata-tag">
                {inc}
              </span>
            ))}
          </span>
        </div>
      )}

      {metadata.exclusions && metadata.exclusions.length > 0 && (
        <div className="metadata-item">
          <span className="metadata-label">Exclusions</span>
          <span className="metadata-value">
            {metadata.exclusions.map((exc) => (
              <span key={exc} className="metadata-tag">
                {exc}
              </span>
            ))}
          </span>
        </div>
      )}
    </div>
  );
}
