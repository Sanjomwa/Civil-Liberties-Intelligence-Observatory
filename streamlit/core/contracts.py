from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

import pandas as pd
from pandas.api.types import (
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
    is_string_dtype,
)


class MartContractError(Exception):
    pass


def _normalize_expected_type(expected: str) -> str:
    return expected.strip().lower()


def _is_expected_dtype(series: pd.Series, expected: str) -> bool:
    expected = _normalize_expected_type(expected)

    if expected == "numeric":
        return is_numeric_dtype(series)

    if expected in ("datetime", "date"):
        if is_datetime64_any_dtype(series):
            return True
        if is_object_dtype(series):
            values = series.dropna()
            return values.empty or all(
                isinstance(value, (datetime, date)) for value in values
            )
        return False

    if expected == "string":
        return is_string_dtype(series) or is_object_dtype(series)

    if expected == "any":
        return True

    return False


def validate_dataframe_schema(
    df: pd.DataFrame,
    required_columns: list[str],
    dtype_hints: dict[str, str] | None = None,
    non_nullable: list[str] | None = None,
    title: str = "mart query",
) -> None:
    missing_columns = [
        col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise MartContractError(
            f"{title} is missing required columns: {', '.join(missing_columns)}"
        )

    if dtype_hints:
        invalid_types: list[str] = []
        for column, expected in dtype_hints.items():
            if column not in df.columns:
                continue
            if not _is_expected_dtype(df[column], expected):
                invalid_types.append(f"{column} expected {expected}")

        if invalid_types:
            raise MartContractError(
                f"{title} has dtype mismatches: {', '.join(invalid_types)}"
            )

    if non_nullable:
        null_columns = [
            column
            for column in non_nullable
            if column in df.columns and df[column].isna().any()
        ]
        if null_columns:
            raise MartContractError(
                f"{title} contains null values in required columns: {', '.join(null_columns)}"
            )


def guard_dataframe_schema(
    df: pd.DataFrame,
    required_columns: list[str],
    dtype_hints: dict[str, str] | None = None,
    non_nullable: list[str] | None = None,
    title: str = "mart query",
    warn_fn: Callable[[str], Any] | None = None,
) -> pd.DataFrame:
    if warn_fn is None:
        try:
            import streamlit as st

            warn_fn = st.warning
        except Exception:  # pragma: no cover
            warn_fn = print

    try:
        validate_dataframe_schema(
            df,
            required_columns=required_columns,
            dtype_hints=dtype_hints,
            non_nullable=non_nullable,
            title=title,
        )

    except MartContractError as error:
        warn_fn(str(error))
        return pd.DataFrame()

    return df
