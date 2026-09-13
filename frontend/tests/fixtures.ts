import type { BatchResult, Capabilities, EvaluationResult, ReviewRow } from "@/lib/contracts";

// Transport fixtures only. The shipped app has no mock evaluation path.
export const result: EvaluationResult = {
  relevance_score: 80, correctness_score: null, groundedness_score: null, completeness_score: 80,
  quality_score: 80, status: "Pass", error_type: "No Error",
  improvement_feedback: "The answer passed the available offline quality checks. Unavailable: correctness (no expected answer); groundedness estimate (no context). These local semantic and rule-based checks are estimates, not a guarantee of factual correctness.",
  evaluation_mode: "Offline Hybrid", evaluator_version: "1.3.0", evaluated_at: "2026-01-02T03:04:05+00:00",
};
export const capabilities: Capabilities = {
  app_name: "LLM Evaluation Toolkit", evaluation_mode: "Offline Hybrid", evaluator_version: "1.3.0",
  single_evaluation: true, batch_csv_evaluation: true, offline_first: true, model_download_on_cache_miss: true,
  app_mode: "local", csv_upload_allowed: true, threshold_editable: true, demo_pass_threshold: 70,
  benchmark: { id: "evalroom-100-v1", title: "Demo Benchmark", row_count: 100 },
  configuration: { default_pass_threshold: 70, model_name: "sentence-transformers/all-MiniLM-L6-v2", pass_threshold: { minimum: 0, maximum: 100, inclusive: true }, metric_weights: { correctness_score: .35, relevance_score: .25, groundedness_score: .25, completeness_score: .15 } },
  required_csv_columns: ["question", "answer"], optional_csv_columns: ["expected_answer", "context", "id"],
  result_columns: Object.keys(result), error_types: ["No Error", "Contradictory Answer"],
  nullable_metrics: ["correctness_score", "groundedness_score"],
};
export const demo: Capabilities = { ...capabilities, app_mode: "demo", csv_upload_allowed: false, threshold_editable: false };
export const rows: ReviewRow[] = [
  { id: "ER-001", question: "How long is the return period?", answer: "14 days", expected_answer: "14 days", context: "14 days", topic: "Returns", ...result },
  { id: "ER-002", question: "How often are backups created?", answer: "12 hours", expected_answer: "24 hours", context: "24 hours", ...result, quality_score: 37, status: "Fail", error_type: "Contradictory Answer", improvement_feedback: 'The answer uses "12 hours", while the expected answer uses "24 hours"; this is a duration conflict.' },
];
export const batch: BatchResult = {
  columns: Object.keys(rows[0]), rows,
  validation: { total_rows: 3, valid_rows: 2, invalid_rows: 1, empty_required_values: 1, duplicate_rows: 0, missing_required_columns: [], can_evaluate: true },
  invalid_rows: [{ question: "q", answer: "", _validation_error: "Empty required value(s): answer" }],
  summary: { total: 2, passed: 1, failed: 1, pass_rate: 50, fail_rate: 50, average_quality_score: 58.5, average_correctness_score: null, average_relevance_score: 80, average_groundedness_score: null, average_completeness_score: 80 },
  evaluated_csv: "id,question,answer,quality_score,status\nER-001,q,a,80,Pass\nER-002,q2,a2,37,Fail\n",
};
