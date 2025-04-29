# backend/document_processor/embeddings.py
from typing import Dict, List, Any
import numpy as np

from sentence_transformers import SentenceTransformer

class EmbeddingGenerator:
    """Generates vector embeddings for document chunks."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: The sentence transformer model to use for embeddings
        """
        self.model = SentenceTransformer(model_name)
    
    def generate_embeddings(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for a list of document chunks.
        
        Args:
            docs: List of document dictionaries with 'text' and 'metadata' keys
            
        Returns:
            The same list with added 'embedding' key in each document
        """
        texts = [doc['text'] for doc in docs]
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Add embeddings to documents
        for i, doc in enumerate(docs):
            doc['embedding'] = embeddings[i]
            
        return docs