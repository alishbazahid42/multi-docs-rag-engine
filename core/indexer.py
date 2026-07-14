import os
import numpy as np
import faiss
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from core.parser import LayoutAwarePDFParser

class VectorIndexer:
    """
    Manages embedding generation, vector storage using FAISS, and semantic search queries.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Load a lightweight, high-performance bi-encoder model running on CPU
        print(f"Loading Bi-Encoder model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.parser = LayoutAwarePDFParser()
        
        # Dynamically set embedding dimension from the model's output size
        self.embedding_dimension = self.model.get_sentence_embedding_dimension()
        
        # IndexFlatIP uses Inner Product (Cosine Similarity if vectors are normalized)
        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        
        # In-memory mapping from FAISS index ID to document chunk data
        self.chunks: List[Dict[str, Any]] = []

    def chunk_text(self, text: str, max_chars: int = 800, overlap: int = 150) -> List[str]:
        """
        Helper method to chunk text that exceeds maximum character threshold
        while maintaining semantic overlap.
        """
        if len(text) <= max_chars:
            return [text]
            
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            chunks.append(text[start:end])
            start += (max_chars - overlap)
            
        return chunks

    def add_document(self, file_path: str) -> int:
        """
        Parses a PDF, chunks text blocks, embeds them, and inserts them into the FAISS index.
        Returns the number of chunks added.
        """
        # 1. Parse PDF using our layout-aware parser
        raw_chunks = self.parser.parse_pdf(file_path)
        if not raw_chunks:
            return 0
            
        processed_chunks = []
        for chunk in raw_chunks:
            text = chunk["text"]
            metadata = chunk["metadata"]
            
            # Sub-chunk text if a layout block is too large
            sub_texts = self.chunk_text(text)
            for sub_text in sub_texts:
                processed_chunks.append({
                    "text": sub_text.strip(),
                    "metadata": metadata
                })
                
        if not processed_chunks:
            return 0
            
        # 2. Extract texts and generate embeddings
        texts = [c["text"] for c in processed_chunks]
        embeddings = self.model.encode(texts, show_progress_bar=False)
        
        # Normalize embeddings to unit length for Cosine Similarity (via FlatIP)
        faiss.normalize_L2(embeddings)
        
        # 3. Add to FAISS index
        self.index.add(np.array(embeddings, dtype=np.float32))
        
        # 4. Save chunk metadata
        self.chunks.extend(processed_chunks)
        
        print(f"Successfully indexed {len(processed_chunks)} chunks from {os.path.basename(file_path)}.")
        return len(processed_chunks)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Embeds the query and performs a similarity search on the FAISS index.
        Returns matching chunks sorted by relevance score.
        """
        if len(self.chunks) == 0:
            return []
            
        # Encode and normalize query vector
        query_vector = self.model.encode([query], show_progress_bar=False)
        faiss.normalize_L2(query_vector)
        
        # Perform similarity search
        actual_k = min(top_k, len(self.chunks))
        scores, indices = self.index.search(np.array(query_vector, dtype=np.float32), actual_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
                
            chunk_data = self.chunks[idx].copy()
            # Convert inner product score back to float
            chunk_data["score"] = float(score)
            results.append(chunk_data)
            
        return results

    def get_all_documents(self) -> List[str]:
        """
        Returns a list of unique document filenames currently indexed.
        """
        seen = set()
        for chunk in self.chunks:
            seen.add(chunk["metadata"]["source"])
        return sorted(list(seen))

    def clear(self):
        """
        Clears the FAISS index and the memory map.
        """
        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        self.chunks = []
        print("Indexer cleared.")

if __name__ == "__main__":
    indexer = VectorIndexer()
    print("Indexer initialized.")
