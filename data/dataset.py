from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd


LABEL_MAP = {
    # canonical dataset labels
    "REAL": 0,
    "FAKE": 1,
    # common numeric exports (REAL->0, FAKE->1)
    "0": 0,
    "1": 1,
}


_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")
_MULTISPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """
    Minimal, reproducible normalization:
    - remove URLs
    - remove special characters
    - lowercase
    """
    if not isinstance(text, str):
        return ""
    x = text.strip()
    x = _URL_RE.sub(" ", x)
    x = x.lower()
    x = _NON_ALNUM_RE.sub(" ", x)
    x = _MULTISPACE_RE.sub(" ", x).strip()
    return x


@dataclass(frozen=True)
class DatasetStats:
    n_rows: int
    n_null_text: int
    n_null_label: int
    class_counts: dict
    class_ratio: dict


def _coerce_and_validate_columns(df: pd.DataFrame) -> pd.DataFrame:
    required = {"text", "label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}. Found: {list(df.columns)}")
    return df[["text", "label"]].copy()


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = _coerce_and_validate_columns(df)
    return df


def merge_datasets(csv_paths: Iterable[str], shuffle: bool = True, seed: int = 42) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for p in csv_paths:
        frames.append(load_csv(p))
    if not frames:
        raise ValueError("No CSV paths provided.")

    df = pd.concat(frames, ignore_index=True)
    if shuffle:
        df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df


def standardize_labels(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    # Handle label variations robustly (REAL/FAKE or 0/1), while avoiding silent failures.
    x["label"] = x["label"].astype(str).str.strip().str.upper()
    x["label"] = x["label"].map(LABEL_MAP)
    return x


def clean_and_filter(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()

    # Null checks
    x = x.dropna(subset=["text", "label"])

    # Clean text
    x["text"] = x["text"].map(clean_text)

    # Drop empties after cleaning
    x = x[x["text"].str.len() > 0]
    x = x[x["label"].isin([0, 1])]
    x = x.reset_index(drop=True)
    return x


def analyze_quality(df: pd.DataFrame) -> DatasetStats:
    n_rows = len(df)
    n_null_text = int(df["text"].isna().sum()) if "text" in df.columns else n_rows
    n_null_label = int(df["label"].isna().sum()) if "label" in df.columns else n_rows

    counts = df["label"].value_counts(dropna=False).to_dict() if "label" in df.columns else {}
    total = sum(v for v in counts.values() if isinstance(v, (int, np.integer, float)))
    ratio = {k: (float(v) / float(total) if total else 0.0) for k, v in counts.items()}

    return DatasetStats(
        n_rows=n_rows,
        n_null_text=n_null_text,
        n_null_label=n_null_label,
        class_counts=counts,
        class_ratio=ratio,
    )


def prepare_dataframe(
    csv_paths: List[str],
    shuffle: bool = True,
    seed: int = 42,
) -> Tuple[pd.DataFrame, DatasetStats]:
    """
    End-to-end dataset preparation:
    - merge (optional)
    - standardize labels (REAL->0, FAKE->1)
    - clean + drop null/empty
    - return stats
    """
    raw = merge_datasets(csv_paths, shuffle=shuffle, seed=seed)
    stats_before = analyze_quality(raw)
    df = standardize_labels(raw)
    df = clean_and_filter(df)
    stats_after = analyze_quality(df)

    # helpful: attach both sets of stats for logging
    combined = DatasetStats(
        n_rows=stats_after.n_rows,
        n_null_text=stats_before.n_null_text,
        n_null_label=stats_before.n_null_label,
        class_counts=stats_after.class_counts,
        class_ratio=stats_after.class_ratio,
    )
    return df, combined

