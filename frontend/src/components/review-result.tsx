import { displayText, formatScore, metricKeys, metricLabels, type EvaluationResult, type ReviewRow } from "@/lib/contracts";

export function DimensionRails({ result }: { result: Pick<EvaluationResult, typeof metricKeys[number]> }) {
  return <dl className="grading-annotations" aria-label="Scoring dimensions">{metricKeys.map(key => <div className="grading-entry" key={key}>
    <dt>{metricLabels[key]}</dt><dd><span className="grading-strokes" aria-hidden>{Array.from({ length: 10 }, (_, index) => <i className={result[key] != null && result[key]! >= (index + 1) * 10 ? "marked" : ""} key={index} />)}</span><span className="annotated-score">{formatScore(result[key])}</span></dd>
    {result[key] == null && <dd className="missing-annotation">{key === "correctness_score" ? "No expected answer supplied" : key === "groundedness_score" ? "No context supplied" : "Metric unavailable"}</dd>}
  </div>)}</dl>;
}

export function ReviewResult({ result, compact = false }: { result: EvaluationResult; compact?: boolean }) {
  return <article className={`paper marking-sheet ${compact ? "dossier-marking" : ""}`} aria-label="Evaluation result">
    <header className="document-heading"><p className="document-kicker">Marking sheet</p><span className="paper-index">REVIEWED</span></header>
    <div className="marked-outcome"><div className="grade"><span className="document-kicker">Quality score</span><strong>{formatScore(result.quality_score)}</strong><span className="grade-denominator">{result.quality_score == null ? "unavailable" : "out of 100"}</span></div><div className={`rubber-verdict ${result.status.toLowerCase()}`}><b>{result.status === "Pass" ? "APPROVED" : "REJECTED"}</b><span className="verdict-stamp">{result.status.toUpperCase()} · OFFLINE REVIEW</span></div></div>
    <section className="finding-annotation"><span className="annotation-number" aria-hidden>01</span><div><p className="document-kicker">Primary finding</p><h3>{result.error_type}</h3></div></section>
    <section className="review-note"><p className="document-kicker">Reviewer note</p><p>{result.improvement_feedback}</p><span className="annotation-signature" aria-hidden>noted.</span></section>
    <DimensionRails result={result} />
    <footer className="paper-footnote"><span>{result.evaluation_mode} · v{result.evaluator_version}</span><time dateTime={result.evaluated_at}>{result.evaluated_at.replace("T", " / ").replace("+00:00", " UTC")}</time></footer>
  </article>;
}

export function Dossier({ row, index }: { row: ReviewRow; index: number }) {
  const extra = Object.entries(row).filter(([key]) => !["id", "question", "answer", "expected_answer", "context", "quality_score", "status", "error_type", "improvement_feedback", "evaluation_mode", "evaluated_at", "evaluator_version", ...metricKeys].includes(key));
  return <section className="pulled-dossier" aria-label={`Review dossier ${displayText(row.id ?? index + 1)}`}>
    <div className="paper source-sheet"><header className="document-heading"><p className="document-kicker">Pulled from the collection</p><span className="paper-index">{displayText(row.id ?? index + 1)}</span></header><h3>{displayText(row.question)}</h3><p className="document-kicker">Model response</p><p className="document-response">{displayText(row.answer)}</p>
      <div className="reference-copy"><p className="document-kicker">Expected answer</p><p>{displayText(row.expected_answer)}</p><p className="document-kicker">Context</p><p>{displayText(row.context)}</p></div>
      {extra.length > 0 && <details className="source-fields"><summary>Additional source fields</summary><dl>{extra.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{displayText(value)}</dd></div>)}</dl></details>}
    </div><ReviewResult result={row} compact />
  </section>;
}
