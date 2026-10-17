#!/usr/bin/env python3
"""
OWASP Knowledge Base Ingestion Script for BLT Preflight

This script:
1. Loads OWASP documents from knowledge_base/owasp_corpus/
2. Performs section-aware chunking
3. Generates embeddings using all-MiniLM-L6-v2
4. Stores everything in ChromaDB
"""

from pathlib import Path
import json
from typing import List, Dict

from sentence_transformers import SentenceTransformer
import chromadb
from tqdm import tqdm

from src.advisory_engine.rag.config import RAGConfig


def load_metadata(metadata_path: Path) -> Dict:
    """Load metadata from JSON file"""
    with open(metadata_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def clean_frontmatter(text: str) -> str:
    """ Remove YAML frontmatter from markown file """
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) > 3:
            return parts[2].strip()
    return text.strip()


def section_aware_chunk(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """
    Split md files into logical chunks based on headings.
    """
    import re

    # Split into sections based on markdown headings
    sections = re.split(r'^(#{1,6}\s+.+?)$', text, flags=re.MULTILINE)

    chunks = []
    current_chunk = ""

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if section.strip().startswith('#'):  # This is a heading
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = section + "\n"
        else:
            current_chunk += section + "\n"

            # If chunk exceeds size, save it and keep overlap
            if len(current_chunk.split()) > chunk_size:
                chunks.append(current_chunk.strip())
                words = current_chunk.split()
                current_chunk = " ".join(words[-overlap:]) + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

    
def main():
    print(" Starting OWASP Knowledge Base Ingestion...\n")

    config = RAGConfig()

    # Step 1: Load Metadata
    metadata = load_metadata(config.METADATA_FILE)
    print(f"Loaded metadata for {len(metadata.get('documents', []))} documents.")

    # Step 2: Initialize Embedding Model
    print(f"Loading embedding model: {config.EMBEDDING_MODEL}")
    embedder = SentenceTransformer(config.EMBEDDING_MODEL)

    # Step 3: Initialize ChromaDB 
    client = chromadb.PersistentClient(path=str(config.CHROMADB_DIR))
    collection = client.get_or_create_collection(
      name="owasp_knowledge_base",
      metadata={"hnsw:space": "cosine"}
    )

    collection.delete(where={})  # Clear previous data
    total_chunks = 0
    
    # Step 4: Process each document
    for doc_info in tqdm(metadata.get('documents', []), desc="Processing documents"):
        file_path = config.KNOWLEDGE_BASE / doc_info["filename"]

        if not file_path.exists():
            print(f"Warning: {file_path} not found. Skipping process.")
            continue

        # Read and clean document
        text = file_path.read_text(encoding='utf-8')
        clean_text = clean_frontmatter(text)

        # Chunk the document
        chunks = section_aware_chunk(
            clean_text,
            chunk_size=config.CHUNK_SIZE,
            overlap=config.CHUNK_OVERLAP
        )

        # Generate embeddings
        embeddings = embedder.encode(chunks, show_progress_bar=False)

        # Prepare metadata for each chunk
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_info['filename']}_{i:04d}"
            metadatas.append({
                "title": doc_info.get("title", ""),
                "category": doc_info.get("category", ""),
                "source_url": doc_info.get("source_url", ""),
                "filename": doc_info["filename"],
                "chunk_index": i,
            })
            ids.append(chunk_id)

        # Add to ChromaDB
        collection.add(
            documents=chunks,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
            ids=ids
        )

        total_chunks += len(chunks)
        print(f" Done {doc_info['filename']}: {len(chunks)} chunks")

    print("\n Ingestion is completed sucessfully!!")
    print(f"  Total documents processed: {len(metadata.get('documents', []))}")
    print(f"  Total chunks stored: {total_chunks}")
    print(f"  ChromaDB path: {config.CHROMADB_DIR}")


if __name__ == "__main__":
    main()
