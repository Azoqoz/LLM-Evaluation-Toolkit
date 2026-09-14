"""Offline full-API RSS smoke test: python -m src.application.diagnose_onnx.

Uses an ephemeral loopback port, runs a benchmark and a maximum-length pair,
and prints diagnostics to the console only. No public diagnostic route.
"""

import importlib.abc
import json
import os
import socket
import sys
import threading
import time
import urllib.request


def main():
    os.environ["APP_MODE"] = "demo"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    class NoHeavy(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {"torch", "sentence_transformers", "transformers"}:
                raise AssertionError("Heavyweight import attempted in ONNX diagnostics")
    sys.meta_path.insert(0, NoHeavy())
    import psutil
    import uvicorn

    process = psutil.Process()
    peak = [process.memory_info().rss]
    stop = threading.Event()

    def sample():
        while not stop.wait(.005):
            peak[0] = max(peak[0], process.memory_info().rss)
    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config("src.api.app:app", host="127.0.0.1", port=port, access_log=False))
    runner = threading.Thread(target=server.run, daemon=True)
    started = time.monotonic()
    runner.start()
    base = f"http://127.0.0.1:{port}"

    def get(path):
        with urllib.request.urlopen(base + path, timeout=5) as response:
            return json.load(response)

    def post(path, payload=None):
        data = json.dumps(payload or {}).encode()
        request = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)

    try:
        while True:
            try:
                health = get("/health")
                break
            except OSError:
                if time.monotonic() - started > 30:
                    raise RuntimeError("API startup timeout")
                time.sleep(.05)
        initial = get("/ready")
        liveness_seconds = time.monotonic() - started
        while (ready := get("/ready"))["status"] == "warming":
            if time.monotonic() - started > 60:
                raise RuntimeError("Evaluator warmup timeout")
            time.sleep(.05)
        assert ready["status"] == "ready", ready
        warm_rss = process.memory_info().rss
        benchmark = post("/evaluate/benchmark")
        assert len(benchmark["rows"]) == 100
        post("/evaluate", {"question": "question " * 400, "answer": "answer " * 400})
        print(json.dumps({
            "platform": sys.platform, "health": health, "initial_readiness": initial,
            "health_seconds": round(liveness_seconds, 2),
            "warm_rss_mib": round(warm_rss / 1024**2, 2),
            "after_benchmark_and_long_pair_rss_mib": round(process.memory_info().rss / 1024**2, 2),
            "sampled_peak_rss_mib": round(peak[0] / 1024**2, 2),
            "benchmark_rows": len(benchmark["rows"]),
            "forbidden_imports": sorted({"torch", "sentence_transformers", "transformers"}.intersection(sys.modules)),
        }, indent=2), flush=True)
    finally:
        server.should_exit = True
        runner.join(timeout=10)
        stop.set()
        sampler.join(timeout=1)


if __name__ == "__main__":
    main()
