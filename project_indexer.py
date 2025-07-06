# android_code_ai/project_indexer.py
import time
import logging
from pathlib import Path
from typing import Tuple
from .dependency_graph import DependencyGraph
from .ast_parser import ASTParser
from .dependency_parser import AndroidDependencyParser
from .embedding_generator import AndroidEmbeddingGenerator
from .vector_db import AndroidVectorDB

logger = logging.getLogger("AndroidCodeAI")

class ProjectIndexer:
    """Handles project indexing operations with incremental updates"""
    def __init__(self, project_root: str, dep_graph: DependencyGraph):
        self.project_root = project_root
        self.parser = ASTParser(dep_graph)
        self.dependency_parser = AndroidDependencyParser(project_root)
        self.embedding_generator = AndroidEmbeddingGenerator()
        self.vector_db = AndroidVectorDB()
        self.dep_graph = dep_graph
        self.last_index_time = 0
    
    def index_project(self, full_index: bool = False):
        """Index the entire Android project or update changed files"""
        logger.info(f"Indexing Android project at {self.project_root}")
        
        # First parse dependencies
        dependencies = self.dependency_parser.parse_project()
        logger.info(f"Detected dependencies: {dependencies}")
        
        # Check for DI frameworks
        if dependencies['di_frameworks']:
            logger.info(f"Detected DI frameworks: {', '.join(dependencies['di_frameworks'])}")
        
        # Process files
        file_extensions = ('.java', '.kt', '.xml', '.gradle', '.kts', '.properties')
        if full_index:
            self._full_index(file_extensions)
        else:
            self._incremental_index(file_extensions)
        
        logger.info("Project indexing completed!")
    
    def _full_index(self, file_extensions: Tuple[str]):
        """Perform a full index of all files"""
        for ext in file_extensions:
            for file_path in Path(self.project_root).rglob(f'*{ext}'):
                try:
                    self._process_file(file_path)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
        self.last_index_time = time.time()
    
    def _incremental_index(self, file_extensions: Tuple[str]):
        """Update only changed files"""
        changed_files = []
        for ext in file_extensions:
            for file_path in Path(self.project_root).rglob(f'*{ext}'):
                if self.dep_graph.has_changed(file_path):
                    changed_files.append(file_path)
        
        logger.info(f"Found {len(changed_files)} changed files to index")
        
        # Process changed files
        for file_path in changed_files:
            try:
                self._process_file(file_path)
                self.dep_graph.update_hash(file_path)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
        
        self.last_index_time = time.time()
    
    def _process_file(self, file_path: Path):
        """Process a single file and store its chunks"""
        logger.info(f"Processing {file_path}")
        
        # Add to dependency graph
        self.dep_graph.add_file(str(file_path))
        
        # Extract chunks
        chunks = self.parser.extract_chunks(str(file_path))
        
        # Generate embeddings for chunks
        chunks_with_embeddings = self.embedding_generator.generate_embeddings(chunks)
        
        # Store chunks in vector DB
        self.vector_db.store_chunks(chunks_with_embeddings)
        
        # Update hash in dependency graph
        self.dep_graph.update_hash(str(file_path))