# trigger: mece
## MECE decomposition principles (auto-loaded)
- Mutually Exclusive: no overlap between sibling components. Collectively Exhaustive: no gaps.
- Dimension selection: temporal, functional, stakeholder, state, or input-output. Pick the most natural non-overlapping cut.
- Atomicity: stop decomposing when sub-steps always co-occur, single responsibility, stable interface, SDK-mappable.
- Fan-out: 3-7 children per branch. Warn at >5 depth levels.
- Quality gate: ME/CE scores >= 0.70 for export, >= 0.85 for confidence.
- For full methodology, scoring rubrics, and SDK mapping, invoke /mece-decomposer:mece-decomposer.
