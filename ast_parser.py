# android_code_ai/ast_parser.py
import os
import json
import logging
from tree_sitter_languages import get_parser
from pathlib import Path
from typing import Any, Dict, List, Optional
from .di_analyzer import DIAnalyzer
from .xml_analyzer import XMLAnalyzer
import hashlib

logger = logging.getLogger("AndroidCodeAI")

class ASTParser:
    MAX_CHUNK_SIZE = 2000
    MIN_CHUNK_SIZE = 500
    CACHE_DIR = ".ast_cache"
    
    def __init__(self, dep_graph):
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        self.parsers = {
            'python': get_parser('python'),
            'java': get_parser('java'),
            'kt': get_parser('kotlin'),
            'kts': get_parser('kotlin'),
        }
        self.di_analyzer = DIAnalyzer()
        self.xml_analyzer = XMLAnalyzer()
        self.dep_graph = dep_graph
    
    def get_parser(self, file_path: str):
        """Get appropriate parser for file type"""
        ext = Path(file_path).suffix[1:]
        return self.parsers.get(ext)
    
    def parse_file(self, file_path: str) -> Any:
        """Parse file using Tree-sitter if possible"""
        parser = self.get_parser(file_path)
        if not parser:
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            return parser.parse(bytes(code, 'utf8'))
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {str(e)}")
            return None
    
    def extract_chunks(self, file_path: str) -> List[Dict]:
        """Extract or load chunks for a file"""
        cache_file = self._get_cache_path(file_path)
        
        # Try to load from cache
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                logger.warning(f"Failed to load cache for {file_path}")
        
        # Generate chunks and save to cache
        chunks = self._generate_chunks(file_path)
        with open(cache_file, 'w') as f:
            json.dump(chunks, f, indent=2)
        
        return chunks
    
    def _get_cache_path(self, file_path: str) -> str:
        """Get path to cache file"""
        file_hash = hashlib.md5(file_path.encode()).hexdigest()
        return os.path.join(self.CACHE_DIR, f"{file_hash}.json")
    
    def _generate_chunks(self, file_path: str) -> List[Dict]:
        """Generate chunks for a file"""
        content = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {str(e)}")
            return []
        
        # Process based on file type
        if file_path.endswith(('.java', '.kt', '.kts')):
            tree = self.parse_file(file_path)
            return self._extract_code_chunks(tree, content, file_path)
        elif file_path.endswith('.xml'):
            return self.xml_analyzer.analyze_file(file_path, content)
        else:
            return self._chunk_by_lines(content, file_path)
    
    def _extract_code_chunks(self, tree: Any, content: str, file_path: str) -> List[Dict]:
        """Extract chunks from code files"""
        chunks = []
        
        if not tree:
            return chunks
        
        # Perform DI analysis
        di_analysis = self.di_analyzer.analyze_file(file_path, content)
        
        # Extract imports for dependency graph
        imports = self._extract_imports(tree)
        for imp in imports:
            target_file = self._import_to_file(imp, file_path)
            if target_file:
                self.dep_graph.add_dependency(file_path, target_file, "imports")
        
        # Extract classes and functions as primary chunks
        cursor = tree.walk()
        self._traverse_code(cursor.node, content, file_path, chunks)
        
        # Add DI chunks if available
        if di_analysis:
            chunks.extend(self._create_di_chunks(di_analysis, file_path))
        
        return chunks
    
    def _extract_imports(self, tree: Any) -> list:
        """Extract import statements from code"""
        imports = []
        cursor = tree.walk()
        
        def traverse(node):
            if node.type == 'import_declaration':
                import_statement = node.text.decode('utf8').replace('import', '').strip().rstrip(';')
                imports.append(import_statement)
            
            for child in node.children:
                traverse(child)
        
        traverse(cursor.node)
        return imports
    
    def _import_to_file(self, import_path: str, source_file: str) -> Optional[str]:
        """Convert import path to file path"""
        try:
            project_root = Path(source_file).parent
            while project_root.name != 'java' and project_root.name != 'kotlin':
                project_root = project_root.parent
            
            package_path = import_path.replace('.', '/')
            return str(project_root / f"{package_path}.kt")
        except:
            return None
    
    def _traverse_code(self, node: Any, content: str, file_path: str, chunks: list):
        """Traverse AST to extract meaningful chunks"""
        try:
            # Chunk classes
            if node.type == 'class_declaration':
                class_content = node.text.decode('utf8')
                if self.MIN_CHUNK_SIZE < len(class_content) < self.MAX_CHUNK_SIZE:
                    chunks.append({
                        'type': 'class',
                        'content': class_content,
                        'file_path': file_path,
                    })
                else:
                    self._chunk_large_node(node, content, file_path, chunks, 'class')
            
            # Chunk functions
            elif node.type in ['function_declaration', 'method_declaration']:
                func_content = node.text.decode('utf8')
                if self.MIN_CHUNK_SIZE < len(func_content) < self.MAX_CHUNK_SIZE:
                    chunks.append({
                        'type': 'function',
                        'content': func_content,
                        'file_path': file_path,
                    })
                else:
                    self._chunk_large_node(node, content, file_path, chunks, 'function')
            
            # Recursively traverse children
            for child in node.children:
                self._traverse_code(child, content, file_path, chunks)
                
        except Exception as e:
            logger.error(f"Error traversing node: {str(e)}")
    
    def _chunk_large_node(self, node: Any, content: str, file_path: str, chunks: list, node_type: str):
        """Break large AST nodes into smaller chunks"""
        node_content = node.text.decode('utf8')
        current_chunk = ""
        
        # Split by logical boundaries
        lines = node_content.split('\n')
        for line in lines:
            if len(current_chunk) + len(line) > self.MAX_CHUNK_SIZE and current_chunk:
                chunks.append({
                    'type': f'{node_type}_chunk',
                    'content': current_chunk.strip(),
                    'file_path': file_path,
                })
                current_chunk = ""
            current_chunk += line + '\n'
        
        if current_chunk.strip():
            chunks.append({
                'type': f'{node_type}_chunk',
                'content': current_chunk.strip(),
                'file_path': file_path,
            })
    
    def _create_di_chunks(self, di_analysis: Dict, file_path: str) -> list:
        """Create chunks for DI components"""
        chunks = []
        
        # Create chunks for DI components
        for component in di_analysis.get('components', []):
            chunks.append({
                'type': 'di_component',
                'content': component,
                'file_path': file_path,
                'framework': di_analysis['framework']
            })
        
        # Create chunks for DI modules
        for module in di_analysis.get('modules', []):
            chunks.append({
                'type': 'di_module',
                'content': module,
                'file_path': file_path,
                'framework': di_analysis['framework']
            })
        
        # Create chunks for DI providers
        for provider in di_analysis.get('providers', []):
            chunks.append({
                'type': 'di_provider',
                'content': provider,
                'file_path': file_path,
                'framework': di_analysis['framework']
            })
        
        return chunks
    
    def _chunk_by_lines(self, content: str, file_path: str) -> list:
        """Chunk content by lines for unsupported file types"""
        chunks = []
        lines = content.split('\n')
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk) + len(line) > self.MAX_CHUNK_SIZE and current_chunk:
                chunks.append({
                    'type': 'text_chunk',
                    'content': current_chunk.strip(),
                    'file_path': file_path,
                })
                current_chunk = ""
            current_chunk += line + '\n'
        
        if current_chunk.strip():
            chunks.append({
                'type': 'text_chunk',
                'content': current_chunk.strip(),
                'file_path': file_path,
            })
        
        return chunks