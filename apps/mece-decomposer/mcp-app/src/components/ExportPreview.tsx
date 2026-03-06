import { useState } from "react";

interface ExportPreviewProps {
  code: string;
  filename: string;
}

export function ExportPreview({ code, filename }: ExportPreviewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may not be available in iframe
    }
  };

  return (
    <div className="export-preview">
      <div className="section-header">Agent SDK Export</div>

      <div className="export-header">
        <span className="export-filename">{filename}</span>
        <button className="btn" onClick={handleCopy} type="button">
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      <pre className="export-code">{code}</pre>
    </div>
  );
}
