"""CSV export helpers."""

from __future__ import annotations

import pandas as pd

from src.config.settings import EXPORT_COLUMNS


def prepare_export(results: pd.DataFrame) -> pd.DataFrame:
    """Return results with all required export columns in a stable order."""

    export = results.copy()
    for column in EXPORT_COLUMNS:
        if column not in export.columns:
            export[column] = pd.NA
    original_columns = [
        column for column in export.columns if column not in EXPORT_COLUMNS
    ]
    return export[original_columns + list(EXPORT_COLUMNS)]


def to_csv_bytes(results: pd.DataFrame) -> bytes:
    """Serialize evaluated results as UTF-8 CSV bytes."""

    return prepare_export(results).to_csv(index=False).encode("utf-8")
