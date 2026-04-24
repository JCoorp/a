from backend.universe import load_universe, search_assets, validate_universe_file


def test_universe_file_is_valid():
    assert validate_universe_file() == []


def test_universe_loads_assets():
    assets = load_universe()
    tickers = {asset.ticker for asset in assets}
    assert "NVDA" in tickers
    assert "TSLA" in tickers


def test_search_assets_finds_by_sector():
    results = search_assets("Semiconductors")
    tickers = {item["ticker"] for item in results}
    assert "NVDA" in tickers or "SMH" in tickers
