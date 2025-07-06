# android_code_ai/dependency_graph.py
import hashlib
import networkx as nx
from pathlib import Path

class DependencyGraph:
    """Manages file relationships and dependencies"""
    def __init__(self):
        self.graph = nx.DiGraph()
        self.file_hashes = {}
    
    def add_file(self, file_path: str):
        """Add a file to the graph"""
        if file_path not in self.graph:
            self.graph.add_node(file_path)
            self.file_hashes[file_path] = self._calculate_file_hash(file_path)
    
    def add_dependency(self, source: str, target: str, rel_type: str = "imports"):
        """Add a dependency relationship between files"""
        self.add_file(source)
        self.add_file(target)
        
        if not self.graph.has_edge(source, target):
            self.graph.add_edge(source, target, type=rel_type)
    
    def get_related_files(self, file_path: str, depth: int = 2) -> list:
        """Get files related to the given file within a certain depth"""
        if file_path not in self.graph:
            return []
        
        related = set()
        # Get files that depend on this file
        for ancestor in nx.ancestors(self.graph, file_path):
            if nx.shortest_path_length(self.graph, ancestor, file_path) <= depth:
                related.add(ancestor)
        
        # Get files this file depends on
        for descendant in nx.descendants(self.graph, file_path):
            if nx.shortest_path_length(self.graph, file_path, descendant) <= depth:
                related.add(descendant)
        
        return list(related)
    
    def has_changed(self, file_path: str) -> bool:
        """Check if a file has changed since last index"""
        if file_path not in self.file_hashes:
            return True
        
        current_hash = self._calculate_file_hash(file_path)
        return current_hash != self.file_hashes[file_path]
    
    def update_hash(self, file_path: str):
        """Update the hash for a file"""
        self.file_hashes[file_path] = self._calculate_file_hash(file_path)
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate file hash for change detection"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""