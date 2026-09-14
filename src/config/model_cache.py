"""One app-relative artifact shared by build prefetch and runtime loading."""

from pathlib import Path

MODEL_CACHE_PATH = Path(__file__).resolve().parents[2] / ".model-cache" / "all-MiniLM-L6-v2"
