# Demo Benchmark — evalroom-100-v1

Exactly 100 authored responses: 20 scenarios, each with five distinct answers.
Topics include product returns, access permissions, storage, backups, scheduling,
education, archives, data retention, importing, and research workflows.

Each scenario includes a supplied expected answer and context. The policies and
events are self-contained example material. There are easy, medium, and hard
scenarios, including numerical facts, unit equivalence, named entities, permissions,
multiple requirements, and ordered instructions.

| Authored response style | Count | Intent |
| --- | --- | --- |
| Reference | 20 | Direct supported answer |
| Paraphrase | 20 | Equivalent wording or normalized units |
| Conflict | 20 | A changed fact, permission, value, or requirement |
| Incomplete | 20 | Missing detail, including a placeholder and a refusal |
| Off-topic | 20 | Plausible but unresponsive information |

These are input labels, not fixed scoring expectations. The current evaluator
may accept or reject cases in ways that differ from human intent. Its semantic
model, deterministic rules, factual comparisons, weights, and threshold are
unchanged. No scores or expected verdicts are stored in the CSV.

The backend executes this fixed asset through the same CSV reader, validator,
batch evaluator, summary and exporter used by Local Mode. Extra source columns
`topic`, `difficulty` and `response_style` survive in the results. IDs run from
ER-001 through ER-100. The Public Demo threshold is 70.
