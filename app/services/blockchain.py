import json
import os
from pathlib import Path
from web3 import Web3
from fastapi import HTTPException

RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
if not PRIVATE_KEY:
    # Use Anvil Account 0
    PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

DEPLOYMENT_FILE = Path(os.getenv("DEPLOYMENT_FILE", r"C:\NebulaVerse\Smart_Contract_V1\deployments\anvil\deployment.json"))
ASSET_REGISTRY_OUT = Path(os.getenv("ASSET_REGISTRY_OUT", r"C:\NebulaVerse\Smart_Contract_V1\out\AssetRegistry.sol\AssetRegistry.json"))
VERIFICATION_REGISTRY_OUT = Path(os.getenv("VERIFICATION_REGISTRY_OUT", r"C:\NebulaVerse\Smart_Contract_V1\out\VerificationRegistry.sol\VerificationRegistry.json"))

w3 = Web3(Web3.HTTPProvider(RPC_URL))

def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_contract_data():
    deployment = _load_json(DEPLOYMENT_FILE)
    asset_address = deployment["contracts"]["AssetRegistry"]
    verification_address = deployment["contracts"]["VerificationRegistry"]
    
    asset_abi = _load_json(ASSET_REGISTRY_OUT)["abi"]
    verification_abi = _load_json(VERIFICATION_REGISTRY_OUT)["abi"]
    
    return {
        "asset_registry": w3.eth.contract(address=asset_address, abi=asset_abi),
        "verification_registry": w3.eth.contract(address=verification_address, abi=verification_abi)
    }

def check_connection():
    if not w3.is_connected():
        raise HTTPException(status_code=503, detail="Blockchain network is unavailable.")
    return True

def initiate_verification(asset_hash_hex: str, transcript_hash_hex: str, sandbox_version: str):
    """
    Submits asset registration and verification request on-chain.
    """
    check_connection()
    try:
        contracts = get_contract_data()
        asset_registry = contracts["asset_registry"]
        verification_registry = contracts["verification_registry"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load contract definitions: {str(e)}")

    account = w3.eth.account.from_key(PRIVATE_KEY)

    # Convert inputs to bytes
    if asset_hash_hex.startswith("0x"):
        asset_hash_hex = asset_hash_hex[2:]
    if transcript_hash_hex.startswith("0x"):
        transcript_hash_hex = transcript_hash_hex[2:]
        
    asset_hash_bytes = bytes.fromhex(asset_hash_hex.zfill(64))
    transcript_hash_bytes = bytes.fromhex(transcript_hash_hex.zfill(64))
    sandbox_version_bytes = sandbox_version.encode("utf-8").ljust(32, b'\0')

    try:
        nonce = w3.eth.get_transaction_count(account.address)
        
        # 1. Register Asset
        register_tx = asset_registry.functions.registerAsset(asset_hash_bytes).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price
        })
        signed_register_tx = w3.eth.account.sign_transaction(register_tx, private_key=PRIVATE_KEY)
        register_tx_hash = w3.eth.send_raw_transaction(signed_register_tx.raw_transaction)
        register_receipt = w3.eth.wait_for_transaction_receipt(register_tx_hash)
        
        if register_receipt.status != 1:
            raise Exception("Asset registration transaction reverted.")
            
        register_logs = asset_registry.events.AssetRegistered().process_receipt(register_receipt)
        if not register_logs:
            raise Exception("AssetRegistered event missing from receipt.")
        asset_id = register_logs[0]['args']['assetId']
        
        # 2. Request Verification
        nonce += 1
        verify_tx = verification_registry.functions.requestVerification(
            asset_id, transcript_hash_bytes, sandbox_version_bytes
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price
        })
        signed_verify_tx = w3.eth.account.sign_transaction(verify_tx, private_key=PRIVATE_KEY)
        verify_tx_hash = w3.eth.send_raw_transaction(signed_verify_tx.raw_transaction)
        verify_receipt = w3.eth.wait_for_transaction_receipt(verify_tx_hash)
        
        if verify_receipt.status != 1:
            raise Exception("Verification request transaction reverted.")
            
        verify_logs = verification_registry.events.VerificationRequested().process_receipt(verify_receipt)
        if not verify_logs:
            raise Exception("VerificationRequested event missing from receipt.")
        verification_id = verify_logs[0]['args']['verificationId']
        
        return {
            "asset_id": "0x" + asset_id.hex(),
            "verification_id": "0x" + verification_id.hex(),
            "register_tx_hash": "0x" + register_tx_hash.hex(),
            "verify_tx_hash": "0x" + verify_tx_hash.hex()
        }
    except Exception as e:
        # Preserve diagnostics but return safe HTTP error
        print(f"Contract interaction failed: {e}")
        raise HTTPException(status_code=400, detail=f"Contract interaction failed: {str(e)}")
