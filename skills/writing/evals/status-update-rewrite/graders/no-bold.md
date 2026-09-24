---
# claim: house rule 'no bold for emphasis': the draft has no interface labels, so any bold in the rewrite is emphasis.
type: regex
pattern: '\*\*[^*\n]+\*\*|__[^_\n]+__'
match: not_contains
---
