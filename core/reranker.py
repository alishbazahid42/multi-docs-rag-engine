import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import CrossEncoder

class CrossEncoderReranker:
    """
    Reranks document chunks using a Cross-Encoder model to improve precision
    and filter out false positives from the vector database.
    """
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self.is_loaded = False
        
        try:
            print(f"Initializing Reranker: {model_name}...")
            self.load_model()
        except Exception as e:
            print(f"Reranker initialization warning: {e}")

    def load_model(self):
        """
        Loads the Cross-Encoder model in memory.
        """
        if not self.is_loaded:
            try:
                print(f"Loading Cross-Encoder model: {self.model_name} (this may take a minute on first run)...")
                self.model = CrossEncoder(self.model_name)
                self.is_loaded = True
                print("Cross-Encoder model loaded successfully.")
            except Exception as e:
                print(f"Error loading Cross-Encoder model. Reranker will run in fallback mode: {e}")
                self.model = None
                self.is_loaded = False

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Reranks a list of chunks based on a query using the Cross-Encoder model.
        Falls back to Vector DB similarity score if the model fails to load.
        """
        if not chunks:
            return []
            
        self.load_model()
        
        # If Cross-Encoder is not loaded, use fallback (already sorted by vector similarity)
        if not self.is_loaded or self.model is None:
            print("Reranker running in fallback mode (using Bi-Encoder scores).")
            # Sort by existing similarity score just in case, and take top_n
            sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
            return sorted_chunks[:top_n]
            
        try:
            # Prepare pairs: (query, text)
            pairs = [[query, chunk["text"]] for chunk in chunks]
            
            # Predict relevance scores (higher means more relevant)
            scores = self.model.predict(pairs)
            
            # Apply scores to chunks
            for i, score in enumerate(scores):
                chunks[i]["rerank_score"] = float(score)
                # Convert logit/score to a normalized confidence estimate (sigmoid)
                chunks[i]["confidence"] = float(1 / (1 + np.exp(-score)))
                
            # Sort by rerank score descending
            sorted_chunks = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
            
            print(f"Reranked {len(chunks)} chunks down to top {min(top_n, len(chunks))}.")
            return sorted_chunks[:top_n]
            
        except Exception as e:
            print(f"Error during reranking: {e}. Falling back to Bi-Encoder scores.")
            sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
            return sorted_chunks[:top_n]

if __name__ == "__main__":
    reranker = CrossEncoderReranker()
    print("Reranker ready.")
