---
type: regex
pattern: 'Model choice applies to this consultation only:[*_` ]*gpt-6-astra[*_`]*, effort [*_`]*medium\b'
---

The final response carries the fixed model-scope line with the full model slug and the effort: `Model choice applies to this consultation only: gpt-6-astra, effort medium.` Markdown emphasis around the fixed words or the values is tolerated; an alias instead of the slug, a missing effort, a translation or a sentence that paraphrases the line is not.
