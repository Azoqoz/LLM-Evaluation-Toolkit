"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { safeError } from "@/lib/errors";
import { type EvaluationInput, type EvaluationResult } from "@/lib/contracts";
import { ReviewResult } from "./review-result";

export function SingleReview({ threshold, ready, onRequestError }: { threshold: number; ready: boolean; onRequestError: (error: unknown) => void }) {
  const [fields, setFields] = useState({ question: "", answer: "", expected_answer: "", context: "" });
  const [review, setReview] = useState<{ result: EvaluationResult; input: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sheetNumber, setSheetNumber] = useState(1);
  const abort = useRef<AbortController | null>(null);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const formHeading = useRef<HTMLHeadingElement>(null);
  useEffect(() => () => abort.current?.abort(), []);
  const input: EvaluationInput = { ...fields, pass_threshold: threshold };
  const stale = review && review.input !== JSON.stringify(input);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !ready) return;
    if (!fields.question.trim() || !fields.answer.trim()) { setError("Add a question and a model response to begin your review."); return; }
    const controller = new AbortController(); abort.current = controller;
    setBusy(true); setError(""); setReview(null);
    try {
      const result = await api.evaluate(input, controller.signal);
      setReview({ result, input: JSON.stringify(input) });
      resultHeading.current?.focus({ preventScroll: true });
      if (window.matchMedia?.("(max-width: 760px)").matches) resultHeading.current?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    } catch (error) { if (!controller.signal.aborted) { setError(safeError(error)); onRequestError(error); } }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  const update = (key: keyof typeof fields, value: string) => setFields(current => ({ ...current, [key]: value }));
  return <div className={`single-paper-desk ${review ? "has-marking" : ""}`}>
    <form className="paper response-sheet" onSubmit={submit} aria-label="Single response review">
      <header className="response-title"><div><p className="document-kicker">Original submission</p><h2 tabIndex={-1} ref={formHeading}>Response<br />sheet.</h2></div><div className="submission-number"><span>REVIEW No.</span><b>{String(sheetNumber).padStart(3, "0")}</b></div></header>
      <fieldset disabled={busy}>
        <label className="document-field question-entry"><span><b>01</b>Question</span><textarea aria-label="Question" required rows={2} value={fields.question} onChange={e => update("question", e.target.value)} placeholder="What was the model asked?" /></label>
        <label className="document-field response-entry"><span><b>02</b>Model response <i>the text under review</i></span><textarea aria-label="Model response" required rows={8} value={fields.answer} onChange={e => update("answer", e.target.value)} placeholder="Write or paste the response here. Give it room to speak for itself." /></label>
        <details className="reference-fold"><summary><span>Reference material</span><small>03 / optional</small></summary><div className="reference-entries"><label className="document-field"><span>Expected answer</span><textarea aria-label="Expected answer" rows={3} value={fields.expected_answer} onChange={e => update("expected_answer", e.target.value)} placeholder="The answer to compare against." /></label><label className="document-field"><span>Context</span><textarea aria-label="Context" rows={3} value={fields.context} onChange={e => update("context", e.target.value)} placeholder="Supporting evidence or source material." /></label></div><p className="pencil-note">No reference? That dimension remains N/A.</p></details>
        <div className="submission-footer"><div><p className="handwritten">Ready for a second look?</p><button type="button" className="margin-link" onClick={() => { setFields({ question: "", answer: "", expected_answer: "", context: "" }); setReview(null); setError(""); setSheetNumber(current => current + 1); }}>Clear sheet</button></div><button className="stamp-control" type="submit" disabled={!ready || busy}><span aria-hidden>FOR REVIEW</span><b>{busy ? "Review in progress" : "Evaluate response"}</b><small aria-hidden>{busy ? "MARKING…" : "EVALROOM"}</small></button></div>
      </fieldset>
      {error && <div className="correction-note" role="alert"><strong>Review needs attention</strong><p>{error}</p></div>}
      {busy && <p className="pencil-note pending-note" role="status"><span className="ink-loader" />Comparing your response with the available evidence. Your marking sheet will appear when the review is complete.</p>}
      <span className="page-number">SUBMISSION / {String(sheetNumber).padStart(3, "0")}</span>
    </form>
    <div className="marking-place"><h2 ref={resultHeading} tabIndex={-1} className="visually-hidden sheet-anchor">Review findings</h2>
      {review ? <>{stale && <p className="correction-note" role="status">This assessment belongs to the previous submission. Evaluate again to review your changes.</p>}<ReviewResult result={review.result} /><button className="margin-link back-to-sheet" onClick={() => { formHeading.current?.focus(); formHeading.current?.scrollIntoView({ block: "start", behavior: "auto" }); }}>Turn back to the response sheet</button></> : <aside className="desk-memorandum"><span className="paperclip" aria-hidden /><span className="document-kicker">A note before you begin</span><h3>{busy ? "A review is taking shape." : "Good answers can stand a little scrutiny."}</h3><p className="handwritten">{busy ? "The marking sheet will arrive here when the evaluator finishes." : "Add the question, the response, and any evidence. We’ll put the assessment on a separate sheet."}</p><div className="memorandum-bottom"><span>Pass standard</span><b>{threshold}<small>/100</small></b></div></aside>}
    </div>
  </div>;
}
