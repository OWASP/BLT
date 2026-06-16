""" Configuration for RAG Pipeline """

from pathlib import Path
import os

class RAGConfig:
    ## PATH
    BASE_DIR = Path(__file__).parent.parent.parent.parent
    KNOWLEDGE_BASE = BASE_DIR / "knowledge_base" / "owasp_corpus"
    # Support both chroma_index (Docker) and chromadb (local)
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "chroma_index"))
    CHROMADB_DIR = Path(CHROMA_PERSIST_DIR)

    ## METADATA
    METADATA_FILE = BASE_DIR / "knowledge_base" / "ingestion_metadata.json"

    ## Embedding settings
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    ## Chunking settings
    CHUNK_SIZE = 400     # tokens
    CHUNK_OVERLAP = 50   # tokens

    ## Retrieval settings
    TOP_K = 3
    SIMILARITY_THRESHOLD = 0.6  # Quality threshold for retrieval
    CONFIDENCE_MIN = 0.55       # Absolute minimum similarity to return
