#!/usr/bin/env python3
"""
Android Code AI - Main Application
"""

import os
import argparse
import logging
import time
from .dependency_graph import DependencyGraph
from .project_indexer import ProjectIndexer
from .context_retrieval import ContextRetrievalEngine
from .rag_system import AndroidRAGSystem
from .vector_db import AndroidVectorDB
import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("android_code_ai.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AndroidCodeAI")

class AndroidCodeAI:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.dep_graph = DependencyGraph()
        self.indexer = ProjectIndexer(project_root, self.dep_graph)
        self.vector_db = AndroidVectorDB()
        self.context_engine = ContextRetrievalEngine(self.vector_db)
        self.rag = AndroidRAGSystem(self.context_engine)
        self.last_query_time = 0
    
    def index_project(self, full_index: bool = True):
        """Index the project codebase"""
        self.indexer.index_project(full_index)
    
    def query(self, question: str) -> str:
        """Query the codebase with natural language"""
        # Check if we need to do incremental indexing before querying
        if time.time() - self.indexer.last_index_time > 3600:  # 1 hour
            logger.info("Performing incremental index before query")
            self.index_project(full_index=False)
        
        self.last_query_time = time.time()
        return self.rag.generate_response(question)

def main():
    parser = argparse.ArgumentParser(description='Android Code AI Assistant')
    parser.add_argument('project_root', help='Path to Android project root')
    parser.add_argument('--index', action='store_true', help='Index the project')
    parser.add_argument('--incremental', action='store_true', help='Perform incremental indexing')
    parser.add_argument('--query', help='Natural language query about the codebase')
    parser.add_argument('--openai-key', help='OpenAI API key for LLM queries')
    
    args = parser.parse_args()
    
    # Set OpenAI API key if provided
    if args.openai_key:
        os.environ['OPENAI_API_KEY'] = args.openai_key
        openai.api_key = args.openai_key
    
    # Initialize the AI system
    android_ai = AndroidCodeAI(args.project_root)
    
    # Index the project if requested
    if args.index:
        android_ai.index_project(full_index=not args.incremental)
    
    # Handle queries
    if args.query:
        response = android_ai.query(args.query)
        print("\n" + "="*80)
        print("RESPONSE:")
        print("="*80)
        print(response)
        print("="*80)

if __name__ == "__main__":
    main()