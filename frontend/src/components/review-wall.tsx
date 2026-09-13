"use client";
import { formatScore, type ReviewRow } from "@/lib/contracts";

interface ReviewWallProps {
  rows?: ReviewRow[];
  count?: number;
  selected?: number | null;
  onSelect?: (index: number) => void;
}

export function ReviewWall({ rows, count = 100, selected, onSelect }: ReviewWallProps) {
  const length = rows ? rows.length : count;
  return <section className="contact-sheet" aria-label="Response review wall">
    <header className="wall-caption"><div><span className="document-kicker">Contact sheet</span><h3>{rows ? "Every response leaves a mark." : "A place for every response."}</h3></div><p>{rows ? "Pull a numbered sheet to read the review." : "Unmarked until the real review is complete."}</p></header>
    <ol className="review-wall">{Array.from({ length }, (_, index) => {
      const row = rows?.[index];
      const number = String(index + 1).padStart(index < 99 ? 2 : 3, "0");
      const id = row?.id == null ? number : String(row.id);
      return <li key={index}><button id={`review-sheet-${index}`} type="button" className={`wall-sheet ${row?.status.toLowerCase() ?? "unmarked"} ${selected === index ? "pulled" : ""}`} disabled={!row} aria-label={row ? `Open review ${id}, ${row.status}, quality ${formatScore(row.quality_score)}` : `Response ${number}, not yet reviewed`} aria-expanded={row ? selected === index : undefined} aria-controls={row ? "collection-dossier" : undefined} onClick={() => onSelect?.(index)}><span className="tile-number">{number}</span><span className="tile-status">{row ? row.status.toUpperCase() : "—"}</span><span className="tile-id">{row ? id : "TO REVIEW"}</span><span className="tile-grade"><span className="tile-strokes" aria-hidden>{Array.from({ length: 5 }, (_, mark) => <i key={mark} className={row?.quality_score != null && row.quality_score >= (mark + 1) * 20 ? "inked" : ""} />)}</span><span>{row ? formatScore(row.quality_score) : ""}</span></span></button></li>;
    })}</ol>
    <p className="wall-legend">{rows ? <><span className="pass">✓ Pass</span><span className="fail">× Fail</span><span>Five strokes represent the 0–100 quality scale. Open a sheet for exact findings.</span></> : <span className="handwritten">No grades yet. Just a hundred questions worth asking.</span>}</p>
  </section>;
}
