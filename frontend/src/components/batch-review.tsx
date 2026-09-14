"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { safeError } from "@/lib/errors";
import { displayText, formatScore, metricKeys, type BatchResult, type Capabilities, type ReviewRow } from "@/lib/contracts";
import { DimensionRails, Dossier } from "./review-result";
import { ReviewWall } from "./review-wall";

function ScoreDistribution({ rows }: { rows: ReviewRow[] }) {
  const bins = [0, 20, 40, 60, 80].map((start, index) => ({ label: `${start}–${index === 4 ? 100 : start + 19}`, count: rows.filter(row => row.quality_score != null && row.quality_score >= start && (index === 4 ? row.quality_score <= 100 : row.quality_score < start + 20)).length }));
  const max = Math.max(1, ...bins.map(bin => bin.count));
  return <figure className="pencil-histogram"><figcaption className="document-kicker">Score distribution</figcaption><div>{bins.map(bin => <div className="distribution-bin" key={bin.label}><span>{bin.count}</span><div><i style={{ height: `${bin.count / max * 100}%` }} /></div><span>{bin.label}</span></div>)}</div></figure>;
}

export function BatchReport({ result }: { result: BatchResult }) {
  const [status, setStatus] = useState("All");
  const [finding, setFinding] = useState("All");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("original");
  const [selected, setSelected] = useState<number | null>(null);
  const [exported, setExported] = useState(false);
  const dossierHeading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (selected == null) return;
    dossierHeading.current?.focus({ preventScroll: true });
    dossierHeading.current?.scrollIntoView?.({ block: "start", behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }, [selected]);
  function returnSheet() {
    if (selected != null) document.getElementById(`review-sheet-${selected}`)?.focus();
    setSelected(null);
  }
  const headings = useMemo(() => [...new Set(result.rows.map(row => row.error_type))].sort(), [result.rows]);
  const common = useMemo(() => {
    const counts = new Map<string, number>();
    result.rows.filter(row => row.error_type !== "No Error").forEach(row => counts.set(row.error_type, (counts.get(row.error_type) ?? 0) + 1));
    return [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  }, [result.rows]);
  const rows = useMemo(() => {
    const filtered = result.rows.map((row, index) => ({ row, index })).filter(({ row }) => (status === "All" || row.status === status) && (finding === "All" || row.error_type === finding) && `${row.id ?? ""} ${row.question ?? ""} ${row.answer ?? ""}`.toLowerCase().includes(query.toLowerCase()));
    if (sort !== "original") filtered.sort((a, b) => {
      if (a.row.quality_score == null) return b.row.quality_score == null ? a.index - b.index : 1;
      if (b.row.quality_score == null) return -1;
      return (sort === "high" ? b.row.quality_score - a.row.quality_score : a.row.quality_score - b.row.quality_score) || a.index - b.index;
    });
    return filtered;
  }, [result.rows, status, finding, query, sort]);
  function download() {
    const url = URL.createObjectURL(new Blob([result.evaluated_csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = "evalroom-reviewed-responses.csv";
    anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); setExported(true);
  }
  const select = (index: number) => setSelected(current => current === index ? null : index);
  const dimensions = Object.fromEntries(metricKeys.map(key => [key, result.summary[`average_${key}`]])) as Pick<ReviewRow, typeof metricKeys[number]>;
  if (!result.rows.length) return <div className="paper empty-paper" role="status"><p className="document-kicker">No assessments returned</p><h3>The review register is empty.</h3><p>No scores have been inferred. Check your dataset and run the review again.</p></div>;
  return <section className="collection-report" aria-label="Batch review results">
    <header className="collection-heading"><div><p className="document-kicker">Collection marked</p><h2>The results are in.</h2></div><button className="paper-tab" onClick={download}>Export reviewed CSV <span aria-hidden>↓</span></button></header>
    {exported && <p className="visually-hidden" role="status">CSV download prepared.</p>}
    <div className="wall-and-margin"><div className="wall-main"><ReviewWall rows={result.rows} selected={selected} onSelect={select} /></div><aside className="editorial-totals" aria-label="Collection summary"><p className="total-inscription"><strong>{result.summary.total}</strong><span>reviewed.</span></p><dl><div className="pass"><dt>Passed</dt><dd>{result.summary.passed}</dd></div><div className="fail"><dt>Failed</dt><dd>{result.summary.failed}</dd></div><div><dt>Pass rate</dt><dd>{formatScore(result.summary.pass_rate)}<small>%</small></dd></div></dl><div className="average-inscription"><span>Average quality</span><strong>{formatScore(result.summary.average_quality_score)}</strong><small>out of 100</small></div><p className="handwritten">The verdict belongs to the response. The pattern belongs to the collection.</p></aside></div>
    <div id="collection-dossier" className="dossier-slot">{selected != null && <><div className="pulled-heading"><h3 ref={dossierHeading} tabIndex={-1}>Sheet {String(selected + 1).padStart(3, "0")} / open for inspection</h3><button className="margin-link" onClick={returnSheet}>Return sheet to wall</button></div><Dossier key={selected} row={result.rows[selected]} index={selected} /></>}</div>
    <div className="collection-notes"><ScoreDistribution rows={result.rows} /><section className="findings-index"><h3 className="document-kicker">Index of common findings</h3>{common.length ? <ol>{common.map(([name, count]) => <li key={name}><span>{name}</span><strong>{count}</strong></li>)}</ol> : <p>No error categories were returned.</p>}</section></div>
    <details className="averages-insert"><summary>Dimension averages <span>available metrics only</span></summary><DimensionRails result={dimensions} /></details>
    <section className="paper utility-register"><header className="register-heading"><div><p className="document-kicker">Appendix / the detailed record</p><h3>Response register</h3></div><p>{rows.length} of {result.rows.length} responses</p></header>
      <div className="validation-notes"><span>Input rows <b>{result.validation.total_rows}</b></span><span>Evaluated <b>{result.validation.valid_rows}</b></span><span>Excluded <b>{result.validation.invalid_rows}</b></span><span>Duplicates <b>{result.validation.duplicate_rows}</b></span><span>Empty required cells <b>{result.validation.empty_required_values}</b></span></div>
      {result.invalid_rows.length > 0 && <details className="excluded-insert"><summary>Review {result.invalid_rows.length} excluded rows</summary><div className="table-scroll"><table><caption className="visually-hidden">Excluded source rows</caption><thead><tr><th>Question</th><th>Response</th><th>Validation finding</th></tr></thead><tbody>{result.invalid_rows.map((row, index) => <tr key={index}><td>{displayText(row.question)}</td><td>{displayText(row.answer)}</td><td>{displayText(row._validation_error)}</td></tr>)}</tbody></table></div></details>}
      <div className="register-filters"><label>Find a response<input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search question, response or ID" /></label><label>Verdict<select value={status} onChange={e => setStatus(e.target.value)}><option>All</option><option>Pass</option><option>Fail</option></select></label><label>Primary finding<select value={finding} onChange={e => setFinding(e.target.value)}><option>All</option>{headings.map(name => <option key={name}>{name}</option>)}</select></label><label>Order<select value={sort} onChange={e => setSort(e.target.value)}><option value="original">Original order</option><option value="low">Lowest quality first</option><option value="high">Highest quality first</option></select></label></div>
      {rows.length ? <div className="table-scroll register-scroll" tabIndex={0} aria-label="Scrollable response register"><table><caption className="visually-hidden">Evaluated responses. Open a question to inspect its review dossier.</caption><thead><tr><th scope="col">ID</th><th scope="col">Question / open dossier</th><th scope="col">Quality</th><th scope="col">Verdict</th><th scope="col">Primary finding</th></tr></thead><tbody>{rows.map(({ row, index }) => <tr key={index} className={selected === index ? "selected-record" : ""}><td>{displayText(row.id ?? String(index + 1).padStart(3, "0"))}</td><td><button className="register-open" aria-expanded={selected === index} aria-controls="collection-dossier" onClick={() => { select(index); document.getElementById("collection-dossier")?.scrollIntoView?.({ block: "start", behavior: "auto" }); }}>{displayText(row.question)}</button></td><td>{formatScore(row.quality_score)}</td><td><span className={row.status.toLowerCase()}>{row.status.toUpperCase()}</span></td><td>{row.error_type}</td></tr>)}</tbody></table></div> : <div className="empty-paper" role="status"><h3>No responses match this view.</h3><button className="margin-link" onClick={() => { setStatus("All"); setFinding("All"); setQuery(""); }}>Clear filters</button></div>}
    </section>
  </section>;
}

export function BatchReview({ capabilities, threshold, ready, onRequestError }: { capabilities: Capabilities; threshold: number; ready: boolean; onRequestError: (error: unknown) => void }) {
  const demo = capabilities.app_mode === "demo";
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<BatchResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [completedThreshold, setCompletedThreshold] = useState<number | null>(null);
  const abort = useRef<AbortController | null>(null);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  useEffect(() => () => abort.current?.abort(), []);
  function selectFile(next: File | null) { setFile(next); setResult(null); setError(""); }
  async function run() {
    if (busy || !ready) return;
    if (!demo && !file) { setError("Choose a CSV to start a batch review."); return; }
    const controller = new AbortController(); abort.current = controller;
    setBusy(true); setError(""); setResult(null);
    try {
      const next = demo ? await api.benchmark(controller.signal) : await api.batch(file!, threshold, controller.signal);
      setResult(next); setCompletedThreshold(demo ? capabilities.demo_pass_threshold : threshold);
      resultHeading.current?.focus({ preventScroll: true });
    } catch (error) { if (!controller.signal.aborted) { setError(safeError(error)); onRequestError(error); } }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <div className="collection-desk">
    {demo ? <section className="benchmark-invitation" aria-label="Demo Benchmark"><div><p className="document-kicker">Fixed collection / {capabilities.benchmark.id}</p><h2>{capabilities.benchmark.title}</h2><p>Twenty scenarios, five kinds of response.<br />A hundred sheets ready for an honest mark.</p><span className="pencil-note">Fixed threshold {capabilities.demo_pass_threshold}. CSV upload is available in Local Mode.</span></div><button className="stamp-control benchmark-stamp" onClick={run} disabled={busy || !ready}><span aria-hidden>COLLECTION REVIEW</span><b>{busy ? "Reviewing 100 responses" : "Run 100-response benchmark"}</b><small aria-hidden>EVALROOM / 100</small></button></section> : <section className="paper intake-sheet"><header className="document-heading"><p className="document-kicker">Collection intake</p><span className="paper-index">CSV / LOCAL</span></header><div className="intake-body"><div><h2>Bring the<br />whole file.</h2><p>A CSV with <code>question</code> and <code>answer</code>. Optional references and extra columns stay with the original rows.</p><a className="margin-link" href="/input-template.csv" download>Download a sample CSV ↓</a></div><div className="file-pocket" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (!busy) selectFile(e.dataTransfer.files[0] ?? null); }}><label className="file-picker" htmlFor="csv-file"><input className="visually-hidden" ref={fileInput} id="csv-file" aria-label="Upload CSV" aria-describedby="csv-file-hint" type="file" accept=".csv,text/csv" disabled={busy} onChange={e => selectFile(e.target.files?.[0] ?? null)} /><span className="file-title">{file ? file.name : "Slip a CSV into the folder"}</span><span className="file-hint" id="csv-file-hint" aria-live="polite">{file ? `${new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(file.size / 1024)} KB · Ready to review` : "Choose a CSV or drop it into this folder."}</span><span className="file-action">{file ? "Choose a different file" : "Choose a CSV"} <span aria-hidden>↗</span></span></label><button className="paper-tab" disabled={busy || !file || !ready} onClick={run}>{busy ? "Reviewing your responses" : "Evaluate CSV"}</button>{file && <button className="margin-link" disabled={busy} onClick={() => { selectFile(null); if (fileInput.current) fileInput.current.value = ""; }}>Remove file</button>}</div></div></section>}
    {error && <div className="correction-note" role="alert"><strong>Batch review needs attention</strong><p>{error}</p></div>}
    {busy && <div className="processing-slip" role="status"><span className="ink-loader" /><div><h3>Reading. Comparing. Reviewing.</h3><p>The collection is with the evaluator. Keep this desk open while the responses are reviewed.</p></div></div>}
    <h2 className="visually-hidden sheet-anchor" ref={resultHeading} tabIndex={-1}>Batch findings</h2>
    {result ? <>{!demo && completedThreshold !== threshold && <p className="correction-note">This register was evaluated at threshold {completedThreshold}. Run the batch again to apply threshold {threshold}.</p>}<BatchReport key={JSON.stringify([result.rows[0]?.evaluated_at, completedThreshold])} result={result} /></> : demo && <ReviewWall count={capabilities.benchmark.row_count} />}
  </div>;
}
