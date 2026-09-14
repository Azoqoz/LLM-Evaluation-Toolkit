# EVALROOM

A Next.js App Router review desk for the existing LLM Evaluation Toolkit API.
TypeScript and Zod describe and validate backend results. React renders the
assessment; it never calculates quality, classifies errors, or invents feedback.

## Run locally

From the repository root, start the Python API in one terminal:

```powershell
$env:APP_MODE = "local"
.venv/Scripts/python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm ci
# Optional: copy .env.example to .env.local to change the backend URL.
npm run dev
```

Visit `http://localhost:3000`. For the production build, run `npm run build`
followed by `npm start`. The existing Streamlit entry point is unchanged.

Node.js 24 LTS is used for verification. There are no remote fonts, image
services, analytics, external LLM providers, or browser-persisted submissions.

## Public Demo / Local Mode

Set `APP_MODE=demo` on the Python process and restart it for Public Demo. Omit
`APP_MODE` or use `APP_MODE=local` for Full Local Mode. Environment values are
trimmed and compared without case; other values resolve to local, matching the
existing mode convention. The API resolves mode at service startup, independently
of Streamlit secrets. The frontend uses `/capabilities` only, never hostname
detection or a separate frontend mode flag. Reload the frontend after a backend
mode change so it can fetch the new capabilities.

| Feature | Public Demo | Full Local Mode |
| --- | --- | --- |
| Single review | Free-form inputs, real evaluator | Free-form inputs, real evaluator |
| Threshold | Fixed 70, enforced by backend | Editable inclusive 0–100, including decimals |
| CSV uploads | Rejected before multipart parsing | Original validation and batch pipeline |
| Batch action | Run fixed 100-response benchmark | Upload and evaluate CSV |
| Results | Original fields, summaries, dossiers, CSV export | Same, retaining extra source columns |

The benchmark route always reads `data/demo_benchmark.csv` from the server. No
uploaded file, path, dataset override, or threshold override is accepted by that
route. Tests validate exactly 100 unique valid rows. The dataset describes
self-contained example policies/scenarios, not a certified measure of model
quality. Response-style labels describe author intent, not expected verdicts.

## Architecture and API

- `src/app`: page/layout, error boundary, metadata, original mark, global styling,
  and a same-origin `/api/[...path]` route handler.
- `src/components`: binder spine, response and marking sheets, review wall,
  inline response dossiers, utility register, and method reference.
- `src/lib/contracts.ts`: runtime response schemas and inferred TypeScript types.
- `src/lib/api.ts`: typed browser requests with safe failure handling.
- `src/lib/proxy.ts`: fixed-route backend proxy with no-store responses. It forwards
  JSON and multipart bodies without transforming evaluation input; arbitrary
  paths, cross-origin browser mutations, and redirects are rejected. Backend
  addresses, raw error messages, and internal paths are not exposed to clients.
- `tests`: component interactions, mode behavior, request/response contracts,
  CSV export, and proxy integration. Mock responses exist only under `tests`.

The proxy allowlist is `GET /health`, `GET /ready`, `GET /capabilities`, `POST /evaluate`,
`POST /evaluate/batch`, and `POST /evaluate/benchmark`. The evaluation routes retain the
existing API contracts; capabilities adds mode policy and benchmark metadata.
Benchmark returns the existing batch response schema. Only a missing/empty JSON
body is accepted by the benchmark operation.

`EVALUATION_API_URL` is server-only (default `http://127.0.0.1:8000`). Never use
a `NEXT_PUBLIC_` prefix for it. `EVALUATION_API_TIMEOUT_MS` defaults to 600000.
A timeout closes the frontend connection; it does not cancel Python inference.
Use a persistent Python process with sufficient memory and cached model weights.
Deploying the frontend alone does not host the evaluator. The proxy assumes the
configured URL points to this trusted backend, not a user-selected destination.

Health is a liveness check. After connecting, the desk polls `/ready` every two seconds while warming and disables single, CSV, and benchmark evaluation until ready. Network failures retry; terminal initialization errors stop polling and offer an explicit readiness recheck. No initialization is triggered by evaluation. See [production startup](../src/api/STARTUP.md) for model prefetch and Render commands. Batch rows remain sequential, and timestamps remain evaluator timestamps.

Finite scores are displayed to at most two decimals; their values and the
backend-exported CSV are unchanged. Null scores display N/A. Histogram bins and
finding counts are descriptive aggregations of returned rows, not new scoring
logic. Average scores/pass rates come from the backend summary. The register
retains all rows with original-order, quality-sort, search and filter controls.
CSV export always uses `evaluated_csv`, including original column handling.

## Visual and interaction system

Warm taupe desk, ivory sheets, dark brown ink, forest approval and brick rejection.
A narrow binder spine holds identity, workspace tabs, and the server's mode.
Editorial sans-serif headings and document inputs pair with selective serif
reviewer notes. Paper stacking, grading strokes, circular review stamps, and
slight sheet rotations replace the previous visual system.

The demo contact sheet contains 100 numbered, unmarked placeholders until the
real benchmark returns. Returned rows supply every verdict and score; five
descriptive strokes accompany the exact displayed quality. Selecting a sheet
pulls its dossier below the wall. Summary figures sit in the margin, with the
sortable/filterable register and unchanged CSV export below the collection.

Mobile retains the binder edge and follows submission → action → verdict →
finding → dimensions. The wall uses five columns, sheets turn into a single
reading sequence, and utility tables scroll horizontally. Native
inputs/disclosures, visible focus, a skip link, semantic tables, status/alert
regions, text verdicts, and reduced-motion support provide keyboard and
assistive-technology affordances. Editing a reviewed input or threshold marks
the old assessment as stale. Switching workspaces preserves the in-memory work.

## Verification

```console
python -m pytest -q
```

From `frontend`:

```console
npm test
npm run lint
npm run build
```

No browser automation is required by these tests. The Next.js setup follows the
official [App Router installation](https://nextjs.org/docs/app/getting-started/installation),
[route handler](https://nextjs.org/docs/app/api-reference/file-conventions/route), and
[Vitest integration](https://nextjs.org/docs/app/guides/testing/vitest) documentation.

## Deployment limits

There is no authentication, cross-request results database, job queue, resumable
processing, or model cancellation. A public deployment still needs suitable
infrastructure rate/concurrency limits and request timeouts. Uploads and batch
results are memory-resident; returning JSON plus CSV increases payload size.
Local upload semantics deliberately retain the current behavior, without adding
an application file/row cap. Same-origin proxying avoids a CORS configuration;
the backend should be configured with `APP_MODE=demo` for a public deployment,
even if it is accessible directly. Public upload policy is enforced in Python.
