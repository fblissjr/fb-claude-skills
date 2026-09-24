---
# claim: house rule 'sentence case headings': no markdown heading has a capitalized word after its first word (the draft has no proper nouns to excuse one).
type: regex
pattern: '^#{1,6}[ \t]+[^\n]*?[ \t][A-Z][a-z]'
flags: m
match: not_contains
---
