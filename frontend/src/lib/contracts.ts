import { z } from "zod";

export const metricKeys = ["correctness_score", "relevance_score", "groundedness_score", "completeness_score"] as const;
export type MetricKey = typeof metricKeys[number];
export const metricLabels: Record<MetricKey, string> = {
  correctness_score: "Correctness", relevance_score: "Relevance",
  groundedness_score: "Groundedness", completeness_score: "Completeness",
};
const score = z.number().nullable();
export const resultSchema = z.object({
  relevance_score: score, correctness_score: score, groundedness_score: score,
  completeness_score: score, quality_score: score,
  status: z.enum(["Pass", "Fail"]), error_type: z.string(),
  improvement_feedback: z.string(), evaluation_mode: z.string(),
  evaluated_at: z.string(), evaluator_version: z.string(),
});
export type EvaluationResult = z.infer<typeof resultSchema>;
const scalar = z.union([z.string(), z.number(), z.boolean(), z.null()]);
export const rowSchema = resultSchema.catchall(scalar);
export type ReviewRow = z.infer<typeof rowSchema>;
export const capabilitiesSchema = z.object({
  app_name: z.string(), evaluation_mode: z.string(), evaluator_version: z.string(),
  single_evaluation: z.boolean(), batch_csv_evaluation: z.boolean(),
  offline_first: z.boolean(), model_download_on_cache_miss: z.boolean(),
  app_mode: z.enum(["demo", "local"]), csv_upload_allowed: z.boolean(),
  threshold_editable: z.boolean(), demo_pass_threshold: z.number(),
  benchmark: z.object({ id: z.string(), title: z.string(), row_count: z.number() }),
  configuration: z.object({
    default_pass_threshold: z.number(), model_name: z.string(),
    pass_threshold: z.object({ minimum: z.number(), maximum: z.number(), inclusive: z.boolean() }),
    metric_weights: z.object({ correctness_score: z.number(), relevance_score: z.number(), groundedness_score: z.number(), completeness_score: z.number() }),
  }),
  required_csv_columns: z.array(z.string()), optional_csv_columns: z.array(z.string()),
  result_columns: z.array(z.string()), error_types: z.array(z.string()), nullable_metrics: z.array(z.string()),
});
export type Capabilities = z.infer<typeof capabilitiesSchema>;
export const batchSchema = z.object({
  columns: z.array(z.string()), rows: z.array(rowSchema),
  validation: z.object({ total_rows: z.number(), valid_rows: z.number(), invalid_rows: z.number(),
    empty_required_values: z.number(), duplicate_rows: z.number(), missing_required_columns: z.array(z.string()), can_evaluate: z.boolean() }),
  invalid_rows: z.array(z.record(z.string(), scalar)),
  summary: z.object({ total: z.number(), passed: z.number(), failed: z.number(), pass_rate: z.number(), fail_rate: z.number(),
    average_quality_score: score, average_correctness_score: score, average_relevance_score: score,
    average_groundedness_score: score, average_completeness_score: score }),
  evaluated_csv: z.string(),
});
export type BatchResult = z.infer<typeof batchSchema>;
export interface EvaluationInput {
  question: string; answer: string; expected_answer: string | null; context: string | null; pass_threshold: number;
}

export function formatScore(value: number | null | undefined): string {
  return value == null ? "N/A" : new Intl.NumberFormat("en", { maximumFractionDigits: 2 }).format(value);
}
export function displayText(value: unknown): string {
  return value == null || String(value).trim() === "" ? "Not supplied" : String(value);
}
