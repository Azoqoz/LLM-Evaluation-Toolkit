"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { type Capabilities } from "@/lib/contracts";
import { safeError } from "@/lib/errors";
import { SingleReview } from "./single-review";
import { BatchReview } from "./batch-review";
import { Method } from "./method";
import { useReadiness } from "@/lib/use-readiness";

type Workspace = "single" | "batch" | "method";
function ConnectedDesk({ capabilities, workspace }: { capabilities: Capabilities; workspace: Workspace }) {
  const readiness = useReadiness();
  const ready = readiness.state === "ready";
  const [threshold, setThreshold] = useState(capabilities.app_mode === "demo" ? capabilities.demo_pass_threshold : capabilities.configuration.default_pass_threshold);
  const [thresholdText, setThresholdText] = useState(String(threshold));
  const range = capabilities.configuration.pass_threshold;
  const valid = thresholdText.trim() !== "" && Number.isFinite(Number(thresholdText)) && Number(thresholdText) >= range.minimum && Number(thresholdText) <= range.maximum;
  return <>
    <div className="desk-instruments">
      <p className="connection-caption" aria-live="polite"><span className={ready ? "ink-dot" : readiness.state === "warming" ? "ink-loader" : undefined} aria-hidden />{ready ? "Evaluator ready" : readiness.state === "warming" ? "API connected · Preparing evaluator..." : "Evaluator unavailable"} <span>{capabilities.evaluation_mode}</span></p>
      {capabilities.threshold_editable ? <label className="threshold-dial">Pass threshold<input aria-label="Pass threshold" type="number" min={range.minimum} max={range.maximum} step="any" value={thresholdText} aria-invalid={!valid} onChange={e => { const next = e.target.value; setThresholdText(next); if (next.trim() !== "" && Number.isFinite(Number(next)) && Number(next) >= range.minimum && Number(next) <= range.maximum) setThreshold(Number(next)); }} onBlur={() => { if (!valid) setThresholdText(String(threshold)); }} /><span>/100</span></label> : <p className="threshold-fixed">Review standard <strong>{threshold}</strong><span>/100 · fixed</span></p>}
    </div>
    {readiness.state === "error" && <div className="correction-note" role="alert"><p>Evaluator initialization failed. Check again after the service has restarted.</p><button className="margin-link" onClick={readiness.retry}>Check readiness again</button></div>}
    {readiness.state === "unavailable" && <p className="pencil-note" role="status">Reconnecting to the API. It may be waking up. Evaluation will be available when readiness is confirmed.</p>}
    {!valid && <p role="alert" className="pencil-warning">Enter a threshold between {range.minimum} and {range.maximum}. Reviews currently use {threshold}.</p>}
    <section hidden={workspace !== "single"} id="single-workspace" aria-label="Single Review"><SingleReview threshold={threshold} ready={ready} onRequestError={readiness.onRequestError} /></section>
    <section hidden={workspace !== "batch"} id="batch-workspace" aria-label="Batch Review"><BatchReview capabilities={capabilities} threshold={threshold} ready={ready} onRequestError={readiness.onRequestError} /></section>
    <section hidden={workspace !== "method"} id="method-workspace" aria-label="Method and scoring"><Method capabilities={capabilities} /></section>
  </>;
}

export function ReviewRoom() {
  const [workspace, setWorkspace] = useState<Workspace>("single");
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    api.connect(controller.signal).then(next => { if (!controller.signal.aborted) setCapabilities(next); }).catch(error => {
      if (!controller.signal.aborted) {
        setError(safeError(error));
        timer = setTimeout(() => setAttempt(current => current + 1), 2000);
      }
    });
    return () => { controller.abort(); clearTimeout(timer); };
  }, [attempt]);
  return <div className="paper-room">
    <a className="skip-link" href="#review-desk">Skip to review desk</a>
    <aside className="binder-spine" aria-label="EVALROOM binder">
      <Link className="binder-identity" href="/" aria-label="EVALROOM home"><span className="binder-seal" aria-hidden>er.</span><span>EVALROOM</span></Link>
      <nav className="binder-tabs" aria-label="Review workspaces">{([ ["single", "1", "Single", "Single Review"], ["batch", "2", "Batch", "Batch Review"], ["method", "3", "Method", "Method / Scoring"] ] as const).map(([id, number, label, name]) => <button key={id} className={workspace === id ? "selected-tab" : ""} aria-label={name} aria-current={workspace === id ? "page" : undefined} aria-controls={`${id}-workspace`} onClick={() => setWorkspace(id)}><span>{number}</span><b>{label}</b></button>)}</nav>
      <span className="binder-mode">{capabilities ? capabilities.app_mode === "demo" ? "PUBLIC DEMO" : "LOCAL MODE" : "CONNECTING"}</span>
      <span className="spine-footnote" aria-hidden>REVIEW FILE / VOL. 01</span>
    </aside>
    <main id="review-desk" className="open-desk">
      <header className="desk-caption"><div><p className="document-kicker">AI response review system</p><h1>{workspace === "single" ? "The evaluation desk." : workspace === "batch" ? "The response collection." : "Notes on the method."}</h1></div><span className="handwritten desk-note">{workspace === "single" ? "Read closely. Mark honestly." : workspace === "batch" ? "The whole picture, one sheet at a time." : "Keep the reasoning in the margin."}</span></header>
      {capabilities ? <ConnectedDesk capabilities={capabilities} workspace={workspace} /> : <section className="paper connection-paper" role={error ? "alert" : "status"}><span className="paper-index">INCOMING / 00</span><h2>{error ? "The evaluator is unavailable." : "Connecting to the evaluator."}</h2><p>{error || "Preparing your response sheets and checking the review standard."}</p>{error ? <button className="paper-tab" onClick={() => { setError(""); setAttempt(current => current + 1); }}>Reconnect</button> : <span className="ink-loader" aria-hidden />}</section>}
      <footer className="colophon"><span>Filed under: considered responses.</span><span>{capabilities ? `${capabilities.evaluation_mode} · v${capabilities.evaluator_version}` : "EVALROOM / AI response review"}</span></footer>
    </main>
  </div>;
}
