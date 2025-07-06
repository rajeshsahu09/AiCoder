# android_code_ai/embedding_generator.py
import hashlib
from sentence_transformers import SentenceTransformer
from typing import Dict, List

class AndroidEmbeddingGenerator:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
    
    def generate_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        """Generate embeddings for each chunk"""
        chunk_texts = [chunk['content'] for chunk in chunks]
        embeddings = self.model.encode(chunk_texts)
        
        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[i].tolist()
            
            # Generate a unique ID for the chunk
            chunk_id = hashlib.md5(
                f"{chunk['file_path']}-{chunk['type']}".encode()
            ).hexdigest()
            chunk['chunk_id'] = chunk_id
        
        return chunks