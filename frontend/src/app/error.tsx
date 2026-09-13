"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <main className="paper recovery-sheet"><p className="document-kicker">EVALROOM / REVIEW INTERRUPTED</p><h1>Let’s reopen the desk.</h1><p>This page could not complete its last action. Reconnect to the review service and try again.</p><button className="paper-tab" onClick={reset}>Try again <span aria-hidden>↗</span></button></main>;
}
