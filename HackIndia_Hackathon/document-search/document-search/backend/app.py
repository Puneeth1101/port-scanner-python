# backend/app.py
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import configuration
import config

# Import API routes
from api import router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Document Search & Retrieval",
    description="API for searching and retrieving documents using AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting AI Document Search & Retrieval API")
    logger.info(f"Data directory: {config.DATA_DIR}")
    logger.info(f"Documents directory: {config.DOCUMENTS_DIR}")
    logger.info(f"Index directory: {config.INDEX_DIR}")

if __name__ == "__main__":
    uvicorn.run(
        "app:app", 
        host=config.API_HOST, 
        port=config.API_PORT, 
        reload=config.API_DEBUG
    )