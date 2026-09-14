import { z } from "zod";
import { batchSchema, capabilitiesSchema, readinessSchema, resultSchema, type EvaluationInput } from "./contracts";
import { ReviewError } from "./errors";

async function request<T>(path: string, schema: z.ZodType<T>, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try { response = await fetch(`/api/${path}`, { ...options, cache: "no-store" }); }
  catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ReviewError("backend_unavailable");
  }
  let data: unknown;
  try { data = await response.json(); } catch { throw new ReviewError("invalid_response"); }
  if (!response.ok) {
    const parsed = z.object({ error: z.object({ code: z.string() }) }).safeParse(data);
    throw new ReviewError(parsed.success ? parsed.data.error.code : "internal_error");
  }
  const parsed = schema.safeParse(data);
  if (!parsed.success) throw new ReviewError("invalid_response");
  return parsed.data;
}
export const api = {
  ready: (signal?: AbortSignal) => request("ready", readinessSchema, { signal }),
  connect: async (signal?: AbortSignal) => {
    const [, capabilities] = await Promise.all([
      request("health", z.object({ status: z.literal("ok"), evaluator_version: z.string() }), { signal }),
      request("capabilities", capabilitiesSchema, { signal }),
    ]);
    return capabilities;
  },
  evaluate: (input: EvaluationInput, signal?: AbortSignal) => request("evaluate", resultSchema, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input), signal,
  }),
  batch: (file: File, threshold: number, signal?: AbortSignal) => {
    const body = new FormData(); body.append("file", file); body.append("pass_threshold", String(threshold));
    return request("evaluate/batch", batchSchema, { method: "POST", body, signal });
  },
  benchmark: (signal?: AbortSignal) => request("evaluate/benchmark", batchSchema, { method: "POST", signal }),
};
