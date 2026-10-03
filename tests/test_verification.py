import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

def test_verification_missing_inputs():
    response = client.post("/api/verification/request", json={
        "asset_hash": "",
        "transcript_hash": "0x123",
        "sandbox_version": "0.1.0"
    })
    assert response.status_code == 400

@patch("app.services.blockchain.w3.is_connected")
def test_verification_network_unavailable(mock_is_connected):
    mock_is_connected.return_value = False
    
    response = client.post("/api/verification/request", json={
        "asset_hash": "0xabc",
        "transcript_hash": "0x123",
        "sandbox_version": "0.1.0"
    })
    assert response.status_code == 503
    assert "Blockchain network is unavailable" in response.json()["detail"]

@patch("app.services.blockchain.w3")
@patch("app.services.blockchain.get_contract_data")
def test_verification_mocked_success(mock_get_contracts, mock_w3):
    """
    Mocked test to verify the API workflow without Anvil.
    """
    mock_w3.is_connected.return_value = True
    mock_w3.eth.gas_price = 1000000000
    mock_w3.eth.get_transaction_count.return_value = 0
    
    mock_asset_registry = MagicMock()
    mock_verification_registry = MagicMock()
    mock_get_contracts.return_value = {
        "asset_registry": mock_asset_registry,
        "verification_registry": mock_verification_registry
    }
    
    mock_receipt_success = MagicMock()
    mock_receipt_success.status = 1
    mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt_success
    
    # Mock event parsing
    mock_asset_registry.events.AssetRegistered.return_value.process_receipt.return_value = [
        {'args': {'assetId': b'asset_id_12345678901234567890123'}}
    ]
    mock_verification_registry.events.VerificationRequested.return_value.process_receipt.return_value = [
        {'args': {'verificationId': b'verify_id_1234567890123456789012'}}
    ]
    
    mock_w3.eth.send_raw_transaction.side_effect = [b'tx_hash_1', b'tx_hash_2']
    
    response = client.post("/api/verification/request", json={
        "asset_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "transcript_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "sandbox_version": "0.1.0"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "asset_id" in data["on_chain_data"]
    assert "verification_id" in data["on_chain_data"]
    data = response.json()
    assert data["status"] == "success"
    assert "asset_id" in data["on_chain_data"]
    assert "verification_id" in data["on_chain_data"]

