---
# claim: house rule 'no italics for emphasis': no *word* or _word_ spans (bullet markers and snake_case do not match).
type: regex
pattern: '(?<![\w*])\*(?![\s*])[^*\n]+(?<![\s*])\*(?![\w*])|(?<![\w_])_(?![\s_])[^_\n]+(?<![\s_])_(?![\w_])'
match: not_contains
---
