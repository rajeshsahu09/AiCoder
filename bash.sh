# Install dependencies
pip install tree-sitter-languages chromadb sentence-transformers openai networkx rank-bm25

# Full index
python main.py /path/to/android/project --index

# Incremental index
python main.py /path/to/android/project --index --incremental

# Query the codebase
python main.py /path/to/android/project --query "How is dependency injection implemented?" --openai-key sk-...
