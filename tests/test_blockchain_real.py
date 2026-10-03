import os
import requests
from web3 import Web3

# Explicitly set the private key for the test so we use Anvil Account 0
os.environ["PRIVATE_KEY"] = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

def test_real_blockchain_integration():
    RPC_URL = "http://127.0.0.1:8545"
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    assert w3.is_connected(), "Anvil should be connected"
    
    assert w3.eth.chain_id == 31337, "Chain ID should be 31337"

    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # Valid bytes32 format
    asset_hash = "0x" + "11" * 32
    transcript_hash = "0x" + "22" * 32
    sandbox_version = "0.1.0"
    
    response = client.post("/api/verification/request", json={
        "asset_hash": asset_hash,
        "transcript_hash": transcript_hash,
        "sandbox_version": sandbox_version
    })
    
    assert response.status_code == 200, f"API error: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    
    on_chain_data = data["on_chain_data"]
    asset_id = on_chain_data["asset_id"]
    verification_id = on_chain_data["verification_id"]
    
    from app.services.blockchain import get_contract_data
    contracts = get_contract_data()
    verification_registry = contracts["verification_registry"]
    
    verification_record = verification_registry.functions.getVerification(bytes.fromhex(verification_id[2:])).call()
    
    exists = verification_record[0]
    rec_ver_id = verification_record[1].hex()
    rec_asset_id = verification_record[2].hex()
    rec_transcript = verification_record[3].hex()
    rec_status = verification_record[6] # VerificationStatus.PENDING == 0
    
    assert exists is True
    assert rec_ver_id == verification_id[2:]
    assert rec_asset_id == asset_id[2:]
    assert rec_status == 0 # PENDING
    
    print("\n--- TEST REPORT ---")
    print("Real Blockchain Integration Test: PASSED")
    print(f"Asset ID: {asset_id}")
    print(f"Verification ID: {verification_id}")
    print(f"Status (from contract): {rec_status} (PENDING)")
    print(f"Register TX: {on_chain_data['register_tx_hash']}")
    print(f"Verify TX: {on_chain_data['verify_tx_hash']}")
    print("-------------------\n")

if __name__ == "__main__":
    test_real_blockchain_integration()
