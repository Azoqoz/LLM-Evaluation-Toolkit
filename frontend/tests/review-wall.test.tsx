import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { ReviewWall } from "@/components/review-wall";
import { BatchReport } from "@/components/batch-review";
import { ReviewResult } from "@/components/review-result";
import { batch, result } from "./fixtures";

it("reserves exactly 100 numbered sheets without fabricating pending grades", () => {
  render(<ReviewWall />);
  const wall = screen.getByRole("region", { name: "Response review wall" });
  const sheets = within(wall).getAllByRole("button");
  expect(sheets).toHaveLength(100);
  expect(sheets[0]).toHaveAccessibleName("Response 01, not yet reviewed");
  expect(sheets[99]).toHaveAccessibleName("Response 100, not yet reviewed");
  for (const sheet of sheets) {
    expect(sheet).toBeDisabled();
    expect(sheet).not.toHaveAttribute("aria-expanded");
    expect(sheet.querySelector(".tile-grade")).toHaveTextContent("");
    expect(sheet.querySelector(".inked")).toBeNull();
  }
  expect(within(wall).queryByText(/^(PASS|FAIL)$/)).not.toBeInTheDocument();
});

it("uses returned verdicts and nullable quality even when the number suggests a different verdict", () => {
  const rows = [
    { ...batch.rows[0], quality_score: 100, status: "Fail" as const },
    { ...batch.rows[1], quality_score: null },
  ];
  render(<ReviewWall rows={rows} />);
  const high = screen.getByRole("button", { name: "Open review ER-001, Fail, quality 100" });
  expect(high.querySelectorAll(".inked")).toHaveLength(5);
  expect(high).toHaveClass("fail");
  const missing = screen.getByRole("button", { name: "Open review ER-002, Fail, quality N/A" });
  expect(within(missing).getByText("N/A")).toBeInTheDocument();
  expect(missing.querySelectorAll(".inked")).toHaveLength(0);
});

it("opens the hundredth review as one inline dossier and returns keyboard focus to its sheet", async () => {
  const user = userEvent.setup();
  const rows = Array.from({ length: 100 }, (_, index) => ({
    ...batch.rows[index % 2], id: `ER-${String(index + 1).padStart(3, "0")}`,
  }));
  render(<BatchReport result={{ ...batch, rows, summary: { ...batch.summary, total: 100, passed: 50, failed: 50 } }} />);
  const wall = screen.getByRole("region", { name: "Response review wall" });
  expect(within(wall).getAllByRole("button")).toHaveLength(100);
  const lastSheet = within(wall).getByRole("button", { name: "Open review ER-100, Fail, quality 37" });
  lastSheet.focus();
  await user.keyboard("{Enter}");
  const dossier = screen.getByRole("region", { name: "Review dossier ER-100" });
  expect(within(dossier).getByText(batch.rows[1].improvement_feedback)).toBeInTheDocument();
  expect(within(dossier).getByText("REJECTED")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Sheet 100 / open for inspection" })).toHaveFocus();
  expect(lastSheet).toHaveAttribute("aria-expanded", "true");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Return sheet to wall" }));
  expect(screen.queryByRole("region", { name: "Review dossier ER-100" })).not.toBeInTheDocument();
  expect(lastSheet).toHaveFocus();
  expect(lastSheet).toHaveAttribute("aria-expanded", "false");
});

it("keeps the whole collection wall and original dossier identity when the utility register is filtered", async () => {
  const user = userEvent.setup();
  render(<BatchReport result={batch} />);
  await user.selectOptions(screen.getByLabelText("Verdict"), "Fail");
  const wall = screen.getByRole("region", { name: "Response review wall" });
  expect(within(wall).getAllByRole("button")).toHaveLength(2);
  expect(within(screen.getByRole("table", { name: /Evaluated responses/ })).getAllByRole("row")).toHaveLength(2);
  await user.click(within(wall).getByRole("button", { name: "Open review ER-001, Pass, quality 80" }));
  expect(screen.getByRole("region", { name: "Review dossier ER-001" })).toBeInTheDocument();
});

it.each([
  ["Pass", "APPROVED"],
  ["Fail", "REJECTED"],
] as const)("stamps %s without rewriting findings or treating unavailable dimensions as zero", (status, stamp) => {
  render(<ReviewResult result={{ ...result, status }} />);
  expect(screen.getByText(stamp)).toBeInTheDocument();
  expect(screen.getByText(result.error_type)).toBeInTheDocument();
  expect(screen.getByText(result.improvement_feedback)).toBeInTheDocument();
  const dimensions = screen.getByLabelText("Scoring dimensions");
  for (const entry of dimensions.querySelectorAll(".grading-entry")) {
    if (entry.textContent?.includes("N/A")) expect(entry.querySelectorAll(".marked")).toHaveLength(0);
  }
  expect(screen.getAllByText("N/A")).toHaveLength(2);
});
