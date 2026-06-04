""" Configuration for RAG Pipeline """

from pathlib import path

class RAGConfig:
""" Central configuration for RAG pipeline"""

## PATH
BASE_DIR = Path(_file_).parent.parent.parent
KNOWLEDGE_BASE = BASE_DIR / "knowledge_base" / "owasp_corpus"
CHROMADB_DIR = BASE_DIR / "chromadb"

## METADATA
METADATA_FILE = BASE_DIR / "ingestion_metadata.json"

## Embedding settings
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

## Chunking settings
CHUNK_SIZE = 400     #tokens
CHUNK_OVERLAP = 50   #tokens

## Retrieval settings
TOP_K = 3
SIMILARITY_THRESHOLD = 0.6