"use client";
import { useEffect, useState } from "react";
import { api } from "./api";
import { ReviewError } from "./errors";

export function useReadiness() {
  const [state, setState] = useState<"warming" | "ready" | "error" | "unavailable">("warming");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const result = await api.ready(controller.signal);
        if (controller.signal.aborted) return;
        setState(result.status);
        if (result.status !== "warming") return;
      } catch {
        if (controller.signal.aborted) return;
        setState("unavailable");
      }
      timer = setTimeout(poll, 2000);
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [attempt]);
  function retry() { setState("warming"); setAttempt(value => value + 1); }
  function onRequestError(error: unknown) {
    if (error instanceof ReviewError && ["evaluator_warming", "evaluator_unavailable", "backend_unavailable", "timeout"].includes(error.code)) retry();
  }
  return { state, retry, onRequestError };
}
