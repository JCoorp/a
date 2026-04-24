import pandas as pd

from backend.consensus_engine import build_consensus
from backend.models import Asset, Snapshot
from backend.stock_scanner import evaluate_asset


def test_evaluate_asset_returns_signal_for_clean_uptrend():
    rows = 110
    df = pd.DataFrame(
        {
            "Open": [100 + i * 0.5 for i in range(rows)],
            "High": [101 + i * 0.5 for i in range(rows)],
            "Low": [99 + i * 0.5 for i in range(rows)],
            "Close": [100 + i * 0.5 for i in range(rows)],
            "Volume": [1000 + i * 5 for i in range(rows)],
        }
    )
    asset = Asset("TEST", "Test Inc.", "USA", "Technology", "equity", "Nasdaq", "yes", "momentum")
    consensus = build_consensus(
        [
            Snapshot("a", "TEST", 154.5, 1000, "USD", "t", True),
            Snapshot("b", "TEST", 154.6, 1000, "USD", "t", True),
            Snapshot("c", "TEST", 154.4, 1000, "USD", "t", True),
        ]
    )
    signal = evaluate_asset(asset, df, "test", 70, 75, consensus, [])
    assert signal is not None
    assert signal.level >= 1
    assert signal.data_quality == "alta"
