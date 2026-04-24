import pandas as pd

from backend.indicators import preparar_indicadores


def test_preparar_indicadores_adds_expected_columns():
    rows = 100
    df = pd.DataFrame(
        {
            "Open": [100 + i * 0.1 for i in range(rows)],
            "High": [101 + i * 0.1 for i in range(rows)],
            "Low": [99 + i * 0.1 for i in range(rows)],
            "Close": [100 + i * 0.1 for i in range(rows)],
            "Volume": [1000 + i for i in range(rows)],
        }
    )
    result = preparar_indicadores(df)
    for col in ["EMA20", "EMA50", "RET_5D", "RET_20D", "HIGH20", "LOW20", "RSI14"]:
        assert col in result.columns
    assert not result.empty
