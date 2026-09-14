# Production startup

Run the Render Python service from the repository root.

Build Command:

```sh
pip install --no-cache-dir -r requirements-render.txt && HF_HUB_OFFLINE=0 python -m src.application.prefetch_onnx
```

Start Command:

```sh
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false python -m uvicorn src.api.app:app --host 0.0.0.0 --port $PORT --workers 1
```

Set Render's health-check path to `/health`. Set `APP_MODE=demo` and `PYTHON_VERSION=3.12.13` on Render.
The Next.js service retains its build/start commands and its server-only
`EVALUATION_API_URL` pointing at this API. These commands follow Render's
[FastAPI deployment interface](https://render.com/docs/deploy-fastapi).

The build fetches the official full-precision `onnx/model.onnx` and matching
artifacts for `sentence-transformers/all-MiniLM-L6-v2`, pinned to revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. It does not export, quantize, or
install Torch/SentenceTransformers/Transformers. Artifacts are saved beneath
`.model-cache/all-MiniLM-L6-v2-onnx` inside the deployed build artifact. The
prefetch step verifies a real forward pass and writes a SHA-256 manifest.
No external persistent disk is needed. Build failure prevents deployment.

Demo mode uses ONNX Runtime CPU inference with the official Rust tokenizer,
256-token right truncation (including special tokens), attention-mask mean
pooling, and float32 L2 normalization. The existing semantic scorer still
performs cosine calculation, clipping, and rounding. The evaluator and its
scoring/classification/feedback logic are unchanged.

Runtime reads only local ONNX/tokenizer files. Missing or corrupt artifacts
produce the existing safe readiness error; there is no runtime download or
SentenceTransformer fallback. Only the build step imports the Hub downloader.
ONNX runs one thread, at most two sequences per inference, basic graph
optimization, and no CPU memory arena/prepacked-weight cache to limit RSS.
The API serializes evaluations as before. Use exactly one Uvicorn worker.

Local Mode remains unchanged: install `requirements.txt`, use `APP_MODE=local`,
and optionally run `python -m src.application.prefetch_model` to populate the
original `.model-cache/all-MiniLM-L6-v2` SentenceTransformer cache. The local
backend retains the original cache-first/download fallback during warm-up.
`requirements-render.txt` is exclusively for the production/demo API; it does
not include Streamlit or local-model/test tooling. Do not install the local
requirements alongside it on Render. Clear Render's build cache when switching
from the old requirements so old heavyweight packages are not retained.

FastAPI lifespan launches one daemon thread and yields immediately. It does not
wait for embedding-runtime imports, model loading, or warm-up inference
before the server can bind. Ordinary Python application imports still precede
binding. The thread initializes one evaluator and performs one normalized
embedding forward pass before publishing readiness.

- `GET /health`: HTTP 200, unchanged liveness body, including during warm-up
  and after initialization failure.
- `GET /ready`: HTTP 200 with `Cache-Control: no-store` and exactly
  `{"status":"warming"}`, `{"status":"ready"}`, or
  `{"status":"error","message":"Evaluator initialization failed."}`.
  Consumers must inspect the body; this is not a load-balancer readiness probe.
- Evaluation POST routes return safe HTTP 503 until ready, before request body
  parsing. Demo CSV restrictions still take precedence. GET probes never start
  initialization.

An initialization lock prevents duplicate attempts, including concurrent calls.
The ready evaluator and model are reused under a separate evaluation lock;
each request's exact numeric threshold is set and restored inside that lock.
Inference is serialized per process, including whole CSV batches. Liveness and
readiness do not take the inference lock.

Initialization failure is terminal for that process. Restart the API after
correcting the build/cache/resources, then use “Check readiness again” in the
frontend. Rechecking readiness does not initiate another warm-up or download.
No raw exception text, stack trace, or path is returned by readiness/errors.
The daemon cannot cancel a stuck native model load; shutdown ends the process.
Use one worker to avoid duplicating model memory. Memory exhaustion can kill
the process before Python can report an error, so Render must provide enough
memory for the API and ONNX session. Actual Render/Linux RSS must still be monitored.

The desk polls every two seconds after each completed warming response and
retries transient connection failures. GET proxy calls time out after at most
15 seconds so sleeping/waking services can recover. Polls never overlap and
stop on ready, terminal initialization error, or component unmount. Evaluation
controls remain disabled until readiness succeeds; text/file preparation remains
available. An evaluation rejected by a restarted backend re-enters readiness
polling without resubmitting the user's request.

## Reproducible verification and memory diagnostics

The initialization thread logs RSS before loading and after warm-up, only in
Demo mode. These diagnostics are never exposed through an HTTP endpoint.
For a complete offline API memory smoke test (including the 100-row benchmark
and a maximum-length input pair), run:

```console
python -m src.application.diagnose_onnx
```

The diagnostic starts and stops its own loopback server, samples process RSS
throughout startup/inference, and fails on Torch, SentenceTransformers, or
Transformers imports. Local Windows measurements are recorded in
[ONNX verification](ONNX_VERIFICATION.md); they are not a Render measurement.

For real parity tests, use a developer environment containing both backends,
install `onnxruntime==1.30.0 psutil==7.2.2`, and prefetch both caches. Then run:

```sh
REQUIRE_ONNX_PARITY=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python -m pytest tests/onnx -q
python -m pytest tests/parity -q
python -m pytest -q
```

Real-model tests skip when optional artifacts/dependencies are absent in an
ordinary local environment. `REQUIRE_ONNX_PARITY=1` makes absent artifacts a
failure; this flag was enabled for the reported focused run.