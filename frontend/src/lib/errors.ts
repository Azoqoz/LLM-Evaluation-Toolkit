export const errorMessages: Record<string, string> = {
  invalid_request: "Check the required fields and threshold, then try again.",
  invalid_csv: "This file could not be read as UTF-8 CSV. Check its format and upload it again.",
  invalid_csv_schema: "The CSV column structure could not be validated. Check for conflicting column names.",
  missing_csv_columns: "Your CSV needs question and answer columns.",
  no_valid_rows: "No valid rows remain. Supply a question and response in at least one row.",
  demo_restricted: "This action is available in Local Mode. Public Demo uses the fixed benchmark and threshold.",
  evaluation_failed: "The evaluator could not complete this review. Please retry shortly.",
  evaluator_warming: "Preparing evaluator. Please wait until the evaluator is ready.",
  evaluator_unavailable: "Evaluator initialization failed. Please check readiness again shortly.",
  backend_unavailable: "The review service is unavailable. Check that the backend is running, then reconnect.",
  timeout: "This review took longer than the connection allows. The backend may still be processing it. Try again shortly.",
  invalid_response: "The review service returned an unexpected result. Reconnect and try again.",
  internal_error: "The review could not be completed. Please try again.",
  http_error: "The request could not be processed. Check your input and try again.",
};
export class ReviewError extends Error {
  constructor(public code: string) { super(errorMessages[code] ?? errorMessages.internal_error); }
}
export function safeError(error: unknown): string {
  return error instanceof ReviewError ? error.message : errorMessages.internal_error;
}
