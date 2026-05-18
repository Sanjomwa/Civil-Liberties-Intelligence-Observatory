import pandas as pd

from streamlit.core.contracts import MartContractError, validate_dataframe_schema


def test_validate_dataframe_schema_accepts_matching_schema():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["a", "b", "c"],
            "value": [1.0, 2.5, 3.5],
        }
    )

    validate_dataframe_schema(
        df,
        required_columns=["id", "name", "value"],
        dtype_hints={"id": "numeric", "name": "string", "value": "numeric"},
        non_nullable=["id", "name"],
    )


def test_validate_dataframe_schema_rejects_missing_columns():
    df = pd.DataFrame({"id": [1], "value": [2.0]})

    try:
        validate_dataframe_schema(df, required_columns=[
                                  "id", "name"], title="test query")
    except MartContractError as exc:
        assert "missing required columns" in str(exc)
    else:
        raise AssertionError("Expected MartContractError")
