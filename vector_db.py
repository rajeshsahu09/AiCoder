# android_code_ai/vector_db.py
import chromadb
import numpy as np
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from typing import Dict, List

class AndroidVectorDB:
    def __init__(self, db_path: str = "android_vector_db"):
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(allow_reset=True)
        )
        self.collection = self.client.get_or_create_collection(name="code_chunks")
        self.bm25_index = None
        self.chunk_documents = []
        self.chunk_metadatas = []
    
    def store_chunks(self, chunks: List[Dict]):
        """Store all chunks in the vector database"""
        embeddings = []
        documents = []
        metadatas = []
        ids = []
        
        for chunk in chunks:
            if 'embedding' not in chunk:
                continue
                
            embeddings.append(chunk['embedding'])
            documents.append(chunk['content'])
            
            metadata = {
                'file_path': chunk['file_path'],
                'type': chunk['type'],
                'chunk_id': chunk.get('chunk_id', '')
            }
            
            # Add framework if available
            if 'framework' in chunk:
                metadata['framework'] = chunk['framework']
            
            metadatas.append(metadata)
            ids.append(chunk.get('chunk_id', ''))
        
        # Store in vector DB
        if embeddings:
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        
        # Update BM25 index
        self.chunk_documents.extend(documents)
        self.chunk_metadatas.extend(metadatas)
        tokenized_docs = [doc.split() for doc in self.chunk_documents]
        self.bm25_index = BM25Okapi(tokenized_docs)
    
    def hybrid_search(self, query: str, n_results: int = 10) -> List[Dict]:
        """Perform hybrid search (vector + keyword)"""
        # Vector search
        vector_results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # BM25 keyword search
        bm25_results = self._bm25_search(query, n_results)
        
        # Combine results
        return self._combine_results(vector_results, bm25_results, n_results)
    
    def _bm25_search(self, query: str, n_results: int) -> List[Dict]:
        """Perform BM25 keyword search"""
        if not self.bm25_index:
            return []
        
        tokenized_query = query.split()
        scores = self.bm25_index.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:n_results]
        
        results = []
        for idx in top_indices:
            if idx < len(self.chunk_metadatas):
                results.append({
                    'id': str(idx),
                    'document': self.chunk_documents[idx],
                    'metadata': self.chunk_metadatas[idx],
                    'score': scores[idx]
                })
        
        return results
    
    def _combine_results(self, vector_results: Dict, bm25_results: List[Dict], n_results: int) -> List[Dict]:
        """Combine vector and keyword search results"""
        combined = []
        
        # Add vector results
        if vector_results['ids']:
            for i in range(len(vector_results['ids'][0])):
                combined.append({
                    'id': vector_results['ids'][0][i],
                    'document': vector_results['documents'][0][i],
                    'metadata': vector_results['metadatas'][0][i],
                    'score': 1 - vector_results['distances'][0][i]  # Convert distance to similarity
                })
        
        # Add BM25 results
        for result in bm25_results:
            # Normalize BM25 score to 0-1 range
            normalized_score = min(1.0, result['score'] / 10)
            combined.append({
                'id': result['id'],
                'document': result['document'],
                'metadata': result['metadata'],
                'score': normalized_score
            })
        
        # Deduplicate and sort
        seen = set()
        deduped = []
        for item in combined:
            if item['id'] not in seen:
                seen.add(item['id'])
                deduped.append(item)
        
        sorted_results = sorted(deduped, key=lambda x: x['score'], reverse=True)
        return sorted_results[:n_results]