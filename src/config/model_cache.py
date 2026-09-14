"""One app-relative artifact shared by build prefetch and runtime loading."""

from pathlib import Path

MODEL_CACHE_PATH = Path(__file__).resolve().parents[2] / ".model-cache" / "all-MiniLM-L6-v2"
ONNX_CACHE_PATH = MODEL_CACHE_PATH.with_name("all-MiniLM-L6-v2-onnx")
# Pin matching full-precision ONNX, tokenizer and configuration artifacts.
ONNX_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
ONNX_ARTIFACTS = (
    "onnx/model.onnx", "tokenizer.json", "tokenizer_config.json",
    "special_tokens_map.json", "vocab.txt", "sentence_bert_config.json",
    "config.json", "1_Pooling/config.json",
)
