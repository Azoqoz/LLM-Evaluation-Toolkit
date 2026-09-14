"""Float32 pooling, tokenization, cosine and real embedding parity."""

import numpy as np
import pytest

from src.evaluators.onnx_embeddings import mean_pool_and_normalize
from src.evaluators.semantic import SentenceTransformerScorer

TEXTS = [
    "Hello world!", " hello   WORLD ", "ما هي سياسة الإرجاع؟", "Café — naïve résumé",
    "Returns are accepted within 14 days.", "The return period is two weeks.",
    "Backups happen every 12 hours.", "Backups happen every 24 hours.",
    "hello " * 400, "word " * 253 + " tail beyond cutoff " * 40, "", "a",
]


def test_attention_mask_mean_pooling_and_float32_normalization():
    hidden = np.array([[[3, 0], [0, 4], [999, 999]]], dtype=np.float32)
    result = mean_pool_and_normalize(hidden, np.array([[1, 1, 0]]))
    assert result.dtype == np.float32
    np.testing.assert_allclose(result, [[.6, .8]], atol=1e-7)


def test_all_masked_tokens_remain_finite_zero():
    result = mean_pool_and_normalize(np.ones((2, 3, 384), dtype=np.float32), np.zeros((2, 3)))
    assert np.isfinite(result).all()
    assert np.count_nonzero(result) == 0


def test_real_shape_normalization_and_embedding_parity(onnx_model, reference_model):
    actual = onnx_model.encode(TEXTS, normalize_embeddings=True)
    expected = reference_model.encode(TEXTS, normalize_embeddings=True)
    assert actual.shape == (len(TEXTS), 384)
    assert actual.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(actual, axis=1), 1, atol=2e-7)
    np.testing.assert_allclose(actual, expected, atol=2e-6, rtol=2e-5)


def test_same_tokenizer_padding_special_tokens_and_truncation(onnx_model, reference_model):
    assert onnx_model.max_seq_length == reference_model.max_seq_length == 256
    actual = onnx_model.tokenize(TEXTS)
    expected = reference_model.tokenize(TEXTS)
    assert actual["input_ids"].shape == (len(TEXTS), 256)
    for name, values in actual.items():
        np.testing.assert_array_equal(values, expected[name].numpy())
    np.testing.assert_array_equal(
        onnx_model.tokenize(["hello " * 400])["input_ids"],
        onnx_model.tokenize(["hello " * 254])["input_ids"],
    )


@pytest.mark.parametrize("left,right", list(zip(TEXTS[::2], TEXTS[1::2])))
def test_raw_cosine_and_current_rounded_similarity(onnx_model, reference_model, left, right):
    a = onnx_model.encode([left, right], normalize_embeddings=True).astype(float)
    b = reference_model.encode([left, right], normalize_embeddings=True).astype(float)
    assert abs(np.dot(a[0], a[1]) - np.dot(b[0], b[1])) <= 2e-6
    assert SentenceTransformerScorer(model=onnx_model).similarity(left, right) == SentenceTransformerScorer(model=reference_model).similarity(left, right)


def test_empty_collection_shape(onnx_model):
    assert onnx_model.encode([]).shape == (0, 384)
