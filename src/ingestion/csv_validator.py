"""CSV schema and row validation."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import pandas as pd

from src.config.settings import INPUT_COLUMNS, REQUIRED_COLUMNS


def read_csv_bytes(content: bytes) -> pd.DataFrame:
    """Read uploaded CSV bytes while preserving literal placeholder strings."""

    return pd.read_csv(io.BytesIO(content), keep_default_na=False)


@dataclass
class CsvValidationResult:
    """Validation summary plus safe valid and invalid row subsets."""

    total_rows: int
    valid_rows: int
    invalid_rows: int
    missing_required_columns: list[str] = field(default_factory=list)
    empty_required_values: int = 0
    duplicate_rows: int = 0
    valid_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    invalid_data: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def can_evaluate(self) -> bool:
        """Whether at least one valid row is available."""

        return not self.missing_required_columns and self.valid_rows > 0


def validate_dataframe(data: pd.DataFrame) -> CsvValidationResult:
    """Validate schema and rows without raising on user data problems."""

    frame = data.copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    total_rows = len(frame)
    if missing:
        invalid = frame.copy()
        invalid["_validation_error"] = "Missing required column(s): " + ", ".join(missing)
        return CsvValidationResult(
            total_rows=total_rows,
            valid_rows=0,
            invalid_rows=total_rows,
            missing_required_columns=missing,
            invalid_data=invalid,
        )

    empty_masks = {
        column: frame[column].isna() | frame[column].astype(str).str.strip().eq("")
        for column in REQUIRED_COLUMNS
    }
    empty_row_mask = empty_masks["question"] | empty_masks["answer"]
    comparable = [column for column in INPUT_COLUMNS if column in frame.columns and column != "id"]
    normalized = frame[comparable].fillna("").astype(str).apply(
        lambda series: series.str.strip().str.lower()
    )
    duplicate_mask = normalized.duplicated(keep="first")
    invalid_mask = empty_row_mask | duplicate_mask

    invalid = frame.loc[invalid_mask].copy()
    reasons: list[str] = []
    for index in invalid.index:
        row_reasons = []
        missing_values = [
            column for column, mask in empty_masks.items() if bool(mask.loc[index])
        ]
        if missing_values:
            row_reasons.append("Empty required value(s): " + ", ".join(missing_values))
        if bool(duplicate_mask.loc[index]):
            row_reasons.append("Duplicate row")
        reasons.append("; ".join(row_reasons))
    if not invalid.empty:
        invalid["_validation_error"] = reasons

    valid = frame.loc[~invalid_mask].copy()
    return CsvValidationResult(
        total_rows=total_rows,
        valid_rows=len(valid),
        invalid_rows=len(invalid),
        empty_required_values=int(sum(mask.sum() for mask in empty_masks.values())),
        duplicate_rows=int(duplicate_mask.sum()),
        valid_data=valid,
        invalid_data=invalid,
    )
