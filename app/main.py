from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import health, sandbox, verification, workflow
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local dev — enumerate specific origins in production
    allow_credentials=False,  # Cannot combine wildcard origin with credentials=True (CORS spec)
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sandbox.router)
app.include_router(verification.router)
app.include_router(workflow.router)

@app.get("/")
async def root():
    return {"message": "Welcome to NebulaVerse API"}
