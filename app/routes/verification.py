from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.blockchain import initiate_verification

router = APIRouter(prefix="/api/verification")

class VerificationRequest(BaseModel):
    asset_hash: str
    transcript_hash: str
    sandbox_version: str

@router.post("/request")
async def request_verification(req: VerificationRequest):
    if not req.asset_hash or not req.transcript_hash:
        raise HTTPException(status_code=400, detail="Missing required hashes.")
        
    result = initiate_verification(
        asset_hash_hex=req.asset_hash,
        transcript_hash_hex=req.transcript_hash,
        sandbox_version=req.sandbox_version
    )
    
    return {
        "status": "success",
        "on_chain_data": result
    }
