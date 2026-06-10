"""
Simple RAG Retriever for BLT Preflight

"""

from typing import List, Dict
from sentence_transformers import SentenceTransformer
import chromadb

from src.advisory_engine.rag.config  import RAGConfig


class RAGRetriever:
    """Simple retriever to get relevant OWASP chunks."""

    def __init__(self):
        self.config = RAGConfig()
        self.embedder = SentenceTransformer(self.config.EMBEDDING_MODEL)
        
        # Connect to existing ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.config.CHROMA_DB_DIR))
        self.collection = self.client.get_collection("owasp_knowledge_base")

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Retrieve top relevant chunks for a user query.
        """
        # Generate embedding for query
        query_embedding = self.embedder.encode(query)
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        retrieved = []
        for i in range(len(results['documents'][0])):
            retrieved.append({
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "similarity": 1 - results['distances'][0][i]   # Convert distance to similarity
            })
        
        return retrieved


# Quick test when running directly
if __name__ == "__main__":
    retriever = RAGRetriever()
    
    test_queries = [
        "I modified the login flow",
        "I added a new API endpoint",
        "I changed how passwords are stored",
        "How to prevent SQL injection"
    ]
    
    print(" Testing Retrieval:\n")
    for query in test_queries:
        print(f"Query: {query}")
        results = retriever.retrieve(query, top_k=2)
        for i, r in enumerate(results):
            print(f"  {i+1}. [{r['similarity']:.3f}] {r['metadata'].get('title', 'N/A')}")
            print(f"     {r['text'][:150]}...\n")
        print("-" * 80)