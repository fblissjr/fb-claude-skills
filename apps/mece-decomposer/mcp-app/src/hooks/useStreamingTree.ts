import { useState, useCallback, useRef } from "react";
import type { Decomposition } from "../types.js";

export type StreamingPhase =
  | "idle"
  | "metadata_only"
  | "tree_root"
  | "building_tree"
  | "complete";

export interface StreamingState {
  decomposition: Decomposition | null;
  phase: StreamingPhase;
}

/**
 * Parse partial and complete tool inputs into a renderable decomposition.
 *
 * The host heals partial JSON, so `toolInputsPartial.decomposition` is always
 * a valid JSON string (possibly truncated/completed by the host).
 */
export function useStreamingTree(): {
  state: StreamingState;
  handlePartial: (partial: Record<string, unknown> | null) => void;
  handleComplete: (complete: Record<string, unknown> | null) => void;
  reset: () => void;
} {
  const [state, setState] = useState<StreamingState>({
    decomposition: null,
    phase: "idle",
  });
  const lastPartialRef = useRef<string>("");

  const handlePartial = useCallback(
    (partial: Record<string, unknown> | null) => {
      if (!partial) return;

      const raw = partial.decomposition;
      if (typeof raw !== "string" || !raw.trim()) return;

      // Skip if we already parsed this exact string
      if (raw === lastPartialRef.current) return;
      lastPartialRef.current = raw;

      try {
        const parsed = JSON.parse(raw) as Partial<Decomposition>;
        let phase: StreamingPhase = "metadata_only";

        if (parsed.tree) {
          if (
            parsed.tree.node_type === "branch" &&
            "children" in parsed.tree &&
            Array.isArray(parsed.tree.children) &&
            parsed.tree.children.length > 0
          ) {
            phase = "building_tree";
          } else {
            phase = "tree_root";
          }
        }

        setState({
          decomposition: parsed as Decomposition,
          phase,
        });
      } catch {
        // JSON not parseable yet, skip
      }
    },
    [],
  );

  const handleComplete = useCallback(
    (complete: Record<string, unknown> | null) => {
      if (!complete) return;

      const raw = complete.decomposition;
      if (typeof raw !== "string") return;

      try {
        const parsed = JSON.parse(raw) as Decomposition;
        setState({ decomposition: parsed, phase: "complete" });
        lastPartialRef.current = "";
      } catch {
        // Keep existing state if final parse fails
      }
    },
    [],
  );

  const reset = useCallback(() => {
    setState({ decomposition: null, phase: "idle" });
    lastPartialRef.current = "";
  }, []);

  return { state, handlePartial, handleComplete, reset };
}
