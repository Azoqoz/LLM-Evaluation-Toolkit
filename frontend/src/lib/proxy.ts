import { errorMessages } from "./errors";

const routes: Record<string, string> = {
  health: "GET", capabilities: "GET", evaluate: "POST", "evaluate/batch": "POST", "evaluate/benchmark": "POST",
};
function failure(status: number, code: string) {
  return Response.json({ error: { code, message: errorMessages[code] ?? errorMessages.http_error, details: {} } },
    { status, headers: { "Cache-Control": "no-store" } });
}
/** A fixed-route proxy. No user-controlled hosts, credentials, redirects or paths. */
export async function proxyRequest(request: Request, path: string): Promise<Response> {
  if (!Object.hasOwn(routes, path)) return failure(404, "http_error");
  if (request.method !== routes[path]) return failure(405, "http_error");
  const origin = request.headers.get("origin");
  if (request.method === "POST" && origin && origin !== new URL(request.url).origin) return failure(403, "http_error");
  try {
    const base = new URL(process.env.EVALUATION_API_URL ?? "http://127.0.0.1:8000");
    if (!["http:", "https:"].includes(base.protocol) || base.username || base.password) return failure(502, "backend_unavailable");
    const url = `${base.toString().replace(/\/$/, "")}/${path}`;
    const configuredTimeout = Number(process.env.EVALUATION_API_TIMEOUT_MS ?? 600000);
    const timeout = Number.isFinite(configuredTimeout) && configuredTimeout > 0 ? configuredTimeout : 600000;
    const response = await fetch(url, {
      method: request.method,
      headers: request.headers.has("content-type") ? { "Content-Type": request.headers.get("content-type")! } : {},
      body: request.method === "POST" ? await request.arrayBuffer() : undefined,
      cache: "no-store", redirect: "error",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(timeout)]),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const code = typeof body?.error?.code === "string" && Object.hasOwn(errorMessages, body.error.code) ? body.error.code : "internal_error";
      return failure(response.status, code);
    }
    if (!response.headers.get("content-type")?.includes("application/json")) return failure(502, "invalid_response");
    return new Response(response.body, { status: response.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  } catch (error) {
    return failure(error instanceof Error && error.name === "TimeoutError" ? 504 : 502,
      error instanceof Error && error.name === "TimeoutError" ? "timeout" : "backend_unavailable");
  }
}
