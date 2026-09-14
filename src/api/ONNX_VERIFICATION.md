# ONNX verification — 2026-09-14

Reference: existing cached SentenceTransformer backend (5.6.1, Torch 2.13.0,
CPU float32). Candidate: ONNX Runtime 1.30.0 CPU, tokenizers 0.22.2.
Both use sentence-transformers/all-MiniLM-L6-v2 and a maximum of 256 tokens.

Artifacts come from the [official repository](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41),
revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`:

- `onnx/model.onnx` (unquantized float32)
- `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`, `vocab.txt`
- `sentence_bert_config.json`, `config.json`, `1_Pooling/config.json`

ONNX SHA-256:
`6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452`.
The build records all artifact checksums in its ignored cache manifest.

Initial comparison, including multilingual, whitespace and overlength inputs:
384-dimensional float32 embeddings; token IDs, attention masks and token types
matched exactly. Largest observed component difference: 1.6298145e-7. Focused
tests use absolute embedding tolerance 2e-6 (relative 2e-5) and absolute cosine
tolerance 2e-6. Rounded semantic scores must match exactly.

All 100 benchmark rows matched in every evaluation field (timestamps frozen in
tests), including nullable metrics, quality, status, classification and feedback.
Both produced 40 Pass / 60 Fail. Threshold-sensitive fixtures compare the
original and candidate evaluator at zero, 70, 100, the reference quality, and
0.01 immediately above/below it. No compensating thresholds or rounding changes
are used. Finite float32 comparisons do not establish bitwise equivalence for
all possible inputs or every CPU.

Full API memory diagnostic, Windows / Python 3.12.13, offline:

| Stage | Process RSS |
| --- | ---: |
| Before model initialization | 103.8 MiB |
| Ready | 228.71 MiB |
| After benchmark and maximum-length pair | 234.37 MiB |
| Sampled peak, including startup | 247.38 MiB |

The process imported none of `torch`, `sentence_transformers`, or
`transformers`; an import guard was active. These are whole-process RSS
measurements, not just model allocations. The peak is sampled every 5 ms, so
brief unobserved peaks remain possible. This provides substantial local headroom
below 512 MB; actual Render/Linux memory has not been measured or deployed here.
Startup emits private log diagnostics to support that deployment check.
