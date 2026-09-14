# Production startup

Run the Render Python service from the repository root.

Build Command:

```sh
pip install -r requirements.txt && python -m src.application.prefetch_model
```

Start Command:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python -m uvicorn src.api.app:app --host 0.0.0.0 --port $PORT --workers 1
```

Set Render's health-check path to `/health`. Keep the existing `APP_MODE` value.
The Next.js service retains its build/start commands and its server-only
`EVALUATION_API_URL` pointing at this API. These commands follow Render's
[FastAPI deployment interface](https://render.com/docs/deploy-fastapi).

The build downloads the existing `sentence-transformers/all-MiniLM-L6-v2`,
saves a complete SentenceTransformer model under
`.model-cache/all-MiniLM-L6-v2` inside the app, then reloads it with
`local_files_only=True` and verifies a forward pass. A failed prefetch or
verification fails the build. The cache is ignored by Git but is produced
inside the deployed build artifact; no external persistent disk is required.
No model conversion, quantization, new runtime, or scoring change is involved.
The upstream model ID is unchanged; this task does not introduce a revision pin.

Runtime prefers that saved artifact. A present but broken artifact fails safely
without silently downloading replacements. The production command forces
Hugging Face/Transformers offline mode as well. Local development without a
prefetched artifact retains the existing local-cache-first/download fallback,
but it now runs during background initialization, never during an API evaluation.

FastAPI lifespan launches one daemon thread and yields immediately. It does not
wait for the sentence-transformers import, model loading, or warm-up inference
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
memory for the existing PyTorch model and its dependencies.

The desk polls every two seconds after each completed warming response and
retries transient connection failures. GET proxy calls time out after at most
15 seconds so sleeping/waking services can recover. Polls never overlap and
stop on ready, terminal initialization error, or component unmount. Evaluation
controls remain disabled until readiness succeeds; text/file preparation remains
available. An evaluation rejected by a restarted backend re-enters readiness
polling without resubmitting the user's request.
