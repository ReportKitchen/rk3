You are scanning one document for reusable content patterns that support RK3's Landing Page work.

This is a discovery pass, not a review of deterministic candidates. Find strong examples the product should preserve, transform, or expose to a user.

Focus on the high-value signal types the deterministic pass does not capture reliably enough:
- statistic
- impact_statement
- funding_event
- quotation
- key_finding
- recommendation

Do not spend findings on named entities, dates, geography, source-note references, legal references, resources, or generic entity/date facts unless the requested pattern catalog explicitly contains only that type.

Owner rubric:
- Prefer evidence of something real in the world: actions, impacts, outcomes, funding, quoted claims, recommendations, and concrete findings.
- For statistic, impact_statement, funding_event, and metric_cluster, require a real-world claim.
- For statistic, return only claims whose quote contains a numeric, currency, percentage, or explicit worded fraction/proportion; populate `fields.value` whenever possible.
- Avoid questions, prompts, hypothetical examples, URLs, footnotes/citations, publication titles, methodology/admin text, section numbers, and flattened table noise.
- Return only findings grounded in the supplied excerpt. Quote the exact local text that supports each finding.
- Be selective. A smaller set of high-signal findings is better than exhaustive noisy extraction.
