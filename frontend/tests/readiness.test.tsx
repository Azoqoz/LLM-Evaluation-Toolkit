import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ReviewRoom } from "@/components/review-room";
import { api } from "@/lib/api";
import { ReviewError } from "@/lib/errors";
import { batch, capabilities, demo, result } from "./fixtures";

vi.mock("@/lib/api", () => ({ api: { connect: vi.fn(), ready: vi.fn(), evaluate: vi.fn(), batch: vi.fn(), benchmark: vi.fn() } }));
beforeEach(() => {
  vi.useFakeTimers();
  vi.resetAllMocks();
  vi.mocked(api.connect).mockResolvedValue(capabilities);
  vi.mocked(api.ready).mockResolvedValue({ status: "warming" });
  vi.mocked(api.evaluate).mockResolvedValue(result);
  vi.mocked(api.benchmark).mockResolvedValue(batch);
});
afterEach(() => { vi.useRealTimers(); });
async function openDesk() { await act(async () => { render(<ReviewRoom />); }); }
async function tick(ms = 2000) { await act(async () => { await vi.advanceTimersByTimeAsync(ms); }); }

it("disables single evaluation while warming, then enables it and stops polling", async () => {
  await openDesk();
  expect(screen.getByText("API connected · Preparing evaluator...")).toBeInTheDocument();
  const evaluate = screen.getByRole("button", { name: "Evaluate response" });
  expect(evaluate).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Question"), { target: { value: "q" } });
  fireEvent.change(screen.getByLabelText("Model response"), { target: { value: "a" } });
  fireEvent.submit(screen.getByRole("form", { name: "Single response review" }));
  expect(api.evaluate).not.toHaveBeenCalled();
  vi.mocked(api.ready).mockResolvedValue({ status: "ready" });
  await tick();
  expect(screen.getByText("Evaluator ready")).toBeInTheDocument();
  expect(evaluate).toBeEnabled();
  await tick(8000);
  expect(api.ready).toHaveBeenCalledTimes(2);
  await act(async () => { fireEvent.click(evaluate); });
  expect(api.evaluate).toHaveBeenCalledOnce();
});

it("gates the fixed demo benchmark until ready without exposing Local controls", async () => {
  vi.mocked(api.connect).mockResolvedValue(demo);
  await openDesk();
  fireEvent.click(screen.getByRole("button", { name: "Batch Review" }));
  const benchmark = screen.getByRole("button", { name: "Run 100-response benchmark" });
  expect(benchmark).toBeDisabled();
  fireEvent.click(benchmark);
  expect(api.benchmark).not.toHaveBeenCalled();
  expect(screen.queryByLabelText("Upload CSV")).not.toBeInTheDocument();
  vi.mocked(api.ready).mockResolvedValue({ status: "ready" });
  await tick();
  expect(benchmark).toBeEnabled();
});

it("keeps Local CSV evaluation disabled while allowing file preparation", async () => {
  await openDesk();
  fireEvent.click(screen.getByRole("button", { name: "Batch Review" }));
  const input = screen.getByLabelText("Upload CSV");
  expect(input).toBeEnabled();
  fireEvent.change(input, { target: { files: [new File(["question,answer\nq,a"], "file.csv")] } });
  const evaluate = screen.getByRole("button", { name: "Evaluate CSV" });
  expect(evaluate).toBeDisabled();
  vi.mocked(api.ready).mockResolvedValue({ status: "ready" });
  await tick();
  expect(evaluate).toBeEnabled();
});

it("stops on terminal initialization failure and offers a safe explicit recheck", async () => {
  vi.mocked(api.ready).mockResolvedValue({ status: "error", message: "Traceback C:/secret/model" });
  await openDesk();
  expect(screen.getByText("Evaluator unavailable")).toBeInTheDocument();
  expect(screen.getByRole("alert")).not.toHaveTextContent(/secret|Traceback/);
  expect(screen.getByRole("button", { name: "Evaluate response" })).toBeDisabled();
  await tick(8000);
  expect(api.ready).toHaveBeenCalledOnce();
  vi.mocked(api.ready).mockResolvedValue({ status: "ready" });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Check readiness again" })); });
  expect(screen.getByRole("button", { name: "Evaluate response" })).toBeEnabled();
});

it("recovers from a sleeping API and a transient readiness connection failure", async () => {
  vi.mocked(api.connect).mockRejectedValueOnce(new ReviewError("backend_unavailable"));
  vi.mocked(api.ready).mockRejectedValueOnce(new ReviewError("timeout")).mockResolvedValue({ status: "ready" });
  await openDesk();
  expect(screen.queryByRole("button", { name: "Evaluate response" })).not.toBeInTheDocument();
  await tick();
  expect(screen.getByRole("button", { name: "Evaluate response" })).toBeDisabled();
  expect(screen.getByText(/Reconnecting to the API/)).toBeInTheDocument();
  await tick();
  expect(screen.getByText("Evaluator ready")).toBeInTheDocument();
});

it("cancels polling on unmount", async () => {
  let unmount!: () => void;
  await act(async () => { unmount = render(<ReviewRoom />).unmount; });
  const signal = vi.mocked(api.ready).mock.calls[0][0];
  unmount();
  expect(signal?.aborted).toBe(true);
  await tick(8000);
  expect(api.ready).toHaveBeenCalledOnce();
});

it("rechecks readiness if a restarted backend rejects a previously enabled review", async () => {
  vi.mocked(api.ready).mockResolvedValueOnce({ status: "ready" });
  vi.mocked(api.evaluate).mockRejectedValue(new ReviewError("evaluator_warming"));
  await openDesk();
  fireEvent.change(screen.getByLabelText("Question"), { target: { value: "q" } });
  fireEvent.change(screen.getByLabelText("Model response"), { target: { value: "a" } });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Evaluate response" })); });
  expect(screen.getByRole("button", { name: "Evaluate response" })).toBeDisabled();
  expect(api.ready).toHaveBeenCalledTimes(2);
});
