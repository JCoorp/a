from backend.consensus_engine import build_consensus, data_quality_score
from backend.models import Snapshot


def test_consensus_high_quality_when_sources_agree():
    snapshots = [
        Snapshot("a", "NVDA", 100.0, 1000, "USD", "t1", True),
        Snapshot("b", "NVDA", 100.1, 1200, "USD", "t1", True),
        Snapshot("c", "NVDA", 99.9, 900, "USD", "t1", True),
    ]
    consensus = build_consensus(snapshots)
    assert consensus.quality == "alta"
    assert consensus.blocked is False
    assert consensus.valid_sources == 3


def test_consensus_blocks_high_divergence():
    snapshots = [
        Snapshot("a", "NVDA", 100.0, 1000, "USD", "t1", True),
        Snapshot("b", "NVDA", 120.0, 1200, "USD", "t1", True),
        Snapshot("c", "NVDA", 99.8, 900, "USD", "t1", True),
    ]
    consensus = build_consensus(snapshots)
    assert consensus.blocked is True
    assert consensus.quality == "baja"


def test_data_quality_score_mapping():
    assert data_quality_score("alta") == 100.0
    assert data_quality_score("media") == 70.0
    assert data_quality_score("baja") == 35.0
