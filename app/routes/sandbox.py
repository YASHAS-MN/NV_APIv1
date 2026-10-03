from fastapi import APIRouter, UploadFile, File, HTTPException
import tempfile
import shutil
from pathlib import Path
import asyncio
import sys
import os

sandbox_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Sandbox_V2"))
if sandbox_path not in sys.path:
    sys.path.insert(0, sandbox_path)

try:
    from sandbox.orchestration.verifier import NebulaVerifier  # type: ignore
except ImportError:
    NebulaVerifier = None

router = APIRouter(prefix="/api/sandbox")

MAX_UPLOAD_SIZE = 1 * 1024 * 1024  # 1 MB limit

@router.post("/execute")
async def execute_sandbox(file: UploadFile = File(...)):
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
        with open(temp_file_path, "wb") as f:
            while chunk := await file.read(8192):
                size += len(chunk)
                if size > MAX_UPLOAD_SIZE:
                    raise HTTPException(status_code=413, detail="File too large.")
                f.write(chunk)
                
        if size == 0:
            raise HTTPException(status_code=400, detail="Empty upload.")

        def run_verifier():
            verifier = NebulaVerifier(timeout=10.0)
            return verifier.verify(temp_file_path).to_dict()
            
        result_dict = await asyncio.to_thread(run_verifier)
        
        return {
            "status": "success",
            "asset_name": file.filename,
            "sandbox_version": "0.1.0",
            "classification": result_dict.get("classification"),
            "static_analysis": result_dict.get("static_analysis"),
            "decision": result_dict.get("decision"),
            "execution": result_dict.get("execution"),
            "transcript": result_dict.get("transcript"),
            "hash": result_dict.get("hash")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Sandbox execution error: {e}")
        raise HTTPException(status_code=500, detail="Sandbox execution failed due to an internal error.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
