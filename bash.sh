# Install dependencies
pip install tree-sitter-languages chromadb sentence-transformers openai networkx rank-bm25

# Full index
python main.py /path/to/android/project --index

# Incremental index
python main.py /path/to/android/project --index --incremental

# Query the codebase
python main.py /path/to/android/project --query "How is dependency injection implemented?" --openai-key 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