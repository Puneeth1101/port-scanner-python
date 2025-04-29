# backend/search/engine.py
import os
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
import faiss
import pickle
import json

class SearchEngine:
    """Vector-based search engine for document retrieval."""
    
    def __init__(self, embedding_dim: int = 384, index_path: str = None, docs_path: str = None):
        """
        Initialize the search engine.
        
        Args:
            embedding_dim: Dimension of embeddings
            index_path: Path to saved index, if available
            docs_path: Path to saved document metadata, if available
        """
        self.embedding_dim = embedding_dim
        self.index = None
        self.documents = []
        self.doc_ids_to_indices = {}  # Mapping from doc_ids to index positions
        
        # Initialize or load index
        if index_path and os.path.exists(index_path) and docs_path and os.path.exists(docs_path):
            self.load_index(index_path, docs_path)
        else:
            self.index = faiss.IndexFlatL2(embedding_dim)
    
    def add_documents(self, docs: List[Dict[str, Any]]) -> None:
        """
        Add documents to the search index.
        
        Args:
            docs: List of document dictionaries with 'text', 'metadata', and 'embedding' keys
        """
        if not docs:
            return
            
        # Prepare embeddings for FAISS
        embeddings = np.array([doc['embedding'] for doc in docs]).astype('float32')
        
        # Add to index
        start_idx = len(self.documents)
        self.index.add(embeddings)
        
        # Store documents without embeddings to save memory
        for i, doc in enumerate(docs):
            # Remove large embedding from stored document
            doc_copy = {k: v for k, v in doc.items() if k != 'embedding'}
            self.documents.append(doc_copy)
            
            # Map document ID to its position
            doc_id = doc['metadata']['doc_id']
            chunk_id = doc['metadata']['chunk_id']
            unique_id = f"{doc_id}_{chunk_id}"
            self.doc_ids_to_indices[unique_id] = start_idx + i
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query.
        
        Args:
            query_embedding: Vector representation of the query
            top_k: Number of results to return
            
        Returns:
            List of document dictionaries with similarity scores
        """
        if len(self.documents) == 0:
            return []
            
        # Ensure the embedding is the right shape
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        
        # Search the index
        distances, indices = self.index.search(query_embedding, min(top_k, len(self.documents)))
        
        # Get the documents
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # FAISS returns -1 for not enough results
                doc = self.documents[idx]
                # Add distance as a similarity score (lower is better)
                doc['score'] = float(1.0 / (1.0 + distances[0][i]))
                results.append(doc)
                
        return results
    
    def save_index(self, index_path: str, docs_path: str) -> None:
        """
        Save the index and documents to disk.
        
        Args:
            index_path: Path to save the FAISS index
            docs_path: Path to save the document metadata
        """
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        os.makedirs(os.path.dirname(docs_path), exist_ok=True)
        
        # Save the index
        faiss.write_index(self.index, index_path)
        
        # Save the documents
        with open(docs_path, 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'doc_ids_to_indices': self.doc_ids_to_indices
            }, f)
    
    def load_index(self, index_path: str, docs_path: str) -> None:
        """
        Load the index and documents from disk.
        
        Args:
            index_path: Path to the saved FAISS index
            docs_path: Path to the saved document metadata
        """
        # Load the index
        self.index = faiss.read_index(index_path)
        
        # Load the documents
        with open(docs_path, 'rb') as f:
            data = pickle.load(f)
            self.documents = data['documents']
            self.doc_ids_to_indices = data['doc_ids_to_indices']