from fastapi import APIRouter, UploadFile, File, HTTPException
import tempfile
import shutil
from pathlib import Path
import asyncio
import sys
import os
import hashlib
from app.services.blockchain import initiate_verification, get_contract_data

sandbox_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Sandbox_V2"))
if sandbox_path not in sys.path:
    sys.path.insert(0, sandbox_path)

try:
    from sandbox.orchestration.verifier import NebulaVerifier  # type: ignore
except ImportError:
    NebulaVerifier = None

router = APIRouter(prefix="/api/workflow")

MAX_UPLOAD_SIZE = 1 * 1024 * 1024  # 1 MB limit

@router.post("/submit")
async def submit_workflow(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty upload.")
    
    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Only .py files are supported.")
        
    if NebulaVerifier is None:
        raise HTTPException(status_code=500, detail="Sandbox module is not available.")
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = Path(temp_dir) / file.filename
    
    try:
        size = 0
        hasher = hashlib.sha256()
        
        with open(temp_file_path, "wb") as f:
            while chunk := await file.read(8192):
                size += len(chunk)
                if size > MAX_UPLOAD_SIZE:
                    raise HTTPException(status_code=413, detail="File too large.")
                f.write(chunk)
                hasher.update(chunk)
                
        if size == 0:
            raise HTTPException(status_code=400, detail="Empty upload.")

        asset_hash = hasher.hexdigest()

        # 2. Run Sandbox
        def run_verifier():
            verifier = NebulaVerifier(timeout=10.0)
            return verifier.verify(temp_file_path).to_dict()
            
        result_dict = await asyncio.to_thread(run_verifier)
        
        sandbox_decision = result_dict.get("decision")
        transcript_hash = result_dict.get("hash")
        sandbox_version = "0.1.0"
        
        if sandbox_decision is None or sandbox_decision not in ("ACCEPT", "CONTINUE"):
            # Just return the sandbox failure, do not request verification
            return {
                "status": "rejected",
                "message": f"Sandbox execution did not accept the file. Decision: {sandbox_decision}",
                "sandbox_result": result_dict
            }
            
        # 3. Submit Verification Request
        on_chain_data = initiate_verification(asset_hash, transcript_hash, sandbox_version)
        
        # 4. Get current on-chain status
        try:
            contracts = get_contract_data()
            verification_registry = contracts["verification_registry"]
            verification_id_bytes = bytes.fromhex(on_chain_data["verification_id"][2:])
            verification_record = verification_registry.functions.getVerification(verification_id_bytes).call()
            status_code = verification_record[6]
            status_string = "PENDING" if status_code == 0 else ("FINALIZED" if status_code == 1 else "REJECTED")
        except Exception as e:
            print(f"Failed to read verification status back: {e}")
            status_string = "UNKNOWN"

        on_chain_data["status"] = status_string

        return {
            "status": "success",
            "message": "Workflow completed successfully.",
            "asset_hash": "0x" + asset_hash,
            "sandbox_result": {
                "asset_name": file.filename,
                "sandbox_version": sandbox_version,
                "classification": result_dict.get("classification"),
                "decision": sandbox_decision,
                "transcript_hash": transcript_hash
            },
            "on_chain_data": on_chain_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Workflow execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
