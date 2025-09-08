from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Import routers
from app.routers import pipeline, edit, animate, agent_chat

# Create FastAPI app
app = FastAPI(title="Pixel Banana Suite API", version="1.0.0")

# Configure CORS - MUST be before routers
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,          # ok for dev; don't use with allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],           # optional: expose custom headers
    max_age=600,                     # optional: cache preflight 10 min
)

# Optional: Static file serving for artifacts (before routers)
app.mount("/view", StaticFiles(directory="assets/outputs"), name="view")

# Include routers
app.include_router(pipeline.router)
app.include_router(edit.router)
app.include_router(animate.router)
app.include_router(agent_chat.router)

@app.get("/")
def root():
    return {"message": "Pixel Banana Suite API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}