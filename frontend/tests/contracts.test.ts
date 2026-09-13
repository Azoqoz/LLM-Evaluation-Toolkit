import { describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { batchSchema, capabilitiesSchema, formatScore, resultSchema } from "@/lib/contracts";
import { ReviewError } from "@/lib/errors";
import { batch, capabilities, result } from "./fixtures";

describe("typed API contracts", () => {
  it("preserves nullable metrics, metadata, columns and CSV bytes", () => {
    expect(resultSchema.parse(result)).toEqual(result);
    expect(batchSchema.parse(batch).evaluated_csv).toBe(batch.evaluated_csv);
    expect(batchSchema.parse(batch).columns).toEqual(batch.columns);
    expect(capabilitiesSchema.parse(capabilities)).toEqual(capabilities);
    expect(formatScore(null)).toBe("N/A");
    expect(formatScore(0)).toBe("0");
    expect(formatScore(80.01)).toBe("80.01");
  });
  it("requires a real mode and a valid verdict", () => {
    expect(capabilitiesSchema.safeParse({ ...capabilities, app_mode: undefined }).success).toBe(false);
    expect(resultSchema.safeParse({ ...result, status: "approved" }).success).toBe(false);
  });
  it("passes free-form input and a fractional threshold unchanged", async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json(result)); vi.stubGlobal("fetch", fetch);
    const input = { question: " q ", answer: "answer", expected_answer: "", context: null, pass_threshold: 80.01 };
    expect(await api.evaluate(input)).toEqual(result);
    expect(fetch.mock.calls[0][0]).toBe("/api/evaluate");
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(input);
  });
  it("sends multipart without overriding its boundary", async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json(batch)); vi.stubGlobal("fetch", fetch);
    const file = new File(["question,answer\nq,a\n"], "case.csv", { type: "text/csv" });
    await api.batch(file, 80.01);
    const options = fetch.mock.calls[0][1];
    expect(options.headers).toBeUndefined();
    expect(options.body.get("file").name).toBe("case.csv");
    expect(options.body.get("pass_threshold")).toBe("80.01");
  });
  it("benchmark sends no replaceable dataset or threshold", async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json(batch)); vi.stubGlobal("fetch", fetch);
    await api.benchmark();
    expect(fetch.mock.calls[0][0]).toBe("/api/evaluate/benchmark");
    expect(fetch.mock.calls[0][1].body).toBeUndefined();
  });
  it("hides backend exception messages", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ error: { code: "evaluation_failed", message: "Traceback C:/private/model" } }, { status: 503 })));
    await expect(api.evaluate({ question: "q", answer: "a", expected_answer: null, context: null, pass_threshold: 70 })).rejects.toThrow("The evaluator could not complete");
  });
  it("rejects malformed success responses without fabricating scores", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ quality_score: 99 })));
    await expect(api.benchmark()).rejects.toEqual(new ReviewError("invalid_response"));
  });
  it("reports network errors safely", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("private host at C:/config")));
    await expect(api.connect()).rejects.toEqual(new ReviewError("backend_unavailable"));
  });
});
