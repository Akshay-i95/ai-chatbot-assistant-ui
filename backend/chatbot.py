"""
AI Chatbot Interface - Phase 3 Implementation
Chunk-level retrieval with precise context for accurate responses

This module provides:
- Intelligent query processing and chunk retrieval
- Source attribution and citation system
- Context optimization for LLM responses
- Multi-turn conversation support
- Response quality assessment
- PDF download functionality via Azure Blob Storage
"""

import os
import sys
import logging
import time
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import re

# Import Azure download service
try:
    from azure_blob_service import create_azure_download_service
    AZURE_DOWNLOAD_AVAILABLE = True
except ImportError:
    AZURE_DOWNLOAD_AVAILABLE = False

# Fix Windows Unicode issues
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# For LLM integration (placeholder - can be replaced with actual LLM)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class AIChhatbotInterface:
    def __init__(self, vector_db_manager, config: Dict):
        """Initialize AI chatbot with enhanced vector retrieval"""
        try:
            # Setup logging first
            self.logger = logging.getLogger(__name__)
            
            self.vector_db = vector_db_manager
            self.config = config
            
            # Configuration
            self.max_context_chunks = config.get('max_context_chunks', 5)
            self.max_context_length = config.get('max_context_length', 4000)
            self.min_similarity_threshold = config.get('min_similarity_threshold', 0.35)  # Lowered for better recall
            self.enable_citations = config.get('enable_citations', True)
            self.enable_context_expansion = config.get('enable_context_expansion', True)
            
            # LLM Configuration
            self.llm_model = config.get('llm_model', 'gpt-3.5-turbo')
            self.max_response_tokens = config.get('max_response_tokens', 1000)
            self.temperature = config.get('temperature', 0.7)
            
            # Initialize Azure download service
            self.azure_service = None
            if AZURE_DOWNLOAD_AVAILABLE:
                try:
                    self.logger.info("🔄 Initializing Azure download service...")
                    
                    # Debug: Log Azure configuration
                    azure_config = {
                        'azure_connection_string': config.get('azure_connection_string'),
                        'azure_account_name': config.get('azure_account_name'),
                        'azure_account_key': config.get('azure_account_key'),
                        'azure_container_name': config.get('azure_container_name'),
                        'azure_folder_path': config.get('azure_folder_path')
                    }
                    
                    # Log config status (safely)
                    self.logger.info(f"Azure Account Name: {'✅' if azure_config['azure_account_name'] else '❌'}")
                    self.logger.info(f"Azure Container: {'✅' if azure_config['azure_container_name'] else '❌'}")
                    self.logger.info(f"Azure Connection String: {'✅' if azure_config['azure_connection_string'] else '❌'}")
                    self.logger.info(f"Azure Account Key: {'✅' if azure_config['azure_account_key'] else '❌'}")
                    
                    self.azure_service = create_azure_download_service(azure_config)
                    if self.azure_service:
                        self.logger.info("✅ Azure download service initialized successfully")
                        
                        # Test service
                        stats = self.azure_service.get_download_stats()
                        self.logger.info(f"📁 Found {stats.get('total_pdf_files', 0)} PDF files in Azure storage")
                    else:
                        self.logger.warning("⚠️ Azure download service initialization returned None")
                except Exception as e:
                    self.logger.warning(f"⚠️ Azure download service initialization failed: {str(e)}")
                    import traceback
                    self.logger.debug(traceback.format_exc())
            else:
                self.logger.warning("⚠️ Azure Storage SDK not available for download functionality")
            
            # Conversation state
            self.conversation_history = []
            self.session_stats = {
                'queries_processed': 0,
                'chunks_retrieved': 0,
                'average_response_time': 0,
                'session_start': datetime.now().isoformat()
            }
            
            self.logger.info("✅ AI Chatbot Interface initialized with chunk-level retrieval")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize chatbot: {str(e)}")
            raise
    
    def process_query(self, user_query: str, include_context: bool = True) -> Dict:
        """Process user query and generate response with chunk-level retrieval"""
        try:
            start_time = time.time()
            self.session_stats['queries_processed'] += 1
            
            self.logger.info(f"🤖 Processing query: {user_query[:100]}...")
            
            # Step 1: Query preprocessing
            processed_query = self._preprocess_query(user_query)
            
            # Step 2: Retrieve relevant chunks
            relevant_chunks = self._retrieve_relevant_chunks(processed_query)
            
            if not relevant_chunks:
                return self._generate_no_results_response(user_query)
            
            # Step 3: Expand context if needed
            if self.enable_context_expansion and len(relevant_chunks) < self.max_context_chunks:
                relevant_chunks = self._expand_context(relevant_chunks)
            
            # Step 4: Optimize context for LLM
            optimized_context = self._optimize_context_for_llm(relevant_chunks, processed_query)
            
            # Step 5: Generate response
            response = self._generate_llm_response(processed_query, optimized_context)
            
            # Step 6: Add citations and source attribution
            if self.enable_citations:
                response = self._add_citations(response, relevant_chunks)
            
            # Step 7: Update conversation history
            self._update_conversation_history(user_query, response, relevant_chunks)
            
            # Calculate response time
            response_time = time.time() - start_time
            self._update_session_stats(response_time, len(relevant_chunks))
            
            result = {
                'query': user_query,
                'response': response,
                'reasoning': getattr(self, '_last_reasoning', ''),
                'sources': self._format_sources(relevant_chunks),
                'chunks_used': len(relevant_chunks),
                'response_time': response_time,
                'confidence': self._calculate_confidence(relevant_chunks),
                'context_used': True,
                'model_used': getattr(self, '_last_model_used', 'enhanced_fallback'),
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ Query processed in {response_time:.2f}s using {len(relevant_chunks)} chunks")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Query processing failed: {str(e)}")
            return {
                'query': user_query,
                'response': f"I apologize, but I encountered an error processing your query: {str(e)}",
                'sources': [],
                'chunks_used': 0,
                'response_time': 0,
                'confidence': 0,
                'error': str(e)
            }
    
    def _preprocess_query(self, query: str) -> str:
        """Enhanced preprocess and enhance user query for better retrieval"""
        try:
            # Clean and normalize query
            processed_query = query.strip().lower()
            
            # Remove common question patterns to extract core terms
            question_patterns = [
                r'^what\\s+(is|are|do|does|can)\\s+',
                r'^how\\s+(do|does|can|to)\\s+',
                r'^tell\\s+me\\s+about\\s+',
                r'^explain\\s+',
                r'^describe\\s+',
                r'^define\\s+',
                r'^what\\s+type\\s+of\\s+',
                r'^what\\s+types\\s+of\\s+',
                r'^different\\s+types\\s+of\\s+',
                r'^list\\s+of\\s+',
                r'\\?$'  # Remove question marks
            ]
            
            # Apply pattern removal
            for pattern in question_patterns:
                processed_query = re.sub(pattern, '', processed_query, flags=re.IGNORECASE)
            
            # Clean up extra spaces
            processed_query = ' '.join(processed_query.split())
            
            # Fix common typos in educational terms
            typo_fixes = {
                'assesment': 'assessment',
                'assesments': 'assessments',
                'evalution': 'evaluation',
                'evalutions': 'evaluations',
                'formative assesment': 'formative assessment',
                'summative assesment': 'summative assessment'
            }
            
            for typo, correct in typo_fixes.items():
                processed_query = re.sub(rf'\\b{typo}\\b', correct, processed_query, flags=re.IGNORECASE)
            
            # Expand abbreviations and common terms
            abbreviations = {
                'AI': 'artificial intelligence',
                'ML': 'machine learning',
                'NLP': 'natural language processing',
                'API': 'application programming interface'
            }
            
            for abbrev, full_form in abbreviations.items():
                processed_query = re.sub(rf'\\b{abbrev}\\b', full_form, processed_query, flags=re.IGNORECASE)
            
            # Add educational context for better matching
            if 'formative' in processed_query and 'assessment' in processed_query:
                processed_query += ' ongoing assessment assessment for learning continuous evaluation'
            elif 'summative' in processed_query and 'assessment' in processed_query:
                processed_query += ' final assessment assessment of learning end evaluation'
            elif 'assessment' in processed_query:
                processed_query += ' evaluation testing grading'
            elif 'evaluation' in processed_query:
                processed_query += ' assessment testing'
            
            # Add context from conversation history
            if self.conversation_history:
                recent_context = self._get_conversation_context()
                if recent_context:
                    processed_query = f"{recent_context} {processed_query}"
            
            return processed_query.strip()
            
        except Exception as e:
            self.logger.warning(f"⚠️ Query preprocessing failed: {str(e)}")
            return query
    
    def _retrieve_relevant_chunks(self, query: str) -> List[Dict]:
        """Retrieve most relevant chunks using enhanced vector search"""
        try:
            # Primary search with higher top_k for better coverage
            primary_results = self.vector_db.search_similar_chunks(
                query=query,
                top_k=self.max_context_chunks * 2  # Get more candidates
            )
            
            # Filter by similarity threshold
            filtered_results = [
                chunk for chunk in primary_results
                if chunk.get('similarity_score', 0) >= self.min_similarity_threshold
            ]
            
            # If we have too few results, try alternative strategies
            if len(filtered_results) < 2 and primary_results:
                # Strategy 1: Lower the threshold
                lower_threshold = max(0.25, self.min_similarity_threshold - 0.15)
                filtered_results = [
                    chunk for chunk in primary_results
                    if chunk.get('similarity_score', 0) >= lower_threshold
                ]
                
                # Strategy 2: If still no results, extract keywords and try again
                if not filtered_results:
                    keywords = self._extract_core_keywords(query)
                    if keywords:
                        keyword_query = ' '.join(keywords)
                        keyword_results = self.vector_db.search_similar_chunks(
                            query=keyword_query,
                            top_k=self.max_context_chunks * 2
                        )
                        
                        filtered_results = [
                            chunk for chunk in keyword_results
                            if chunk.get('similarity_score', 0) >= 0.2  # Very low threshold for keyword search
                        ]
            
            # Limit to max context chunks
            relevant_chunks = filtered_results[:self.max_context_chunks]
            
            self.logger.info(f"🔍 Retrieved {len(relevant_chunks)} relevant chunks (threshold: {self.min_similarity_threshold})")
            
            return relevant_chunks
            
        except Exception as e:
            self.logger.error(f"❌ Chunk retrieval failed: {str(e)}")
            return []
    
    def _extract_core_keywords(self, query: str) -> List[str]:
        """Extract core keywords from query for fallback search"""
        try:
            # Remove stop words and extract meaningful terms
            words = re.findall(r'\\b\\w{3,}\\b', query.lower())
            
            stop_words = {
                'what', 'is', 'are', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                'of', 'with', 'by', 'from', 'how', 'does', 'do', 'can', 'will', 'would', 
                'tell', 'me', 'about', 'explain', 'describe', 'give', 'information', 'different',
                'types', 'kind', 'kinds', 'type'
            }
            
            keywords = [word for word in words if word not in stop_words and len(word) > 3]
            
            # Prioritize educational terms
            educational_terms = ['assessment', 'formative', 'summative', 'evaluation', 'testing', 'grading', 'student', 'learning', 'teaching']
            priority_keywords = [kw for kw in keywords if kw in educational_terms]
            other_keywords = [kw for kw in keywords if kw not in educational_terms]
            
            return priority_keywords + other_keywords[:3]  # Max 3 additional keywords
            
        except Exception:
            return []
    
    def _expand_context(self, chunks: List[Dict]) -> List[Dict]:
        """Expand context by retrieving neighboring chunks"""
        try:
            expanded_chunks = list(chunks)  # Start with original chunks
            
            for chunk in chunks:
                chunk_id = chunk.get('metadata', {}).get('chunk_id')
                if chunk_id:
                    # Get neighboring chunks for additional context
                    neighbors = self.vector_db.get_context_chunks(chunk_id, context_size=1)
                    
                    for neighbor in neighbors:
                        # Avoid duplicates
                        neighbor_id = neighbor.get('metadata', {}).get('chunk_id')
                        if not any(c.get('metadata', {}).get('chunk_id') == neighbor_id for c in expanded_chunks):
                            # Add with lower relevance score
                            neighbor['similarity_score'] = chunk.get('similarity_score', 0) * 0.8
                            neighbor['relevance_score'] = chunk.get('relevance_score', 0) * 0.8
                            neighbor['context_chunk'] = True
                            expanded_chunks.append(neighbor)
            
            # Sort by relevance and limit
            expanded_chunks.sort(key=lambda x: x.get('relevance_score', x.get('similarity_score', 0)), reverse=True)
            
            return expanded_chunks[:self.max_context_chunks]
            
        except Exception as e:
            self.logger.warning(f"⚠️ Context expansion failed: {str(e)}")
            return chunks
    
    def _optimize_context_for_llm(self, chunks: List[Dict], query: str) -> str:
        """Optimize retrieved chunks into coherent context for LLM"""
        try:
            context_parts = []
            current_length = 0
            
            # Sort chunks by relevance and document order
            sorted_chunks = self._sort_chunks_for_context(chunks)
            
            for i, chunk in enumerate(sorted_chunks):
                chunk_text = chunk.get('text', '')
                chunk_length = len(chunk_text)
                
                # Check if adding this chunk would exceed max context length
                if current_length + chunk_length > self.max_context_length and context_parts:
                    break
                
                # Format chunk with source information
                source_file = chunk.get('metadata', {}).get('filename', 'unknown')
                chunk_index = chunk.get('metadata', {}).get('chunk_index', 0)
                
                formatted_chunk = f"[Source: {source_file}, Section {int(chunk_index) + 1}]\\n{chunk_text}\\n"
                
                context_parts.append(formatted_chunk)
                current_length += len(formatted_chunk)
            
            # Combine context with clear separators
            optimized_context = "\\n--- RELEVANT INFORMATION ---\\n".join(context_parts)
            
            self.logger.info(f"📄 Optimized context: {len(context_parts)} chunks, {current_length} characters")
            
            return optimized_context
            
        except Exception as e:
            self.logger.error(f"❌ Context optimization failed: {str(e)}")
            return ""
    
    def _sort_chunks_for_context(self, chunks: List[Dict]) -> List[Dict]:
        """Sort chunks for optimal context presentation"""
        try:
            # Group by source document
            doc_groups = {}
            for chunk in chunks:
                filename = chunk.get('metadata', {}).get('filename', 'unknown')
                if filename not in doc_groups:
                    doc_groups[filename] = []
                doc_groups[filename].append(chunk)
            
            # Sort chunks within each document by chunk index
            sorted_chunks = []
            for filename, doc_chunks in doc_groups.items():
                doc_chunks.sort(key=lambda x: x.get('metadata', {}).get('chunk_index', 0))
                sorted_chunks.extend(doc_chunks)
            
            # Sort groups by highest relevance score
            sorted_chunks.sort(key=lambda x: x.get('relevance_score', x.get('similarity_score', 0)), reverse=True)
            
            return sorted_chunks
            
        except Exception as e:
            self.logger.warning(f"⚠️ Chunk sorting failed: {str(e)}")
            return chunks
    
    def _generate_llm_response(self, query: str, context: str) -> str:
        """Generate response using LLM service with optimized context"""
        try:
            # Try to use LLM service if available
            if hasattr(self, 'llm_service') and self.llm_service:
                try:
                    self.logger.info("🤖 Using LLM service for response generation...")
                    llm_response = self.llm_service.generate_response(
                        query=query,
                        context=context,
                        conversation_history=[]
                    )
                    
                    if llm_response.get('response'):
                        self.logger.info("✅ LLM service generated response successfully")
                        # Store reasoning and model info for later use
                        self._last_reasoning = llm_response.get('reasoning', '')
                        self._last_model_used = llm_response.get('model_used', 'llm_service')
                        return llm_response['response']
                    else:
                        self.logger.warning("⚠️ LLM service failed, using fallback")
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ LLM service error: {str(e)}, using fallback")
            
            # Fallback: Generate a structured response based on context
            self.logger.info("🔄 Using enhanced fallback response generation...")
            self._last_reasoning = "Using document-based analysis to provide response"
            self._last_model_used = "enhanced_fallback"
            return self._generate_fallback_response(query, context)
            
        except Exception as e:
            self.logger.error(f"❌ LLM response generation failed: {str(e)}")
            self._last_reasoning = "Error in response generation"
            self._last_model_used = "error_fallback"
            return f"I found relevant information but encountered an error generating the response: {str(e)}"
    
    def _generate_fallback_response(self, query: str, context: str) -> str:
        """Generate a ChatGPT-style fallback response when LLM is not available"""
        try:
            # Extract key information from context
            context_lines = context.split('\n')
            content_snippets = []
            sources = []
            
            current_source = None
            for line in context_lines:
                line = line.strip()
                if line.startswith('[Source:'):
                    # Extract source information
                    current_source = line
                elif line and not line.startswith('---') and len(content_snippets) < 3:
                    # Clean and collect meaningful content
                    clean_content = re.sub(r'<[^>]+>', '', line)
                    clean_content = re.sub(r'&\w+;', ' ', clean_content)
                    clean_content = ' '.join(clean_content.split())
                    
                    if len(clean_content) > 20:
                        content_snippets.append(clean_content)
                        if current_source:
                            sources.append(current_source)
            
            # Generate structured response based on query type
            query_lower = query.lower()
            
            # Determine response structure based on question type
            if any(word in query_lower for word in ['what is', 'what are', 'define', 'definition']):
                # Definition-style response
                if content_snippets:
                    main_content = content_snippets[0]
                    response = f"**{query.replace('?', '').title()}**\n\n"
                    response += f"{main_content}\n\n"
                    
                    if len(content_snippets) > 1:
                        response += "**Additional Information:**\n"
                        for snippet in content_snippets[1:]:
                            response += f"• {snippet}\n"
                    
                    return response
                    
            elif any(word in query_lower for word in ['how', 'steps', 'process', 'method']):
                # Process/How-to style response
                response = f"**{query.replace('?', '')}**\n\n"
                response += "Based on the available information:\n\n"
                
                for i, snippet in enumerate(content_snippets, 1):
                    response += f"**{i}.** {snippet}\n\n"
                    
                return response
                
            elif any(word in query_lower for word in ['why', 'reason', 'cause', 'purpose']):
                # Explanation-style response
                response = f"**{query.replace('?', '')}**\n\n"
                if content_snippets:
                    response += f"{content_snippets[0]}\n\n"
                    
                    if len(content_snippets) > 1:
                        response += "**Key Points:**\n"
                        for snippet in content_snippets[1:]:
                            response += f"• {snippet}\n"
                            
                return response
                
            else:
                # General informational response
                if content_snippets:
                    response = f"Based on the available documents:\n\n"
                    response += f"**{content_snippets[0]}**\n\n"
                    
                    if len(content_snippets) > 1:
                        response += "**Additional details include:**\n"
                        for snippet in content_snippets[1:]:
                            response += f"• {snippet}\n"
                            
                    return response
            
            return "I found relevant information in the documents, but I need more specific context to provide a detailed answer."
            
        except Exception as e:
            self.logger.error(f"❌ Fallback response generation failed: {str(e)}")
            return "I found some information but encountered an error processing it. Please try rephrasing your question."
    
    def _add_citations(self, response: str, chunks: List[Dict]) -> str:
        """Add citations and source attribution to response"""
        try:
            # Don't add citations to the response text anymore
            # Citations will be handled separately in the sources section
            return response
            
        except Exception as e:
            self.logger.warning(f"⚠️ Citation addition failed: {str(e)}")
            return response
    
    def _calculate_confidence(self, chunks: List[Dict]) -> float:
        """Calculate confidence score based on chunk relevance and quantity"""
        try:
            if not chunks:
                return 0.0
            
            # Average similarity score
            avg_similarity = sum(chunk.get('similarity_score', 0) for chunk in chunks) / len(chunks)
            
            # Quantity bonus (more relevant chunks = higher confidence)
            quantity_bonus = min(0.2, len(chunks) * 0.05)
            
            # Source diversity bonus (multiple sources = higher confidence)
            unique_sources = len(set(
                chunk.get('metadata', {}).get('filename', 'unknown') for chunk in chunks
            ))
            diversity_bonus = min(0.1, unique_sources * 0.03)
            
            confidence = avg_similarity + quantity_bonus + diversity_bonus
            
            return min(1.0, confidence)
            
        except Exception:
            return 0.5  # Default confidence
    
    def _format_sources(self, chunks: List[Dict]) -> List[Dict]:
        """Format source information for response with download URLs"""
        try:
            sources = []
            seen_sources = set()
            
            for chunk in chunks:
                metadata = chunk.get('metadata', {})
                filename = metadata.get('filename', 'unknown')
                
                if filename not in seen_sources:
                    source_info = {
                        'filename': filename,
                        'total_pages': metadata.get('file_pages', 0),
                        'extraction_method': metadata.get('extraction_method', 'unknown'),
                        'ocr_used': metadata.get('ocr_used', False),
                        'relevance_score': chunk.get('similarity_score', 0),
                        'download_url': None,
                        'download_available': False,
                        'file_size_mb': None
                    }
                    
                    # Generate download URL if Azure service is available
                    if self.azure_service and filename != 'unknown':
                        try:
                            # Get blob info first
                            blob_info = self.azure_service.get_blob_info(filename)
                            if blob_info and blob_info.get('exists'):
                                # Generate download URL
                                download_url = self.azure_service.generate_download_url(filename, expiry_hours=2)
                                if download_url:
                                    source_info.update({
                                        'download_url': download_url,
                                        'download_available': True,
                                        'file_size_mb': blob_info.get('size_mb'),
                                        'last_modified': blob_info.get('last_modified')
                                    })
                                    self.logger.info(f"✅ Generated download URL for: {filename}")
                                else:
                                    self.logger.warning(f"⚠️ Failed to generate download URL for: {filename}")
                            else:
                                self.logger.warning(f"⚠️ File not found in Azure storage: {filename}")
                        except Exception as e:
                            self.logger.warning(f"⚠️ Error generating download URL for {filename}: {str(e)}")
                    
                    sources.append(source_info)
                    seen_sources.add(filename)
            
            return sources
            
        except Exception as e:
            self.logger.warning(f"⚠️ Source formatting failed: {str(e)}")
            return []
    
    def _generate_no_results_response(self, query: str) -> Dict:
        """Generate response when no relevant chunks are found"""
        return {
            'query': query,
            'response': "I couldn't find information about that in the documents. Try asking about something else or rephrasing your question.",
            'sources': [],
            'chunks_used': 0,
            'response_time': 0,
            'confidence': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _update_conversation_history(self, query: str, response: str, chunks: List[Dict]):
        """Update conversation history for context in future queries"""
        try:
            # Keep last 5 interactions for context
            self.conversation_history.append({
                'query': query,
                'response': response,
                'chunks_used': len(chunks),
                'timestamp': datetime.now().isoformat()
            })
            
            # Limit history size
            if len(self.conversation_history) > 5:
                self.conversation_history = self.conversation_history[-5:]
                
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to update conversation history: {str(e)}")
    
    def _get_conversation_context(self) -> str:
        """Get context from recent conversation for query enhancement"""
        try:
            if not self.conversation_history:
                return ""
            
            # Get last 2 interactions
            recent_interactions = self.conversation_history[-2:]
            context_parts = []
            
            for interaction in recent_interactions:
                # Extract key topics from previous queries
                query = interaction['query']
                key_terms = self._extract_key_terms(query)
                if key_terms:
                    context_parts.extend(key_terms)
            
            return " ".join(context_parts[:10])  # Limit context length
            
        except Exception:
            return ""
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text for context"""
        try:
            # Simple keyword extraction (can be enhanced with NLP)
            words = re.findall(r'\\b\\w{3,}\\b', text.lower())
            
            # Filter out common words
            stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'had', 'but', 'what', 'use', 'how', 'when', 'where', 'why', 'who'}
            key_terms = [word for word in words if word not in stop_words and len(word) > 3]
            
            return key_terms[:5]  # Return top 5 terms
            
        except Exception:
            return []
    
    def _update_session_stats(self, response_time: float, chunks_retrieved: int):
        """Update session statistics"""
        try:
            self.session_stats['chunks_retrieved'] += chunks_retrieved
            
            # Update average response time
            current_avg = self.session_stats['average_response_time']
            query_count = self.session_stats['queries_processed']
            
            new_avg = (current_avg * (query_count - 1) + response_time) / query_count
            self.session_stats['average_response_time'] = new_avg
            
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to update session stats: {str(e)}")
    
    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        return {
            **self.session_stats,
            'conversation_turns': len(self.conversation_history),
            'session_duration_minutes': (datetime.now() - datetime.fromisoformat(self.session_stats['session_start'])).total_seconds() / 60
        }
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = []
        self.logger.info("🔄 Conversation history reset")
    
    def generate_pdf_download_url(self, filename: str, expiry_hours: int = 2) -> Optional[str]:
        """
        Generate a secure download URL for a specific PDF file
        
        Args:
            filename: Name of the PDF file
            expiry_hours: Hours until the download URL expires (default: 2 hours)
            
        Returns:
            Secure download URL or None if not available
        """
        try:
            if not self.azure_service:
                self.logger.warning("⚠️ Azure download service not available")
                return None
            
            download_url = self.azure_service.generate_download_url(filename, expiry_hours)
            
            if download_url:
                self.logger.info(f"✅ Generated download URL for: {filename}")
            else:
                self.logger.warning(f"⚠️ Could not generate download URL for: {filename}")
            
            return download_url
            
        except Exception as e:
            self.logger.error(f"❌ Error generating download URL for {filename}: {str(e)}")
            return None
    
    def get_pdf_info(self, filename: str) -> Optional[Dict]:
        """
        Get information about a PDF file in Azure storage
        
        Args:
            filename: Name of the PDF file
            
        Returns:
            Dictionary with file information or None if not available
        """
        try:
            if not self.azure_service:
                return None
            
            return self.azure_service.get_blob_info(filename)
            
        except Exception as e:
            self.logger.error(f"❌ Error getting PDF info for {filename}: {str(e)}")
            return None
    
    def list_available_pdfs(self) -> List[Dict]:
        """
        List all available PDF files in Azure storage
        
        Returns:
            List of dictionaries with PDF file information
        """
        try:
            if not self.azure_service:
                self.logger.warning("⚠️ Azure download service not available")
                return []
            
            return self.azure_service.list_available_pdfs()
            
        except Exception as e:
            self.logger.error(f"❌ Error listing PDF files: {str(e)}")
            return []
    
    def batch_generate_download_urls(self, filenames: List[str], expiry_hours: int = 2) -> Dict[str, Optional[str]]:
        """
        Generate download URLs for multiple PDF files at once
        
        Args:
            filenames: List of PDF filenames
            expiry_hours: Hours until the download URLs expire (default: 2 hours)
            
        Returns:
            Dictionary mapping filenames to download URLs (or None if failed)
        """
        try:
            if not self.azure_service:
                self.logger.warning("⚠️ Azure download service not available")
                return {filename: None for filename in filenames}
            
            return self.azure_service.batch_generate_download_urls(filenames, expiry_hours)
            
        except Exception as e:
            self.logger.error(f"❌ Error generating batch download URLs: {str(e)}")
            return {filename: None for filename in filenames}
    
    def get_download_service_stats(self) -> Dict:
        """
        Get Azure download service statistics
        
        Returns:
            Dictionary with service statistics
        """
        try:
            if not self.azure_service:
                return {
                    'service_available': False,
                    'reason': 'Azure download service not initialized'
                }
            
            return self.azure_service.get_download_stats()
            
        except Exception as e:
            self.logger.error(f"❌ Error getting download service stats: {str(e)}")
            return {
                'service_available': False,
                'error': str(e)
            }

def main():
    """Run the AI Chatbot Interface as standalone application"""
    try:
        print("=" * 50)
        print("AI CHATBOT - Enhanced with Chunk-Level Retrieval")
        print("=" * 50)
        print("Ask questions about the processed documents.")
        print("Type 'quit', 'exit', or 'bye' to end the session.")
        print("Type 'stats' to see session statistics.")
        print("Type 'reset' to clear conversation history.")
        print("Type 'pdfs' to list available PDF files.")
        print("Type 'download <filename>' to get a download link.")
        print("-" * 50)
        
        # Load configuration
        from dotenv import load_dotenv
        load_dotenv()
        
        config = {
            'vector_db_path': './vector_store',
            'collection_name': 'pdf_chunks',
            'embedding_model': 'all-MiniLM-L6-v2',
            'max_context_chunks': 4,
            'min_similarity_threshold': 0.35,  # Lowered for better recall
            'enable_citations': True,
            'enable_context_expansion': True,
            'max_context_length': 4000,
            'max_response_tokens': 1000,
            'temperature': 0.7,
            # Azure configuration from environment
            'azure_connection_string': os.getenv('AZURE_STORAGE_CONNECTION_STRING'),
            'azure_account_name': os.getenv('AZURE_STORAGE_ACCOUNT_NAME'),
            'azure_account_key': os.getenv('AZURE_STORAGE_ACCOUNT_KEY'),
            'azure_container_name': os.getenv('AZURE_STORAGE_CONTAINER_NAME'),
            'azure_folder_path': os.getenv('AZURE_BLOB_FOLDER_PATH')
        }
        
        # Initialize components
        print("Initializing vector database...")
        from vector_db import EnhancedVectorDBManager
        vector_db = EnhancedVectorDBManager(config)
        
        print("Initializing chatbot...")
        chatbot = AIChhatbotInterface(vector_db, config)
        
        print("Ready to answer questions!")
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\nGoodbye! Thanks for using the AI Chatbot.")
                    break
                
                elif user_input.lower() == 'stats':
                    stats = chatbot.get_session_stats()
                    print("\n" + "=" * 40)
                    print("SESSION STATISTICS")
                    print("=" * 40)
                    print(f"Queries processed: {stats['queries_processed']}")
                    print(f"Chunks retrieved: {stats['chunks_retrieved']}")
                    print(f"Conversation turns: {stats['conversation_turns']}")
                    print(f"Average response time: {stats['average_response_time']:.2f}s")
                    print(f"Session duration: {stats['session_duration_minutes']:.1f} minutes")
                    continue
                
                elif user_input.lower() == 'reset':
                    chatbot.reset_conversation()
                    print("\nConversation history cleared.")
                    continue
                
                elif user_input.lower() == 'pdfs':
                    print("\n" + "=" * 40)
                    print("AVAILABLE PDF FILES")
                    print("=" * 40)
                    
                    pdfs = chatbot.list_available_pdfs()
                    if pdfs:
                        for i, pdf in enumerate(pdfs, 1):
                            print(f"{i}. {pdf['filename']} ({pdf.get('size_mb', 0):.1f} MB)")
                        
                        # Show download service stats
                        stats = chatbot.get_download_service_stats()
                        if stats.get('service_available'):
                            print(f"\nTotal: {stats.get('total_pdf_files', 0)} files, {stats.get('total_size_mb', 0):.1f} MB")
                        else:
                            print(f"\nDownload service: {stats.get('reason', 'Not available')}")
                    else:
                        print("No PDF files found or download service not available.")
                    continue
                
                elif user_input.lower().startswith('download '):
                    filename = user_input[9:].strip()  # Remove 'download ' prefix
                    
                    if not filename:
                        print("Please specify a filename: download <filename>")
                        continue
                    
                    print(f"\nGenerating download link for: {filename}")
                    
                    # Get file info first
                    file_info = chatbot.get_pdf_info(filename)
                    if file_info and file_info.get('exists'):
                        # Generate download URL
                        download_url = chatbot.generate_pdf_download_url(filename, expiry_hours=2)
                        
                        if download_url:
                            print("\n" + "=" * 50)
                            print("DOWNLOAD LINK GENERATED")
                            print("=" * 50)
                            print(f"File: {filename}")
                            print(f"Size: {file_info.get('size_mb', 0):.1f} MB")
                            print(f"Expires: 2 hours from now")
                            print(f"\nDownload URL:")
                            print(download_url)
                            print("\n⚠️  This link expires in 2 hours for security.")
                        else:
                            print(f"❌ Failed to generate download link for: {filename}")
                    else:
                        print(f"❌ File not found: {filename}")
                        print("Use 'pdfs' command to see available files.")
                    continue
                
                # Process the query
                print("\nAI: Searching for relevant information...")
                
                # Try the original query first
                response = chatbot.process_query(user_input)
                
                # If no results, try with alternative phrasings
                if response.get('chunks_used', 0) == 0:
                    # Try simpler keywords
                    simple_query = user_input.lower()
                    simple_query = simple_query.replace("what are", "").replace("how does", "").replace("tell me about", "")
                    simple_query = simple_query.replace("different types of", "").replace("?", "").strip()
                    
                    if simple_query != user_input.lower():
                        print("Trying alternative search terms...")
                        response = chatbot.process_query(simple_query)
                
                # Display response
                print("\n" + "-" * 50)
                print("AI Response:")
                print("-" * 50)
                print(response['response'])
                
                if response.get('sources'):
                    print("\nSources:")
                    for i, source in enumerate(response['sources'][:3], 1):
                        relevance = source.get('relevance_score', source.get('similarity_score', 0))
                        print(f"  {i}. {source['filename']} (Relevance: {relevance:.2f})")
                        
                        # Show download info if available
                        if source.get('download_available'):
                            size_info = f" - {source.get('file_size_mb', 0):.1f} MB" if source.get('file_size_mb') else ""
                            print(f"     📥 Download available{size_info}")
                            print(f"     URL: {source['download_url']}")
                        elif source['filename'] != 'unknown':
                            print(f"     📄 File: {source['filename']} (download not available)")
                
                print(f"\nQuery Info: {response['chunks_used']} chunks used, "
                      f"Confidence: {response.get('confidence', 0):.2f}, "
                      f"Response time: {response['response_time']:.2f}s")
                
            except KeyboardInterrupt:
                print("\n\nSession interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\nError processing query: {str(e)}")
                continue
        
    except Exception as e:
        print(f"Failed to start chatbot: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
