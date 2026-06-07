import pytest
from fastapi.testclient import TestClient
from api.index import app
import yfinance as yf
from unittest.mock import patch

client = TestClient(app)

@patch("api.index.get_company_synthesis")
@patch("yfinance.Ticker")
def test_synthesis_error_leak(mock_ticker, mock_synthesis):
    # Mock yfinance to avoid actual network calls
    mock_stock = mock_ticker.return_value
    mock_stock.info = {"symbol": "AAPL", "shortName": "Apple Inc."}

    # Mock synthesis to raise an exception
    mock_synthesis.side_effect = Exception("Super secret internal synthesis error that should not be leaked")

    response = client.get("/api/valuation/AAPL/synthesis")

    assert response.status_code == 500
    data = response.json()
    assert data["error"] is True
    # The message should NOT contain the original exception
    assert "Super secret internal synthesis error" not in data["detail"]
    assert data["detail"] == "Synthesis failed due to an internal server error."


@patch("api.index.kv_get")
def test_watchlist_database_error_leak(mock_kv_get):
    # Mock database to fail
    mock_kv_get.side_effect = Exception("Secret database connection string leaked")

    response = client.get("/api/watchlist")

    assert response.status_code == 500
    data = response.json()
    assert "Secret database connection string leaked" not in data["detail"]
    assert data["detail"] == "Database unreachable"
