# android_code_ai/context_retrieval.py
from typing import Dict, List

class ContextRetrievalEngine:
    """Automatically finds relevant context for queries"""
    def __init__(self, vector_db):
        self.vector_db = vector_db
        self.query_analyzer = QueryAnalyzer()
    
    def get_context(self, query: str, max_chunks: int = 15) -> Dict:
        """Automatically retrieve relevant context for a query"""
        # Analyze query to determine context type
        query_type = self.query_analyzer.analyze_query(query)
        
        # Get relevant chunks using hybrid search
        chunks = self.vector_db.hybrid_search(query, max_chunks)
        
        # Organize chunks by file
        context_by_file = {}
        for chunk in chunks:
            file_path = chunk['metadata']['file_path']
            if file_path not in context_by_file:
                context_by_file[file_path] = []
            context_by_file[file_path].append({
                'content': chunk['document'],
                'type': chunk['metadata']['type'],
                'score': chunk['score']
            })
        
        return {
            'query_type': query_type,
            'chunks': chunks,
            'files': context_by_file
        }

class QueryAnalyzer:
    """Analyzes queries to determine context needs"""
    def __init__(self):
        self.query_types = {
            'di': ['dagger', 'hilt', 'koin', 'inject', 'component', 'module', 'provide'],
            'ui': ['layout', 'view', 'compose', 'xml', 'button', 'text', 'image'],
            'logic': ['function', 'method', 'class', 'logic', 'algorithm', 'calculate'],
            'data': ['database', 'room', 'api', 'network', 'retrofit', 'data source']
        }
    
    def analyze_query(self, query: str) -> str:
        """Determine the type of context needed for the query"""
        query_lower = query.lower()
        
        for qtype, keywords in self.query_types.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return qtype
        
        # Default to general context
        return 'general'