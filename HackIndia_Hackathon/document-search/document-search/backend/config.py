# backend/config.py
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))

# Document storage
DOCUMENTS_DIR = os.path.join(DATA_DIR, "documents")

# Index storage
INDEX_DIR = os.path.join(DATA_DIR, "index")
INDEX_PATH = os.path.join(INDEX_DIR, "faiss_index.bin")
DOCS_PATH = os.path.join(INDEX_DIR, "documents.pkl")

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_DEBUG = os.getenv("API_DEBUG", "False").lower() == "true"

# Embedding Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSION = 384  # This must match the model's output dimension

# Document Processing Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Search Configuration
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))

# Create required directories
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)