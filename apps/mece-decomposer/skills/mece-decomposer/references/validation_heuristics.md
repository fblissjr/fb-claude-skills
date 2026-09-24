# Validation heuristics

last updated: 2026-09-24

The house scoring for MECE validation. The tests themselves are ordinary reasoning; what is fixed here is how each becomes a 0-1 ratio, how the ratios combine, how much rigor each level gets, and the issue vocabulary the JSON uses. Scores go in `validation_summary` (`output_schema.md`).

## Tests and their ratios

Mutual exclusivity (siblings do not overlap):

| Test | Ratio |
|------|-------|
| Definition | per sibling pair, score 2 (disjoint), 1 (gray zone), 0 (a concrete activity fits both); average over pairs, normalized to 0-1 |
| Example | generate examples spanning the parent's scope; examples with exactly one home / all examples |
| Boundary case | construct 1-2 cases on each pair's boundary; cases assignable without inventing a rule the descriptions do not state / all cases |

`ME = 0.3 * definition + 0.4 * example + 0.3 * boundary`

Collective exhaustiveness (siblings cover the parent):

| Test | Ratio |
|------|-------|
| Scenario | 5-10 scenarios within scope, at least 2 unusual but valid; covered / total |
| Negation | per sibling, what would be lost without it; siblings with a unique loss / all siblings. A sibling with no unique loss is redundant (an ME problem) or already covered |
| Stakeholder | per stakeholder group, is all their work represented; fully represented groups / all groups. Support roles (admin, coordination, communication) are the usual omission |

`CE = 0.4 * scenario + 0.35 * negation + 0.25 * stakeholder`

A decomposition built from a document rather than an interview has no stakeholders to ask: drop the stakeholder term and renormalize the other two weights.

`overall = 0.5 * ME + 0.5 * CE`: overlap costs as much as a gap.

## Rigor by depth

| Level | ME | CE | Target |
|-------|----|----|--------|
| L1 | all three tests, every pair | all three, 5+ scenarios | 0.85 each; L1 errors cascade to the whole tree |
| L2 | definition + example for every pair; boundary case only for pairs flagged ambiguous | scenario (3+) + negation; stakeholder only when the branch spans teams | 0.75 each |
| L3 | definition for every pair; example for the most ambiguous pairs | negation only | 0.70 each; atomicity testing carries most of the quality here |
| L4+ | none; rely on the atomicity test | children's descriptions cover the parent's | none |

Tree score is the depth-weighted mean of level scores, weights L1 1.0, L2 0.8, L3 0.5, L4+ 0.2.

## Gates

| Overall | Status |
|---------|--------|
| >= 0.85 | pass: ready for export |
| 0.70 - 0.84 | conditional pass: export with the known issues documented |
| 0.50 - 0.69 | fail: revise before export |
| < 0.50 | hard fail: restructure |

## Issue vocabulary

`validation_summary.issues[].issue_type` is one of:

| Type | Default severity | Meaning |
|------|------------------|---------|
| `overlap` | warning | two siblings share a boundary; raise the severity at L1 |
| `gap` | warning | a scenario has no home; raise the severity at L1 |
| `atomicity` | warning | a leaf fails an atomicity test |
| `dependency` | info | a cross-branch dependency that complicates orchestration |
| `fan_out`, `depth`, `schema` | set by `scripts/validate_mece.py` | structural findings; the script's severities are authoritative |
