// @vitest-environment node
import { expect, it, vi } from "vitest";
import { proxyRequest } from "@/lib/proxy";
import { result } from "./fixtures";

it("forwards readiness without caching and preserves terminal status", async () => {
  const fetch = vi.fn().mockResolvedValue(Response.json({ status: "error", message: "Evaluator initialization failed." }));
  vi.stubGlobal("fetch", fetch);
  const response = await proxyRequest(new Request("http://desk/api/ready"), "ready");
  expect(await response.json()).toEqual({ status: "error", message: "Evaluator initialization failed." });
  expect(response.headers.get("cache-control")).toBe("no-store");
  expect(fetch.mock.calls[0][0]).toMatch(/\/ready$/);
});

it("forwards only the fixed endpoint to the server-only backend", async () => {
  vi.stubEnv("EVALUATION_API_URL", "http://backend:8000");
  const fetch = vi.fn().mockResolvedValue(Response.json(result)); vi.stubGlobal("fetch", fetch);
  const response = await proxyRequest(new Request("http://desk/api/evaluate", { method: "POST", body: '{"question":"q","answer":"a"}', headers: { "content-type": "application/json", cookie: "private=value" } }), "evaluate");
  expect(await response.json()).toEqual(result);
  expect(fetch.mock.calls[0][0]).toBe("http://backend:8000/evaluate");
  expect(fetch.mock.calls[0][1].headers).toEqual({ "Content-Type": "application/json" });
  expect(fetch.mock.calls[0][1].redirect).toBe("error");
  expect(response.headers.get("cache-control")).toBe("no-store");
});
it.each(["../private", "https://attacker.test", "evaluate/../../files", "__proto__"])("rejects non-allowlisted path %s", async path => {
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
  expect((await proxyRequest(new Request("http://desk/api/x"), path)).status).toBe(404);
  expect(fetch).not.toHaveBeenCalled();
});
it("rejects a cross-origin mutation and unsupported method", async () => {
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
  expect((await proxyRequest(new Request("http://desk/api/evaluate", { method: "POST", headers: { origin: "https://other.test" } }), "evaluate")).status).toBe(403);
  expect((await proxyRequest(new Request("http://desk/api/evaluate"), "evaluate")).status).toBe(405);
  expect(fetch).not.toHaveBeenCalled();
});
it("preserves raw CSV multipart bytes", async () => {
  const fetch = vi.fn().mockResolvedValue(Response.json({ rows: [] })); vi.stubGlobal("fetch", fetch);
  const request = new Request("http://desk/api/evaluate/batch", { method: "POST", headers: { "content-type": "multipart/form-data; boundary=fixed" }, body: "--fixed\r\noriginal bytes" });
  await proxyRequest(request, "evaluate/batch");
  expect(new TextDecoder().decode(fetch.mock.calls[0][1].body)).toBe("--fixed\r\noriginal bytes");
});
it("sanitizes a backend error including nested details", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ error: { code: "evaluation_failed", message: "Traceback C:/secret", details: { path: "C:/secret" } } }, { status: 503 })));
  const response = await proxyRequest(new Request("http://desk/api/evaluate", { method: "POST" }), "evaluate");
  expect(response.status).toBe(503);
  expect(await response.text()).not.toMatch(/secret|Traceback/);
});
it("sanitizes network failure and rejects non-JSON success", async () => {
  const fetch = vi.fn().mockRejectedValueOnce(new Error("C:/secret")).mockResolvedValueOnce(new Response("private debug HTML")); vi.stubGlobal("fetch", fetch);
  expect((await proxyRequest(new Request("http://desk/api/health"), "health")).status).toBe(502);
  expect((await proxyRequest(new Request("http://desk/api/health"), "health")).status).toBe(502);
});
