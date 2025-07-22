"""
Enhanced Vector Database Manager - Phase 3 Implementation
Optimized for chunk-level retrieval and AI chatbot foundation

This module provides:
- Chunk-level vector storage with comprehensive metadata
- Top-K retrieval algorithm for precise context
- Source attribution system
- Multiple vector database backends with enhanced querying
- Similarity search optimization for AI responses
"""

import os
import logging
import time
import uuid
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer

# Vector Databases
try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

class EnhancedVectorDBManager:
    def __init__(self, config: Dict):
        """Initialize enhanced vector database for chunk-level retrieval"""
        try:
            self.config = config
            self.db_type = config.get('vector_db_type', 'chromadb').lower()
            self.db_path = config.get('vector_db_path', './vector_store')
            self.collection_name = config.get('collection_name', 'pdf_chunks')  # Changed to chunks
            self.embedding_model_name = config.get('embedding_model', 'all-MiniLM-L6-v2')
            
            # Enhanced configuration for AI chatbot
            self.max_chunk_length = config.get('max_chunk_length', 2000)
            self.top_k_default = config.get('top_k_default', 5)  # Default retrieval count
            self.similarity_threshold = config.get('similarity_threshold', 0.7)
            self.enable_reranking = config.get('enable_reranking', True)
            
            # Setup logging
            self.logger = logging.getLogger(__name__)
            
            # Initialize embedding model
            self.embedding_model = None
            self.embedding_dim = None
            self._initialize_embedding_model()
            
            # Initialize vector database
            self.db_client = None
            self.collection = None
            self._initialize_database()
            
            # Statistics
            self.stats = {
                'chunks_stored': 0,
                'queries_processed': 0,
                'average_query_time': 0,
                'last_update': None
            }
            
            self.logger.info(f"✅ Enhanced Vector DB Manager initialized: {self.db_type}, chunks collection")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize EnhancedVectorDBManager: {str(e)}")
            raise
    
    def _initialize_embedding_model(self):
        """Initialize embedding model optimized for semantic search"""
        try:
            self.logger.info(f"🤖 Loading embedding model: {self.embedding_model_name}")
            
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            
            # Test the model
            test_embedding = self.embedding_model.encode(["test chunk for AI retrieval"], convert_to_numpy=True)
            if test_embedding.shape[1] != self.embedding_dim:
                raise ValueError("Model dimension mismatch")
            
            self.logger.info(f"✅ Embedding model loaded. Dimension: {self.embedding_dim}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load embedding model: {str(e)}")
            raise
    
    def _initialize_database(self):
        """Initialize vector database with chunk-optimized settings"""
        try:
            if self.db_type == 'chromadb':
                self._initialize_chromadb()
            elif self.db_type == 'faiss':
                self._initialize_faiss()
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize {self.db_type} database: {str(e)}")
            raise
    
    def _initialize_chromadb(self):
        """Initialize ChromaDB with enhanced settings for chunks"""
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB not available. Install with: pip install chromadb")
        
        try:
            # Ensure directory exists
            os.makedirs(self.db_path, exist_ok=True)
            
            # Initialize ChromaDB client with persistence
            self.db_client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Create or get collection with enhanced metadata
            try:
                self.collection = self.db_client.get_collection(
                    name=self.collection_name,
                    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name=self.embedding_model_name
                    )
                )
                self.logger.info(f"✅ Connected to existing ChromaDB collection: {self.collection_name}")
            except:
                self.collection = self.db_client.create_collection(
                    name=self.collection_name,
                    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name=self.embedding_model_name
                    ),
                    metadata={"description": "Enhanced PDF chunks for AI chatbot retrieval"}
                )
                self.logger.info(f"✅ Created new ChromaDB collection: {self.collection_name}")
            
        except Exception as e:
            self.logger.error(f"❌ ChromaDB initialization failed: {str(e)}")
            raise
    
    def _initialize_faiss(self):
        """Initialize FAISS with enhanced indexing for semantic search"""
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not available. Install with: pip install faiss-cpu")
        
        try:
            # Create enhanced FAISS index (HNSW for better semantic search)
            self.faiss_index = faiss.IndexHNSWFlat(self.embedding_dim, 32)
            self.faiss_index.hnsw.efConstruction = 200
            self.faiss_index.hnsw.efSearch = 100
            
            # Metadata storage for FAISS
            self.faiss_metadata = {}
            self.faiss_id_counter = 0
            
            # Try to load existing index
            index_path = os.path.join(self.db_path, "enhanced_chunks.index")
            metadata_path = os.path.join(self.db_path, "enhanced_metadata.json")
            
            if os.path.exists(index_path) and os.path.exists(metadata_path):
                self.faiss_index = faiss.read_index(index_path)
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    self.faiss_metadata = saved_data.get('metadata', {})
                    self.faiss_id_counter = saved_data.get('id_counter', 0)
                self.logger.info(f"✅ Loaded existing FAISS index with {self.faiss_index.ntotal} chunks")
            else:
                os.makedirs(self.db_path, exist_ok=True)
                self.logger.info("✅ Created new FAISS index for enhanced chunks")
            
        except Exception as e:
            self.logger.error(f"❌ FAISS initialization failed: {str(e)}")
            raise
    
    def store_chunks_batch(self, chunks: List[Dict]) -> bool:
        """Store chunks in batch with enhanced metadata for AI retrieval"""
        if not chunks:
            return True
        
        try:
            start_time = time.time()
            
            # Prepare data for batch storage
            texts = []
            metadatas = []
            ids = []
            
            for chunk in chunks:
                # Generate unique ID for chunk
                chunk_id = chunk.get('chunk_id') or f"chunk_{uuid.uuid4().hex[:8]}"
                
                # Prepare text for embedding (combine content with context)
                chunk_text = chunk['text']
                if len(chunk_text) > self.max_chunk_length:
                    chunk_text = chunk_text[:self.max_chunk_length]
                
                # Enhanced metadata for better retrieval
                enhanced_metadata = {
                    # Core identification
                    'chunk_id': chunk_id,
                    'filename': chunk['filename'],
                    'chunk_index': chunk.get('chunk_index', 0),
                    'section_index': chunk.get('section_index', 0),
                    
                    # Content metadata
                    'content_type': chunk.get('content_type', 'general'),
                    'chunk_length': len(chunk_text),
                    'chunk_tokens': chunk.get('chunk_tokens', 0),
                    'preview': chunk.get('preview', chunk_text[:200]),
                    
                    # Source metadata for attribution
                    'file_pages': chunk.get('file_pages', 0),
                    'extraction_method': chunk.get('extraction_method', 'unknown'),
                    'ocr_used': chunk.get('ocr_used', False),
                    'images_processed': chunk.get('images_processed', 0),
                    
                    # Context for better retrieval
                    'previous_chunk_preview': chunk.get('previous_chunk_preview', ''),
                    'next_chunk_preview': chunk.get('next_chunk_preview', ''),
                    
                    # Processing metadata
                    'created_at': chunk.get('created_at', time.time()),
                    'stored_at': time.time()
                }
                
                texts.append(chunk_text)
                metadatas.append(enhanced_metadata)
                ids.append(chunk_id)
            
            # Store based on database type
            if self.db_type == 'chromadb':
                self._store_chunks_chromadb(texts, metadatas, ids)
            elif self.db_type == 'faiss':
                self._store_chunks_faiss(texts, metadatas, ids)
            
            # Update statistics
            self.stats['chunks_stored'] += len(chunks)
            self.stats['last_update'] = datetime.now().isoformat()
            
            processing_time = time.time() - start_time
            self.logger.info(f"✅ Stored {len(chunks)} chunks in {processing_time:.2f}s")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to store chunks batch: {str(e)}")
            return False
    
    def _store_chunks_chromadb(self, texts: List[str], metadatas: List[Dict], ids: List[str]):
        """Store chunks in ChromaDB"""
        try:
            # Convert metadata to ChromaDB format (strings only)
            chroma_metadatas = []
            for metadata in metadatas:
                chroma_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        chroma_metadata[key] = str(value)
                    elif value is not None:
                        chroma_metadata[key] = str(value)
                chroma_metadatas.append(chroma_metadata)
            
            # Store in collection
            self.collection.add(
                documents=texts,
                metadatas=chroma_metadatas,
                ids=ids
            )
            
        except Exception as e:
            self.logger.error(f"❌ ChromaDB storage error: {str(e)}")
            raise
    
    def _store_chunks_faiss(self, texts: List[str], metadatas: List[Dict], ids: List[str]):
        """Store chunks in FAISS"""
        try:
            # Generate embeddings
            embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
            
            # Add to FAISS index
            faiss_ids = []
            for i, (text, metadata, chunk_id) in enumerate(zip(texts, metadatas, ids)):
                faiss_id = self.faiss_id_counter
                self.faiss_id_counter += 1
                
                # Store metadata
                self.faiss_metadata[faiss_id] = {
                    'text': text,
                    'chunk_id': chunk_id,
                    **metadata
                }
                faiss_ids.append(faiss_id)
            
            # Add embeddings to index
            self.faiss_index.add_with_ids(embeddings, np.array(faiss_ids))
            
            # Save index and metadata
            self._save_faiss_index()
            
        except Exception as e:
            self.logger.error(f"❌ FAISS storage error: {str(e)}")
            raise
    
    def _save_faiss_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            index_path = os.path.join(self.db_path, "enhanced_chunks.index")
            metadata_path = os.path.join(self.db_path, "enhanced_metadata.json")
            
            # Save FAISS index
            faiss.write_index(self.faiss_index, index_path)
            
            # Save metadata
            save_data = {
                'metadata': self.faiss_metadata,
                'id_counter': self.faiss_id_counter,
                'updated_at': time.time()
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"❌ Failed to save FAISS index: {str(e)}")
    
    def search_similar_chunks(self, query: str, top_k: int = None, filters: Dict = None) -> List[Dict]:
        """Search for similar chunks optimized for AI chatbot responses"""
        if top_k is None:
            top_k = self.top_k_default
        
        try:
            start_time = time.time()
            
            # Search based on database type
            if self.db_type == 'chromadb':
                results = self._search_chromadb(query, top_k, filters)
            elif self.db_type == 'faiss':
                results = self._search_faiss(query, top_k, filters)
            else:
                return []
            
            # Post-process results for AI optimization
            enhanced_results = self._enhance_search_results(results, query)
            
            # Apply reranking if enabled
            if self.enable_reranking and len(enhanced_results) > 1:
                enhanced_results = self._rerank_results(enhanced_results, query)
            
            # Update statistics
            query_time = time.time() - start_time
            self.stats['queries_processed'] += 1
            current_avg = self.stats['average_query_time']
            self.stats['average_query_time'] = (current_avg * (self.stats['queries_processed'] - 1) + query_time) / self.stats['queries_processed']
            
            self.logger.info(f"🔍 Found {len(enhanced_results)} relevant chunks for query in {query_time:.3f}s")
            
            return enhanced_results
            
        except Exception as e:
            self.logger.error(f"❌ Search failed: {str(e)}")
            return []
    
    def _search_chromadb(self, query: str, top_k: int, filters: Dict = None) -> List[Dict]:
        """Search ChromaDB for similar chunks"""
        try:
            # Prepare where clause for filtering
            where_clause = {}
            if filters:
                for key, value in filters.items():
                    where_clause[key] = str(value)
            
            # Perform search
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_clause if where_clause else None
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    formatted_results.append({
                        'text': doc,
                        'metadata': metadata,
                        'similarity_score': 1 - distance,  # Convert distance to similarity
                        'rank': i + 1
                    })
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"❌ ChromaDB search error: {str(e)}")
            return []
    
    def _search_faiss(self, query: str, top_k: int, filters: Dict = None) -> List[Dict]:
        """Search FAISS for similar chunks"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
            
            # Search FAISS index
            similarities, indices = self.faiss_index.search(query_embedding, min(top_k, self.faiss_index.ntotal))
            
            # Format results
            formatted_results = []
            for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                if idx == -1:  # No more results
                    break
                
                # Convert index to string key for metadata lookup
                metadata = self.faiss_metadata.get(str(idx), {})
                
                # Apply filters if specified
                if filters:
                    skip = False
                    for key, value in filters.items():
                        if metadata.get(key) != str(value):
                            skip = True
                            break
                    if skip:
                        continue
                
                formatted_results.append({
                    'text': metadata.get('text', ''),
                    'metadata': metadata,
                    'similarity_score': float(similarity),
                    'rank': i + 1
                })
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"❌ FAISS search error: {str(e)}")
            return []
    
    def _enhance_search_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Enhance search results with additional context for AI"""
        enhanced_results = []
        
        for result in results:
            try:
                metadata = result['metadata']
                
                # Add source attribution
                source_info = {
                    'source_file': metadata.get('filename', 'unknown'),
                    'chunk_location': f"Chunk {int(metadata.get('chunk_index', 0)) + 1}",
                    'extraction_method': metadata.get('extraction_method', 'unknown'),
                    'content_type': metadata.get('content_type', 'general')
                }
                
                # Add context from neighboring chunks
                context_info = {
                    'previous_context': metadata.get('previous_chunk_preview', ''),
                    'next_context': metadata.get('next_chunk_preview', ''),
                    'section_index': metadata.get('section_index', 0)
                }
                
                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(result, query)
                
                enhanced_result = {
                    'text': result['text'],
                    'similarity_score': result['similarity_score'],
                    'relevance_score': relevance_score,
                    'source_attribution': source_info,
                    'context': context_info,
                    'metadata': metadata,
                    'rank': result['rank']
                }
                
                enhanced_results.append(enhanced_result)
                
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to enhance result: {str(e)}")
                enhanced_results.append(result)
        
        return enhanced_results
    
    def _calculate_relevance_score(self, result: Dict, query: str) -> float:
        """Calculate a relevance score combining similarity and content factors"""
        try:
            # Base similarity score
            base_score = result['similarity_score']
            
            # Content type bonus
            content_type = result['metadata'].get('content_type', 'general')
            content_bonus = 0.1 if content_type in ['conceptual', 'procedural'] else 0.0
            
            # Length penalty for very short or very long chunks
            chunk_length = int(result['metadata'].get('chunk_length', 0))
            if chunk_length < 100:
                length_penalty = 0.1
            elif chunk_length > 1500:
                length_penalty = 0.05
            else:
                length_penalty = 0.0
            
            # OCR penalty (OCR text may be less accurate)
            ocr_penalty = 0.05 if result['metadata'].get('ocr_used') == 'True' else 0.0
            
            # Calculate final score
            relevance_score = base_score + content_bonus - length_penalty - ocr_penalty
            
            return max(0.0, min(1.0, relevance_score))
            
        except Exception:
            return result['similarity_score']
    
    def _rerank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Rerank results using relevance score"""
        try:
            # Sort by relevance score (combination of similarity and relevance factors)
            reranked = sorted(
                results,
                key=lambda x: (x.get('relevance_score', 0), x.get('similarity_score', 0)),
                reverse=True
            )
            
            # Update ranks
            for i, result in enumerate(reranked):
                result['rank'] = i + 1
            
            return reranked
            
        except Exception as e:
            self.logger.warning(f"⚠️ Reranking failed: {str(e)}")
            return results
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """Retrieve a specific chunk by its ID"""
        try:
            if self.db_type == 'chromadb':
                results = self.collection.get(ids=[chunk_id])
                if results['documents'] and results['documents'][0]:
                    return {
                        'text': results['documents'][0],
                        'metadata': results['metadatas'][0]
                    }
            elif self.db_type == 'faiss':
                for metadata in self.faiss_metadata.values():
                    if metadata.get('chunk_id') == chunk_id:
                        return {
                            'text': metadata.get('text', ''),
                            'metadata': metadata
                        }
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Failed to retrieve chunk {chunk_id}: {str(e)}")
            return None
    
    def get_context_chunks(self, chunk_id: str, context_size: int = 2) -> List[Dict]:
        """Get neighboring chunks for additional context"""
        try:
            # Find the target chunk
            target_chunk = self.get_chunk_by_id(chunk_id)
            if not target_chunk:
                return []
            
            filename = target_chunk['metadata'].get('filename')
            chunk_index = int(target_chunk['metadata'].get('chunk_index', 0))
            
            # Search for neighboring chunks
            context_chunks = []
            
            if self.db_type == 'chromadb':
                # Search for chunks from same file with nearby indices
                for i in range(max(0, chunk_index - context_size), chunk_index + context_size + 1):
                    if i != chunk_index:  # Skip the target chunk itself
                        neighbor_id = f"{filename}_{i:03d}"
                        neighbor = self.get_chunk_by_id(neighbor_id)
                        if neighbor:
                            context_chunks.append(neighbor)
            
            elif self.db_type == 'faiss':
                # Search through metadata for neighboring chunks
                for metadata in self.faiss_metadata.values():
                    if (metadata.get('filename') == filename and
                        abs(int(metadata.get('chunk_index', 0)) - chunk_index) <= context_size and
                        metadata.get('chunk_id') != chunk_id):
                        context_chunks.append({
                            'text': metadata.get('text', ''),
                            'metadata': metadata
                        })
            
            # Sort by chunk index
            context_chunks.sort(key=lambda x: int(x['metadata'].get('chunk_index', 0)))
            
            return context_chunks
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get context for chunk {chunk_id}: {str(e)}")
            return []
    
    def get_collection_stats(self) -> Dict:
        """Get detailed statistics about the vector database"""
        try:
            total_chunks = 0
            
            if self.db_type == 'chromadb':
                total_chunks = self.collection.count()
            elif self.db_type == 'faiss':
                total_chunks = self.faiss_index.ntotal
            
            return {
                'database_type': self.db_type,
                'total_chunks': total_chunks,
                'embedding_dimension': self.embedding_dim,
                'embedding_model': self.embedding_model_name,
                'chunks_stored': self.stats['chunks_stored'],
                'queries_processed': self.stats['queries_processed'],
                'average_query_time_ms': self.stats['average_query_time'] * 1000,
                'last_update': self.stats['last_update']
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get collection stats: {str(e)}")
            return {}
    
    def create_search_index(self) -> bool:
        """Create optimized search index for faster retrieval"""
        try:
            if self.db_type == 'faiss' and hasattr(self, 'faiss_index'):
                # Train the index for better performance
                if self.faiss_index.ntotal > 100:
                    self.logger.info("🔧 Optimizing FAISS index for faster search...")
                    # For HNSW index, we can adjust search parameters
                    self.faiss_index.hnsw.efSearch = min(200, self.faiss_index.ntotal)
                    self._save_faiss_index()
                    self.logger.info("✅ FAISS index optimized")
                    return True
            
            elif self.db_type == 'chromadb':
                # ChromaDB handles indexing automatically
                self.logger.info("✅ ChromaDB indexing is automatic")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create search index: {str(e)}")
            return False
