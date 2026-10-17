"""
Enhanced RAG Retriever for BLT Preflight with Quality & Hallucination Prevention

Features:
- Similarity threshold filtering (prevents low-quality matches)
- Multi-pass retrieval (retrieves more, filters down)
- Metadata validation (ensures chunks have proper source info)
- Relevance scoring (normalized confidence metric)
- Fallback mechanism (returns "no relevant docs" instead of hallucinating)
"""

from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import chromadb
import logging

from src.advisory_engine.rag.config import RAGConfig

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Enhanced retriever with hallucination prevention and quality metrics."""

    def __init__(self, similarity_threshold: float = 0.6):
        self.config = RAGConfig()
        self.embedder = SentenceTransformer(self.config.EMBEDDING_MODEL)
        
        # Connect to ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.config.CHROMADB_DIR))
        self.collection = self.client.get_collection("owasp_knowledge_base")
        
        # Quality thresholds
        self.similarity_threshold = similarity_threshold
        self.min_chunk_length = 50  # Prevent tiny/empty chunks

    def retrieve(
        self, 
        query: str, 
        top_k: int = 3,
        similarity_threshold: Optional[float] = None
    ) -> Dict:
        """
        Retrieve top relevant chunks with quality validation.
        
        Returns:
            {
                'status': 'success' | 'no_match' | 'error',
                'query': original query,
                'retrieved_chunks': [
                    {
                        'text': chunk text,
                        'metadata': metadata dict,
                        'similarity': float 0-1,
                        'quality_score': float 0-1,
                        'source': 'title - category'
                    }
                ],
                'retrieval_quality': 'high' | 'medium' | 'low' | 'no_match',
                'message': status message
            }
        """
        threshold = similarity_threshold or self.similarity_threshold
        
        try:
            # Generate embedding for query
            query_embedding = self.embedder.encode(query)
            
            # Retrieve more than needed to allow filtering
            fetch_k = min(top_k * 3, 10)
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=fetch_k,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results['documents'][0]:
                return {
                    'status': 'no_match',
                    'query': query,
                    'retrieved_chunks': [],
                    'retrieval_quality': 'no_match',
                    'message': 'No documents found in knowledge base'
                }
            
            # Process and filter results
            candidates = []
            for i in range(len(results['documents'][0])):
                chunk_text = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]
                similarity = 1 - distance
                
                # Quality checks
                if not self._is_valid_chunk(chunk_text, metadata, similarity, threshold):
                    continue
                
                quality_score = self._calculate_quality_score(
                    chunk_text, 
                    metadata, 
                    similarity
                )
                
                candidates.append({
                    'text': chunk_text.strip(),
                    'metadata': metadata,
                    'similarity': round(similarity, 4),
                    'quality_score': round(quality_score, 4),
                    'source': f"{metadata.get('title', 'Unknown')} - {metadata.get('category', 'General')}"
                })
            
            # Sort by quality score and take top_k
            candidates.sort(key=lambda x: x['quality_score'], reverse=True)
            retrieved = candidates[:top_k]
            
            if not retrieved:
                return {
                    'status': 'no_match',
                    'query': query,
                    'retrieved_chunks': [],
                    'retrieval_quality': 'no_match',
                    'message': f'No high-quality matches found (threshold: {threshold})'
                }
            
            # Determine overall retrieval quality
            avg_quality = sum(r['quality_score'] for r in retrieved) / len(retrieved)
            if avg_quality > 0.75:
                quality_level = 'high'
            elif avg_quality > 0.6:
                quality_level = 'medium'
            else:
                quality_level = 'low'
            
            return {
                'status': 'success',
                'query': query,
                'retrieved_chunks': retrieved,
                'retrieval_quality': quality_level,
                'average_quality_score': round(avg_quality, 4),
                'message': f'Retrieved {len(retrieved)} relevant chunks with {quality_level} confidence'
            }
        
        except Exception as e:
            logger.error(f"Retrieval error: {str(e)}")
            return {
                'status': 'error',
                'query': query,
                'retrieved_chunks': [],
                'retrieval_quality': 'error',
                'message': f'Retrieval failed: {str(e)}'
            }

    def _is_valid_chunk(
        self,
        text: str,
        metadata: Dict,
        similarity: float,
        threshold: float
    ) -> bool:
        """Validate chunk meets quality criteria."""
        # Check similarity threshold
        if similarity < threshold:
            return False
        
        # Check chunk length (not empty/too small)
        if len(text.strip()) < self.min_chunk_length:
            return False
        
        # Check metadata completeness
        required_fields = ['title', 'category', 'source_url']
        if not all(metadata.get(field) for field in required_fields):
            logger.warning(f"Incomplete metadata in chunk: {metadata}")
            return False
        
        return True

    def _calculate_quality_score(
        self,
        text: str,
        metadata: Dict,
        similarity: float
    ) -> float:
        """
        Calculate composite quality score (0-1).
        Combines: similarity, text length, metadata completeness.
        """
        # Base: similarity (60% weight)
        score = similarity * 0.6
        
        # Bonus for content length (20% weight)
        # Longer, more substantive chunks score higher
        text_len_bonus = min(len(text.split()) / 200, 1.0) * 0.2
        score += text_len_bonus
        
        # Bonus for metadata completeness (20% weight)
        metadata_fields = ['title', 'category', 'source_url', 'chunk_index']
        complete_fields = sum(1 for f in metadata_fields if metadata.get(f))
        metadata_bonus = (complete_fields / len(metadata_fields)) * 0.2
        score += metadata_bonus
        
        return min(score, 1.0)


# Test suite
if __name__ == "__main__":
    import json
    
    retriever = RAGRetriever(similarity_threshold=0.6)
    
    test_queries = [
        ("I modified the login flow", "Authentication changes"),
        ("I added a new API endpoint", "API security"),
        ("I changed how passwords are stored", "Cryptographic failures"),
        ("How to prevent SQL injection", "Injection attacks"),
        ("I updated dependencies", "Supply chain security"),
    ]
    
    print("\n" + "=" * 80)
    print(" BLT-Preflight RAG Retrieval Test Suite")
    print("=" * 80 + "\n")
    
    test_results = []
    for query, intent in test_queries:
        print(f"Query: {query}")
        print(f"Intent: {intent}\n")
        
        result = retriever.retrieve(query, top_k=2)
        test_results.append({
            'query': query,
            'intent': intent,
            'retrieval_quality': result['retrieval_quality'],
            'chunks_retrieved': len(result['retrieved_chunks']),
            'average_quality': result.get('average_quality_score', 0)
        })
        
        print(f"Status: {result['status']}")
        print(f"Retrieval Quality: {result['retrieval_quality']}")
        print(f"Message: {result['message']}\n")
        
        if result['retrieved_chunks']:
            for i, chunk in enumerate(result['retrieved_chunks'], 1):
                print(f"  [{i}] {chunk['source']}")
                print(f"      Similarity: {chunk['similarity']:.3f} | Quality: {chunk['quality_score']:.3f}")
                print(f"      Preview: {chunk['text'][:150]}...\n")
        
        print("-" * 80 + "\n")
    
    # Summary
    print("=" * 80)
    print(" Test Summary")
    print("=" * 80)
    print(json.dumps(test_results, indent=2))
    
    high_quality_count = sum(1 for r in test_results if r['retrieval_quality'] in ['high', 'medium'])
    print(f"\n✓ High/Medium Quality Retrievals: {high_quality_count}/{len(test_results)}")
    print("=" * 80 + "\n")