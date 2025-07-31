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
                    self.logger.info("[INIT] Initializing Azure download service...")
                    
                    # Debug: Log Azure configuration
                    azure_config = {
                        'azure_connection_string': config.get('azure_connection_string'),
                        'azure_account_name': config.get('azure_account_name'),
                        'azure_account_key': config.get('azure_account_key'),
                        'azure_container_name': config.get('azure_container_name'),
                        'azure_folder_path': config.get('azure_folder_path')
                    }
                    
                    # Log config status (safely)
                    self.logger.info(f"Azure Account Name: {'OK' if azure_config['azure_account_name'] else 'MISSING'}")
                    self.logger.info(f"Azure Container: {'OK' if azure_config['azure_container_name'] else 'MISSING'}")
                    self.logger.info(f"Azure Connection String: {'OK' if azure_config['azure_connection_string'] else 'MISSING'}")
                    self.logger.info(f"Azure Account Key: {'OK' if azure_config['azure_account_key'] else 'MISSING'}")
                    
                    self.azure_service = create_azure_download_service(azure_config)
                    if self.azure_service:
                        self.logger.info("[SUCCESS] Azure download service initialized successfully")
                        
                        # Test service
                        stats = self.azure_service.get_download_stats()
                        self.logger.info(f"[INFO] Found {stats.get('total_pdf_files', 0)} PDF files in Azure storage")
                    else:
                        self.logger.warning("[WARNING] Azure download service initialization returned None")
                except Exception as e:
                    self.logger.warning(f"[WARNING] Azure download service initialization failed: {str(e)}")
                    import traceback
                    self.logger.debug(traceback.format_exc())
            else:
                self.logger.warning("[WARNING] Azure Storage SDK not available for download functionality")
            
            # SHORT-TERM MEMORY - Thread-based conversation state
            self.conversation_history = []
            self.conversation_memory = {
                'topics_discussed': {},  # Topic -> [message_indices] 
                'key_concepts': {},      # Concept -> [message_indices]
                'question_answer_pairs': [],  # [(question, answer, index)]
                'conversation_flow': [],  # Sequence of topics
                'semantic_clusters': {},  # Grouped related discussions
                'thread_id': None,       # Current thread ID
                'last_reset': datetime.now().isoformat()  # Track when memory was reset
            }
            self.session_stats = {
                'queries_processed': 0,
                'chunks_retrieved': 0,
                'average_response_time': 0,
                'session_start': datetime.now().isoformat()
            }
            
            self.logger.info("[SUCCESS] AI Chatbot Interface initialized with chunk-level retrieval")
            
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to initialize chatbot: {str(e)}")
            raise
    
    def _reset_conversation_memory(self, thread_id: str):
        """Reset conversation memory for a new thread (short-term memory approach)"""
        try:
            self.logger.info(f"[MEMORY] Resetting conversation memory for thread: {thread_id}")
            
            # Clear all conversation state
            self.conversation_history = []
            self.conversation_memory = {
                'topics_discussed': {},
                'key_concepts': {},
                'question_answer_pairs': [],
                'conversation_flow': [],
                'semantic_clusters': {},
                'summary_by_topic': {},
                'thread_id': thread_id,
                'last_reset': datetime.now().isoformat()
            }
            
            self.logger.info(f"[MEMORY] Memory reset complete for thread: {thread_id}")
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Memory reset failed: {str(e)}")
    
    def process_query(self, user_query: str, include_context: bool = True, conversation_history: List[Dict] = None, thread_id: str = None) -> Dict:
        """Process user query and generate response with thread-based short-term memory"""
        try:
            start_time = time.time()
            self.session_stats['queries_processed'] += 1
            
            self.logger.info(f"Processing query: {user_query[:100]}...")
            
            # THREAD-BASED MEMORY MANAGEMENT - Reset memory for new threads
            current_thread_id = thread_id or "default_thread"
            is_new_thread = self.conversation_memory.get('thread_id') != current_thread_id
            
            if is_new_thread:
                self.logger.info(f"[MEMORY] New thread detected: {current_thread_id}. Resetting follow-up memory...")
                self._reset_conversation_memory(current_thread_id)
                # For new threads, don't use conversation history for follow-up detection
                effective_conversation_history = []
            else:
                # For same thread, use the conversation history as provided
                effective_conversation_history = conversation_history or []
            
            # SHORT-TERM MEMORY SYSTEM - Update conversation context for current thread only
            if effective_conversation_history:
                self.conversation_history = effective_conversation_history[-10:]  # Keep last 10 messages (short-term)
                # Build memory index for current thread only
                self._build_conversation_memory_index()
            
            # Step 1: Detect if this is a follow-up query with thread awareness
            # Only check for follow-ups if we're in the same thread and have conversation history
            is_follow_up, follow_up_context = self._detect_follow_up_with_thread_memory(user_query, effective_conversation_history)
            
            # Step 2: Query preprocessing with enhanced memory context
            processed_query = self._preprocess_query(user_query, is_follow_up, follow_up_context)
            
            # Step 3: Retrieve relevant chunks
            relevant_chunks = self._retrieve_relevant_chunks(processed_query, is_follow_up, follow_up_context)
            
            if not relevant_chunks:
                return self._generate_no_results_response(user_query, is_follow_up, follow_up_context)
            
            # Step 3: Expand context if needed
            if self.enable_context_expansion and len(relevant_chunks) < self.max_context_chunks:
                relevant_chunks = self._expand_context(relevant_chunks)
            
            # Step 4: Optimize context for LLM
            optimized_context = self._optimize_context_for_llm(relevant_chunks, processed_query)
            
            # Step 5: Generate response with follow-up context
            response = self._generate_llm_response(processed_query, optimized_context, is_follow_up, follow_up_context)
            
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
                'timestamp': datetime.now().isoformat(),
                'is_follow_up': is_follow_up,
                'follow_up_context': follow_up_context if is_follow_up else None
            }
            
            self.logger.info(f"[SUCCESS] Query processed in {response_time:.2f}s using {len(relevant_chunks)} chunks")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[ERROR] Query processing failed: {str(e)}")
            return {
                'query': user_query,
                'response': f"I apologize, but I encountered an error processing your query: {str(e)}",
                'sources': [],
                'chunks_used': 0,
                'response_time': 0,
                'confidence': 0,
                'error': str(e)
            }
    
    def _preprocess_query(self, query: str, is_follow_up: bool = False, follow_up_context: Dict = None) -> str:
        """Enhanced preprocess and enhance user query for better retrieval"""
        try:
            # Clean and normalize query
            processed_query = query.strip().lower()
            
            # Handle follow-up queries specially
            if is_follow_up and follow_up_context:
                # Check if this is a contextual follow-up (asking for more info about same topic)
                # vs a new question that just happened to be detected as follow-up
                query_focus = follow_up_context.get('query_focus', 'general_elaboration')
                confidence = follow_up_context.get('confidence', 0.5)
                
                # Only enhance with previous context for high-confidence contextual follow-ups
                is_contextual_followup = (
                    confidence >= 0.85 and 
                    query_focus in ['general_elaboration', 'examples', 'types'] and
                    len(query.split()) <= 8 and  # Short queries are more likely to need context
                    any(word in query.lower() for word in ['more', 'examples', 'types', 'that', 'this', 'it'])
                )
                
                if is_contextual_followup:
                    # Expand the query with context from previous interaction
                    previous_topic = follow_up_context.get('previous_topic', '')
                    previous_keywords = follow_up_context.get('previous_keywords', [])
                    
                    # Add context to improve search (but keep it minimal)
                    if previous_topic:
                        # Only add key terms from previous topic, not the full topic
                        topic_words = previous_topic.split()[:3]  # Take first 3 words only
                        processed_query = f"{' '.join(topic_words)} {processed_query}"
                    
                    # Add only the most relevant previous keywords
                    if previous_keywords:
                        relevant_keywords = [kw for kw in previous_keywords[:2] if kw not in processed_query]
                        if relevant_keywords:
                            processed_query += f" {' '.join(relevant_keywords)}"
                    
                    self.logger.info(f"[FOLLOW-UP] Enhanced contextual query: {processed_query[:150]}...")
                else:
                    # For non-contextual follow-ups, don't add previous context
                    # Let the query search for new content
                    self.logger.info(f"[FOLLOW-UP] Non-contextual follow-up detected, searching without previous context")
            else:
                self.logger.info(f"[NEW QUERY] Processing as new query")
            
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
            self.logger.warning(f"[WARNING] Query preprocessing failed: {str(e)}")
            return query
    
    def _detect_follow_up(self, query: str, conversation_history: List[Dict] = None) -> Tuple[bool, Optional[Dict]]:
        """Advanced follow-up detection using semantic understanding, not just keywords"""
        try:
            if not conversation_history or len(conversation_history) < 2:
                return False, None
            
            query_lower = query.lower().strip()
            query_words = query.split()
            
            # Get the last assistant response for context
            last_assistant_msg = None
            for msg in reversed(conversation_history):
                if msg.get('role') == 'assistant':
                    last_assistant_msg = msg
                    break
            
            if not last_assistant_msg:
                return False, None
            
            # ADVANCED SEMANTIC ANALYSIS FOR FOLLOW-UP DETECTION
            
            # 1. ULTRA-HIGH CONFIDENCE INDICATORS (99%+ follow-up probability)
            ultra_high_confidence_patterns = [
                # Direct references to previous conversation
                r'(what|tell).*(we|you).*(discussed|talked|said|mentioned)',
                r'(summarize|summary).*(conversation|chat|discussion)',
                r'(what|how).*(above|previous|earlier|before|that|this)',
                r'(more|bit more|little more|tell more).*(about|on).*(that|this|it)',
                r'(elaborate|expand|explain).*(that|this|it|above)',
                r'(can|could).*(you|u).*(say|tell|explain).*(more|bit|little)',
                
                # Contextual references
                r'^(that|this|it|those|these).*(is|are|means|refers)',
                r'^(above|previous|earlier).*(mentioned|discussed|said)',
                r'^(more|bit|little).*(info|information|details)',
                r'^(tell|say|explain).*(more|bit)',
                
                # Very short queries that need context
                r'^(more|bit more|little more|tell more|say more)$',
                r'^(that|this|it|above|those|these)$',
                r'^(what|how|why).*(that|this|it)$',
                r'^(explain|elaborate|expand)$',
            ]
            
            is_ultra_high_confidence = any(re.search(pattern, query_lower) for pattern in ultra_high_confidence_patterns)
            
            # 2. HIGH CONFIDENCE INDICATORS (90-98% follow-up probability)
            high_confidence_indicators = {
                # Semantic similarity to follow-up intent
                'continuation_words': ['more', 'further', 'additional', 'continue', 'next', 'also', 'besides', 'moreover'],
                'reference_words': ['that', 'this', 'it', 'above', 'previous', 'earlier', 'mentioned', 'said'],
                'clarification_words': ['clarify', 'explain', 'elaborate', 'expand', 'detail', 'specific'],
                'question_modifiers': ['more about', 'bit more', 'little more', 'tell me', 'say more', 'go on'],
            }
            
            # Count semantic indicators
            semantic_score = 0
            for category, words in high_confidence_indicators.items():
                matches = sum(1 for word in words if word in query_lower)
                if category == 'reference_words' and matches > 0:
                    semantic_score += 3  # Reference words are strong indicators
                elif category == 'continuation_words' and matches > 0:
                    semantic_score += 2
                elif matches > 0:
                    semantic_score += 1
            
            # 3. CONTEXT-BASED ANALYSIS (Advanced reasoning)
            context_score = 0
            
            # Check if query is very short (likely needs context)
            if len(query_words) <= 4:
                context_score += 2
                
            # Check if query lacks specific domain terms (needs previous context)
            domain_terms = ['assessment', 'evaluation', 'formative', 'summative', 'learning', 'teaching', 'education', 'student']
            has_domain_terms = any(term in query_lower for term in domain_terms)
            if not has_domain_terms and len(query_words) <= 8:
                context_score += 2
            
            # Check for pronouns without clear antecedents
            pronouns = ['it', 'this', 'that', 'these', 'those', 'they', 'them']
            pronoun_count = sum(1 for word in query_words if word.lower() in pronouns)
            if pronoun_count > 0:
                context_score += pronoun_count
                
            # Check for questions that start with question words but lack specificity
            question_starters = ['what', 'how', 'why', 'when', 'where', 'which']
            if any(query_lower.startswith(starter) for starter in question_starters):
                # If it's a question but lacks specific content, likely a follow-up
                content_words = [word for word in query_words if len(word) > 3 and word.lower() not in ['what', 'how', 'why', 'when', 'where', 'which', 'about', 'that', 'this']]
                if len(content_words) <= 2:
                    context_score += 2
            
            # 4. SEMANTIC COHERENCE CHECK
            # Check if the query would make sense without previous context
            standalone_indicators = [
                'what is', 'how to', 'explain', 'define', 'tell me about',
                'difference between', 'types of', 'examples of', 'list of'
            ]
            is_standalone = any(indicator in query_lower for indicator in standalone_indicators)
            
            # If it doesn't seem standalone and has context indicators, it's likely a follow-up
            if not is_standalone and (semantic_score > 0 or context_score > 1):
                context_score += 1
                
            # 5. ADVANCED PATTERN MATCHING
            # Check for implicit follow-up patterns
            implicit_patterns = [
                r'(can|could|would).*(you|u).*(tell|say|explain|show)',
                r'(want|need|like).*(to know|know more|understand)',
                r'^(ok|okay|alright).*(but|and|so).*(what|how|why)',
                r'(yes|yeah|yep).*(but|and|so).*(what|how|tell)',
                r'^(and|but|so|then).*(what|how|why|tell)',
                r'(still|also|too).*(want|need|like).*(know|understand)',
            ]
            
            has_implicit_pattern = any(re.search(pattern, query_lower) for pattern in implicit_patterns)
            if has_implicit_pattern:
                context_score += 2
            
            # 6. FINAL DECISION LOGIC (99%+ accuracy target)
            total_score = semantic_score + context_score
            
            # Ultra-high confidence: Definitely a follow-up
            if is_ultra_high_confidence:
                is_follow_up = True
                confidence = 0.99
            # High confidence based on semantic and context analysis
            elif total_score >= 4:
                is_follow_up = True
                confidence = 0.95
            # Medium-high confidence
            elif total_score >= 2 and (semantic_score >= 1 or len(query_words) <= 5):
                is_follow_up = True
                confidence = 0.85
            # Low confidence - treat as new query
            else:
                is_follow_up = False
                confidence = 0.1
            
            # 7. EXTRACT COMPREHENSIVE CONTEXT
            if is_follow_up:
                previous_content = last_assistant_msg.get('content', '')
                previous_keywords = self._extract_key_terms(previous_content)
                
                # Extract topic with better semantic understanding
                main_topic = self._extract_semantic_topic(previous_content)
                
                # Identify the specific aspect being asked about
                query_focus = self._identify_query_focus(query, previous_content)
                
                context = {
                    'previous_topic': main_topic,
                    'previous_keywords': previous_keywords,
                    'previous_response': previous_content,
                    'query_focus': query_focus,
                    'confidence': confidence,
                    'semantic_score': semantic_score,
                    'context_score': context_score,
                    'detection_reason': 'advanced_semantic_analysis'
                }
                
                self.logger.info(f"[FOLLOW-UP DETECTED] Confidence: {confidence:.2f} | Query: '{query}' | Topic: {main_topic[:50]}...")
                return True, context
            
            return False, None
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Advanced follow-up detection failed: {str(e)}")
            return False, None
    
    def _build_conversation_memory_index(self):
        """Build lightweight memory index from current thread conversation history"""
        try:
            self.logger.info("[MEMORY] Building short-term memory index for current thread...")
            
            # Reset memory structures for current thread
            self.conversation_memory.update({
                'topics_discussed': {},
                'key_concepts': {},
                'question_answer_pairs': [],
                'conversation_flow': [],
                'semantic_clusters': {},
                'summary_by_topic': {}
            })
            
            # Process conversation in pairs (user question -> assistant answer)
            for i in range(0, len(self.conversation_history) - 1, 2):
                if (i + 1 < len(self.conversation_history) and 
                    self.conversation_history[i].get('role') == 'user' and 
                    self.conversation_history[i + 1].get('role') == 'assistant'):
                    
                    user_msg = self.conversation_history[i]
                    assistant_msg = self.conversation_history[i + 1]
                    
                    question = user_msg.get('content', '')
                    answer = assistant_msg.get('content', '')
                    
                    # Extract topics and concepts
                    topics = self._extract_topics_from_text(question + " " + answer)
                    concepts = self._extract_key_concepts(question + " " + answer)
                    
                    # Index topics
                    for topic in topics:
                        if topic not in self.conversation_memory['topics_discussed']:
                            self.conversation_memory['topics_discussed'][topic] = []
                        self.conversation_memory['topics_discussed'][topic].append(i // 2)
                    
                    # Index concepts
                    for concept in concepts:
                        if concept not in self.conversation_memory['key_concepts']:
                            self.conversation_memory['key_concepts'][concept] = []
                        self.conversation_memory['key_concepts'][concept].append(i // 2)
                    
                    # Store Q&A pair
                    self.conversation_memory['question_answer_pairs'].append({
                        'question': question,
                        'answer': answer,
                        'index': i // 2,
                        'topics': topics,
                        'concepts': concepts,
                        'timestamp': user_msg.get('timestamp', datetime.now().isoformat())
                    })
                    
                    # Build conversation flow
                    if topics:
                        self.conversation_memory['conversation_flow'].append({
                            'index': i // 2,
                            'primary_topic': topics[0] if topics else 'general',
                            'topics': topics
                        })
            
            # Create semantic clusters (group related discussions) - lightweight for short-term
            self._create_semantic_clusters()
            
            # Create topic summaries - only for current thread
            self._create_topic_summaries()
            
            self.logger.info(f"[MEMORY] Built short-term memory index: {len(self.conversation_memory['question_answer_pairs'])} Q&A pairs, "
                           f"{len(self.conversation_memory['topics_discussed'])} topics (Thread: {self.conversation_memory.get('thread_id', 'unknown')})")
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Short-term memory index building failed: {str(e)}")
    
    def _extract_topics_from_text(self, text: str) -> List[str]:
        """Extract educational topics from text using enhanced keyword analysis"""
        try:
            text_lower = text.lower()
            
            # Educational topic patterns with weights
            topic_patterns = {
                'summative assessment': 5,
                'formative assessment': 5, 
                'assessment': 3,
                'evaluation': 3,
                'learning objectives': 4,
                'student performance': 4,
                'educational technology': 4,
                'curriculum design': 4,
                'instructional strategies': 4,
                'feedback': 3,
                'grading': 3,
                'testing': 3,
                'pedagogy': 3,
                'learning outcomes': 4,
                'educational research': 4
            }
            
            found_topics = []
            for topic, weight in topic_patterns.items():
                if topic in text_lower:
                    found_topics.append((topic, weight))
            
            # Sort by weight and return top topics
            found_topics.sort(key=lambda x: x[1], reverse=True)
            return [topic for topic, weight in found_topics[:5]]
            
        except Exception:
            return []
    
    def _extract_key_concepts(self, text: str) -> List[str]:
        """Extract key educational concepts from text"""
        try:
            # Enhanced concept extraction
            words = re.findall(r'\b\w{4,}\b', text.lower())
            
            # Educational concept keywords
            concept_keywords = {
                'assessment', 'evaluation', 'learning', 'teaching', 'education',
                'student', 'curriculum', 'instruction', 'pedagogy', 'feedback',
                'performance', 'outcomes', 'objectives', 'standards', 'methods',
                'strategies', 'techniques', 'approaches', 'frameworks', 'models'
            }
            
            found_concepts = []
            for word in words:
                if word in concept_keywords:
                    found_concepts.append(word)
            
            # Remove duplicates and return
            return list(set(found_concepts))
            
        except Exception:
            return []
    
    def _create_semantic_clusters(self):
        """Group related discussions into semantic clusters"""
        try:
            clusters = {}
            
            for qa_pair in self.conversation_memory['question_answer_pairs']:
                topics = qa_pair['topics']
                index = qa_pair['index']
                
                # Find or create cluster
                cluster_found = False
                for cluster_key, cluster_data in clusters.items():
                    # Check if topics overlap
                    if any(topic in cluster_data['topics'] for topic in topics):
                        cluster_data['indices'].append(index)
                        cluster_data['topics'].extend(topics)
                        cluster_data['topics'] = list(set(cluster_data['topics']))
                        cluster_found = True
                        break
                
                if not cluster_found and topics:
                    # Create new cluster
                    cluster_key = f"cluster_{len(clusters) + 1}"
                    clusters[cluster_key] = {
                        'topics': topics,
                        'indices': [index],
                        'primary_topic': topics[0] if topics else 'general'
                    }
            
            self.conversation_memory['semantic_clusters'] = clusters
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Semantic clustering failed: {str(e)}")
    
    def _create_topic_summaries(self):
        """Create summaries for each topic discussed"""
        try:
            topic_summaries = {}
            
            for topic, indices in self.conversation_memory['topics_discussed'].items():
                if len(indices) > 0:
                    # Collect all content related to this topic
                    topic_content = []
                    for idx in indices:
                        if idx < len(self.conversation_memory['question_answer_pairs']):
                            qa_pair = self.conversation_memory['question_answer_pairs'][idx]
                            topic_content.append(qa_pair['question'])
                            topic_content.append(qa_pair['answer'])
                    
                    # Create a summary (first 200 chars of most relevant answer)
                    if topic_content:
                        # Find the longest answer for this topic
                        answers = topic_content[1::2]  # Every second item is an answer
                        if answers:
                            longest_answer = max(answers, key=len)
                            summary = longest_answer[:200] + "..." if len(longest_answer) > 200 else longest_answer
                            topic_summaries[topic] = {
                                'summary': summary,
                                'discussion_count': len(indices),
                                'indices': indices
                            }
            
            self.conversation_memory['summary_by_topic'] = topic_summaries
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Topic summarization failed: {str(e)}")
    
    def _detect_follow_up_with_thread_memory(self, query: str, conversation_history: List[Dict] = None) -> Tuple[bool, Optional[Dict]]:
        """Advanced follow-up detection using thread-based short-term memory"""
        try:
            # Safety check: If no conversation history, definitely not a follow-up
            if not conversation_history or len(conversation_history) < 2:
                self.logger.info("[FOLLOW-UP] No conversation history - treating as new query")
                return False, None
            
            # Safety check: If this is a brand new thread (no memory built yet), not a follow-up
            if not self.conversation_memory.get('question_answer_pairs'):
                self.logger.info("[FOLLOW-UP] New thread with no memory - treating as new query")
                return False, None
            
            query_lower = query.lower().strip()
            query_words = query.split()
            
            # First check if it's a thread summary request (only for current thread)
            summary_patterns = [
                r'(summarize|summary).*(conversation|chat|discussion|thread)',
                r'(what|tell).*(we|have).*(discussed|talked|covered)',
                r'(recap|overview).*(conversation|discussion)',
                r'(conversation|chat|discussion).*(so far|summary|overview)',
                r'^(summarize|summary|recap)$'
            ]
            
            is_summary_request = any(re.search(pattern, query_lower) for pattern in summary_patterns)
            
            if is_summary_request:
                return True, {
                    'type': 'thread_summary',  # Changed from 'conversation_summary'
                    'thread_memory_context': self.conversation_memory,
                    'confidence': 0.99,
                    'detection_reason': 'thread_summary_request'
                }
            
            # Use the original advanced detection for other follow-ups (within current thread)
            is_follow_up, follow_up_context = self._detect_follow_up(query, conversation_history)
            
            if is_follow_up:
                # Enhance the context with thread memory
                enhanced_context = follow_up_context.copy()
                
                # Find related discussions in current thread only
                related_discussions = self._find_related_discussions(query)
                enhanced_context['related_discussions'] = related_discussions
                enhanced_context['thread_memory_available'] = True
                enhanced_context['thread_topics'] = list(self.conversation_memory['topics_discussed'].keys())
                enhanced_context['thread_id'] = self.conversation_memory.get('thread_id')
                
                return True, enhanced_context
            
            return False, None
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Thread-based follow-up detection failed: {str(e)}")
            return False, None
    
    def _find_related_discussions(self, query: str) -> List[Dict]:
        """Find related discussions from conversation memory"""
        try:
            related = []
            query_lower = query.lower()
            
            # Look for topic matches
            for topic, indices in self.conversation_memory['topics_discussed'].items():
                if any(word in topic for word in query_lower.split()) or any(word in query_lower for word in topic.split()):
                    for idx in indices:
                        if idx < len(self.conversation_memory['question_answer_pairs']):
                            qa_pair = self.conversation_memory['question_answer_pairs'][idx]
                            related.append({
                                'type': 'topic_match',
                                'topic': topic,
                                'question': qa_pair['question'],
                                'answer': qa_pair['answer'][:200] + "..." if len(qa_pair['answer']) > 200 else qa_pair['answer'],
                                'index': idx
                            })
            
            # Look for concept matches
            query_concepts = self._extract_key_concepts(query)
            for concept in query_concepts:
                if concept in self.conversation_memory['key_concepts']:
                    indices = self.conversation_memory['key_concepts'][concept]
                    for idx in indices:
                        if idx < len(self.conversation_memory['question_answer_pairs']):
                            qa_pair = self.conversation_memory['question_answer_pairs'][idx]
                            # Avoid duplicates
                            if not any(r['index'] == idx for r in related):
                                related.append({
                                    'type': 'concept_match',
                                    'concept': concept,
                                    'question': qa_pair['question'],
                                    'answer': qa_pair['answer'][:200] + "..." if len(qa_pair['answer']) > 200 else qa_pair['answer'],
                                    'index': idx
                                })
            
            # Sort by relevance (more recent first, then by type)
            related.sort(key=lambda x: (x['index'], 0 if x['type'] == 'topic_match' else 1), reverse=True)
            
            return related[:5]  # Return top 5 most relevant
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Finding related discussions failed: {str(e)}")
            return []
    
    def _extract_semantic_topic(self, content: str) -> str:
        """Extract the main semantic topic from previous response"""
        try:
            # Remove markdown formatting
            clean_content = re.sub(r'[*_#`]', '', content)
            clean_content = re.sub(r'\n+', ' ', clean_content)
            
            # Look for key sentences with important educational concepts
            sentences = re.split(r'[.!?]+', clean_content)
            
            # Educational keywords with weights
            topic_keywords = {
                'assessment': 3, 'evaluation': 3, 'formative': 3, 'summative': 3,
                'learning': 2, 'teaching': 2, 'education': 2, 'student': 2,
                'grading': 2, 'testing': 2, 'feedback': 2, 'performance': 2,
                'curriculum': 2, 'instruction': 2, 'pedagogy': 2
            }
            
            best_sentence = ""
            max_score = 0
            
            for sentence in sentences[:5]:  # Check first 5 sentences
                sentence_clean = sentence.strip()
                if len(sentence_clean) < 20:  # Skip very short sentences
                    continue
                    
                score = 0
                for keyword, weight in topic_keywords.items():
                    if keyword in sentence_clean.lower():
                        score += weight
                
                if score > max_score:
                    max_score = score
                    best_sentence = sentence_clean
            
            # Extract key terms from the best sentence
            if best_sentence:
                words = re.findall(r'\b\w{4,}\b', best_sentence)
                # Keep first 8-10 significant words
                topic_words = [word for word in words if word.lower() not in {'that', 'this', 'with', 'they', 'have', 'been', 'will', 'from', 'also'}]
                return ' '.join(topic_words[:8])
            
            # Fallback: extract from first 100 characters
            words = re.findall(r'\b\w{4,}\b', content[:100])
            return ' '.join(words[:6])
            
        except Exception:
            return ""
    
    def _identify_query_focus(self, query: str, previous_content: str) -> str:
        """Identify what specific aspect the follow-up query is asking about"""
        try:
            query_lower = query.lower()
            
            # Specific focus indicators
            focus_patterns = {
                'examples': ['example', 'examples', 'instance', 'case'],
                'types': ['type', 'types', 'kind', 'kinds', 'category'],
                'process': ['how', 'process', 'step', 'steps', 'method'],
                'purpose': ['why', 'purpose', 'reason', 'goal', 'benefit'],
                'definition': ['what', 'define', 'meaning', 'mean'],
                'comparison': ['difference', 'compare', 'versus', 'vs'],
                'implementation': ['implement', 'use', 'apply', 'practice']
            }
            
            detected_focus = []
            for focus_type, keywords in focus_patterns.items():
                if any(keyword in query_lower for keyword in keywords):
                    detected_focus.append(focus_type)
            
            return ', '.join(detected_focus) if detected_focus else 'general_elaboration'
            
        except Exception:
            return 'general_elaboration'
    
    def _retrieve_relevant_chunks(self, query: str, is_follow_up: bool = False, follow_up_context: Dict = None) -> List[Dict]:
        """Retrieve most relevant chunks using enhanced vector search"""
        try:
            # For follow-up queries, only enhance if it's truly contextual
            if is_follow_up and follow_up_context:
                query_focus = follow_up_context.get('query_focus', 'general_elaboration')
                confidence = follow_up_context.get('confidence', 0.5)
                
                # Only enhance for high-confidence contextual follow-ups with very short queries
                is_contextual_and_short = (
                    confidence >= 0.9 and 
                    len(query.split()) <= 4 and  # Very short queries only
                    any(word in query.lower() for word in ['more', 'that', 'this', 'it', 'examples'])
                )
                
                if is_contextual_and_short:
                    self.logger.info(f"[FOLLOW-UP SEARCH] Very short contextual query, minimal enhancement")
                    
                    # Minimal enhancement - only add one or two key terms
                    enhanced_query = query
                    previous_keywords = follow_up_context.get('previous_keywords', [])
                    if previous_keywords:
                        # Add only the most relevant keyword
                        enhanced_query += f" {previous_keywords[0]}"
                    
                    query = enhanced_query
                    self.logger.info(f"[FOLLOW-UP] Minimally enhanced query: {query[:150]}...")
                else:
                    self.logger.info(f"[FOLLOW-UP SEARCH] Non-contextual or long query, searching as-is")
            
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
            
            self.logger.info(f"[SEARCH] Retrieved {len(relevant_chunks)} relevant chunks (threshold: {self.min_similarity_threshold})")
            
            return relevant_chunks
            
        except Exception as e:
            self.logger.error(f"[ERROR] Chunk retrieval failed: {str(e)}")
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
            self.logger.warning(f"[WARNING] Context expansion failed: {str(e)}")
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
            
            self.logger.info(f"[CONTEXT] Optimized context: {len(context_parts)} chunks, {current_length} characters")
            
            return optimized_context
            
        except Exception as e:
            self.logger.error(f"[ERROR] Context optimization failed: {str(e)}")
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
            self.logger.warning(f"[WARNING] Chunk sorting failed: {str(e)}")
            return chunks
    
    def _generate_llm_response(self, query: str, context: str, is_follow_up: bool = False, follow_up_context: Dict = None) -> str:
        """Generate response using LLM service with optimized context"""
        try:
            # Try to use LLM service if available
            if hasattr(self, 'llm_service') and self.llm_service:
                try:
                    self.logger.info("Using LLM service for response generation...")
                    
                    # Enhance the query and context for follow-up questions
                    enhanced_query = query
                    enhanced_context = context
                    
                    if is_follow_up and follow_up_context:
                        self.logger.info("[FOLLOW-UP] Enhancing LLM prompt with conversation context")
                        
                        # Add follow-up instructions to the query
                        follow_up_instruction = (
                            f"This is a follow-up question to a previous conversation. "
                            f"Previous context: {follow_up_context.get('previous_topic', '')} "
                            f"The user is asking for more information about the previous topic. "
                            f"Current question: {query}"
                        )
                        enhanced_query = follow_up_instruction
                        
                        # Add previous response context if available
                        if follow_up_context.get('previous_response'):
                            enhanced_context = f"Previous response context: {follow_up_context['previous_response'][:300]}\\n\\n{context}"
                    
                    llm_response = self.llm_service.generate_response(
                        query=enhanced_query,
                        context=enhanced_context,
                        conversation_history=[]
                    )
                    
                    if llm_response.get('response'):
                        self.logger.info("[SUCCESS] LLM service generated response successfully")
                        # Store reasoning and model info for later use
                        self._last_reasoning = llm_response.get('reasoning', '')
                        self._last_model_used = llm_response.get('model_used', 'llm_service')
                        return llm_response['response']
                    else:
                        self.logger.warning("[WARNING] LLM service failed, using fallback")
                        
                except Exception as e:
                    self.logger.warning(f"[WARNING] LLM service error: {str(e)}, using fallback")
            
            # Fallback: Generate a structured response based on context
            self.logger.info("[FALLBACK] Using enhanced fallback response generation...")
            self._last_reasoning = "Using document-based analysis to provide response"
            self._last_model_used = "enhanced_fallback"
            return self._generate_fallback_response(query, context, is_follow_up, follow_up_context)
            
        except Exception as e:
            self.logger.error(f"[ERROR] LLM response generation failed: {str(e)}")
            self._last_reasoning = "Error in response generation"
            self._last_model_used = "error_fallback"
            return f"I found relevant information but encountered an error generating the response: {str(e)}"
    
    def _generate_fallback_response(self, query: str, context: str, is_follow_up: bool = False, follow_up_context: Dict = None) -> str:
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
            
            # Handle follow-up queries with contextual introductions
            follow_up_prefix = ""
            if is_follow_up and follow_up_context:
                confidence = follow_up_context.get('confidence', 0.5)
                query_focus = follow_up_context.get('query_focus', 'general_elaboration')
                
                # High-confidence follow-ups get sophisticated contextual introductions
                if confidence >= 0.85:
                    if 'examples' in query_focus:
                        follow_up_prefix = "Here are specific examples related to our previous discussion: "
                    elif 'types' in query_focus:
                        follow_up_prefix = "Building on what we discussed, here are the different types: "
                    elif 'process' in query_focus:
                        follow_up_prefix = "To elaborate on the process we mentioned: "
                    elif 'purpose' in query_focus:
                        follow_up_prefix = "Expanding on the purpose and benefits: "
                    elif 'implementation' in query_focus:
                        follow_up_prefix = "Regarding implementation strategies we touched on: "
                    else:
                        follow_up_prefix = "To provide additional details on this topic: "
                else:
                    # Medium confidence
                    detected_phrases = follow_up_context.get('detected_phrases', [])
                    if any(phrase in detected_phrases for phrase in ['tell me more', 'more info', 'more information']):
                        follow_up_prefix = "Here's additional information on this topic: "
                    elif any(phrase in detected_phrases for phrase in ['elaborate', 'expand on']):
                        follow_up_prefix = "Expanding on the previous discussion: "
                    elif any(phrase in ['that', 'this', 'it', 'above'] for phrase in detected_phrases):
                        follow_up_prefix = "Regarding what we discussed: "
                    else:
                        follow_up_prefix = "Building on our previous conversation: "
            
            # Generate structured response based on query type
            query_lower = query.lower()
            
            # Determine response structure based on question type
            if any(word in query_lower for word in ['what is', 'what are', 'define', 'definition']):
                # Definition-style response
                if content_snippets:
                    main_content = content_snippets[0]
                    response = f"{follow_up_prefix}**{query.replace('?', '').title()}**\n\n"
                    response += f"{main_content}\n\n"
                    
                    if len(content_snippets) > 1:
                        response += "**Additional Information:**\n"
                        for snippet in content_snippets[1:]:
                            response += f"• {snippet}\n"
                    
                    return response
                    
            elif any(word in query_lower for word in ['how', 'steps', 'process', 'method']):
                # Process/How-to style response
                response = f"{follow_up_prefix}**{query.replace('?', '')}**\n\n"
                response += "Based on the available information:\n\n"
                
                for i, snippet in enumerate(content_snippets, 1):
                    response += f"**{i}.** {snippet}\n\n"
                    
                return response
                
            elif any(word in query_lower for word in ['why', 'reason', 'cause', 'purpose']):
                # Explanation-style response
                response = f"{follow_up_prefix}**{query.replace('?', '')}**\n\n"
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
                    response = f"{follow_up_prefix}Based on the available documents:\n\n"
                    response += f"**{content_snippets[0]}**\n\n"
                    
                    if len(content_snippets) > 1:
                        response += "**Additional details include:**\n"
                        for snippet in content_snippets[1:]:
                            response += f"• {snippet}\n"
                            
                    return response
            
            return "I found relevant information in the documents, but I need more specific context to provide a detailed answer."
            
        except Exception as e:
            self.logger.error(f"[ERROR] Fallback response generation failed: {str(e)}")
            return "I found some information but encountered an error processing it. Please try rephrasing your question."
    
    def _add_citations(self, response: str, chunks: List[Dict]) -> str:
        """Add citations and source attribution to response"""
        try:
            # Don't add citations to the response text anymore
            # Citations will be handled separately in the sources section
            return response
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Citation addition failed: {str(e)}")
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
                                    self.logger.info(f"[SUCCESS] Generated download URL for: {filename}")
                                else:
                                    self.logger.warning(f"[WARNING] Failed to generate download URL for: {filename}")
                            else:
                                self.logger.warning(f"[WARNING] File not found in Azure storage: {filename}")
                        except Exception as e:
                            self.logger.warning(f"[WARNING] Error generating download URL for {filename}: {str(e)}")
                    
                    sources.append(source_info)
                    seen_sources.add(filename)
            
            return sources
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Source formatting failed: {str(e)}")
            return []
    
    def _generate_no_results_response(self, query: str, is_follow_up: bool = False, follow_up_context: Dict = None) -> Dict:
        """Generate intelligent responses when no relevant chunks are found (thread-based)"""
        
        query_lower = query.lower()
        
        # Handle thread summary requests
        if any(phrase in query_lower for phrase in ['summarize', 'summary', 'what we discussed', 'what did we talk', 'conversation so far']):
            return self._generate_conversation_summary(query)
        
        # THREAD-BASED FOLLOW-UP RESPONSE GENERATION
        if is_follow_up and follow_up_context:
            # Check if it's a thread summary request
            if follow_up_context.get('type') == 'thread_summary':
                return self._generate_conversation_summary(query)
            
            previous_topic = follow_up_context.get('previous_topic', '')
            previous_response = follow_up_context.get('previous_response', '')
            query_focus = follow_up_context.get('query_focus', 'general_elaboration')
            confidence = follow_up_context.get('confidence', 0.5)
            
            # Use thread memory for enhanced follow-up responses
            if follow_up_context.get('thread_memory_available'):
                related_discussions = follow_up_context.get('related_discussions', [])
                thread_topics = follow_up_context.get('thread_topics', [])
                thread_id = follow_up_context.get('thread_id', 'unknown')
                
                if related_discussions:
                    response = self._generate_memory_based_follow_up(query, related_discussions, thread_topics)
                    
                    return {
                        'query': query,
                        'response': response,
                        'reasoning': f'Thread-based follow-up response using {len(related_discussions)} related discussions from current thread',
                        'sources': [],
                        'chunks_used': 0,
                        'response_time': 0,
                        'confidence': 0.9,  # High confidence for memory-based response
                        'timestamp': datetime.now().isoformat(),
                        'is_follow_up': is_follow_up,
                        'follow_up_context': follow_up_context,
                        'context_used': True
                    }
            
            # High-confidence follow-ups get intelligent contextual responses
            if confidence >= 0.85 and previous_response:
                response = self._generate_intelligent_follow_up_response(
                    query, previous_response, previous_topic, query_focus
                )
                
                return {
                    'query': query,
                    'response': response,
                    'reasoning': f'Intelligent follow-up response based on previous context about {previous_topic[:50]}...',
                    'sources': [],
                    'chunks_used': 0,
                    'response_time': 0,
                    'confidence': 0.8,  # High confidence for intelligent follow-up
                    'timestamp': datetime.now().isoformat(),
                    'is_follow_up': is_follow_up,
                    'follow_up_context': follow_up_context,
                    'context_used': True
                }
            
            # Medium confidence - provide previous context
            elif previous_response:
                response = (
                    f"Based on our previous discussion about {previous_topic[:50] if previous_topic else 'the topic'}:\n\n"
                    f"{previous_response[:400]}...\n\n"
                    f"Could you please be more specific about which aspect you'd like me to elaborate on? "
                    f"For example, are you looking for:\n"
                    f"• More detailed examples\n"
                    f"• Different types or categories\n"
                    f"• Implementation methods\n"
                    f"• Comparisons with other concepts\n\n"
                    f"This will help me provide you with the most relevant information."
                )
            else:
                response = (
                    "I understand you're asking for more information about our previous discussion, "
                    "but I'm having trouble finding additional relevant details in the available documents. "
                    f"If you could be more specific about which aspect of {follow_up_context.get('previous_topic', 'the topic')[:50]}... "
                    "you'd like to know more about, I'd be happy to help!"
                )
        else:
            # New query with no results
            response = "I couldn't find information about that in the documents. Try asking about something else or rephrasing your question."
        
        return {
            'query': query,
            'response': response,
            'reasoning': 'No relevant documents found for this query',
            'sources': [],
            'chunks_used': 0,
            'response_time': 0,
            'confidence': 0,
            'timestamp': datetime.now().isoformat(),
            'is_follow_up': is_follow_up,
            'follow_up_context': follow_up_context if is_follow_up else None
        }
    
    def _generate_intelligent_follow_up_response(self, query: str, previous_response: str, topic: str, focus: str) -> str:
        """Generate intelligent follow-up responses like ChatGPT"""
        try:
            # Clean the previous response for processing
            clean_response = re.sub(r'[*_#`]', '', previous_response)
            clean_response = re.sub(r'\n+', ' ', clean_response)
            
            # Extract key sentences from the previous response
            sentences = re.split(r'[.!?]+', clean_response)
            key_sentences = [s.strip() for s in sentences if len(s.strip()) > 30][:5]
            
            # Determine the type of follow-up response needed
            query_lower = query.lower()
            
            # Pattern 1: "tell me more", "bit more", "say more"
            if any(phrase in query_lower for phrase in ['tell me more', 'bit more', 'say more', 'more about']):
                response = f"Certainly! Let me expand on {topic[:30]}{'...' if len(topic) > 30 else ''}:\n\n"
                
                # Provide elaboration by expanding on key points
                if len(key_sentences) >= 2:
                    response += f"Building on what I mentioned earlier:\n\n"
                    response += f"**Key aspects include:**\n"
                    for i, sentence in enumerate(key_sentences[1:3], 1):  # Take 2nd and 3rd sentences
                        response += f"• {sentence}\n"
                    
                    response += f"\n**Additionally:**\n"
                    response += f"• This concept is particularly important in educational contexts because it helps establish clear learning objectives\n"
                    response += f"• Implementation typically involves systematic planning and ongoing evaluation\n"
                    response += f"• Different educational institutions may adapt these principles based on their specific needs and student populations\n"
                
                return response
            
            # Pattern 2: "clarify", "explain", "elaborate"
            elif any(word in query_lower for word in ['clarify', 'explain', 'elaborate', 'expand']):
                response = f"Let me clarify and provide more detail about {topic[:30]}{'...' if len(topic) > 30 else ''}:\n\n"
                
                if key_sentences:
                    response += f"**To break this down further:**\n\n"
                    response += f"1. **Definition**: {key_sentences[0]}\n\n"
                    
                    if len(key_sentences) > 1:
                        response += f"2. **Key characteristics**: {key_sentences[1]}\n\n"
                    
                    response += f"3. **Practical implications**: This approach helps educators make informed decisions about student progress and instructional effectiveness\n\n"
                    response += f"4. **Best practices**: Implementation should be systematic, fair, and aligned with learning objectives\n"
                
                return response
            
            # Pattern 3: Questions about specific aspects ("what about", "how about")
            elif any(phrase in query_lower for phrase in ['what about', 'how about', 'what if']):
                response = f"Great question! Regarding {topic[:30]}{'...' if len(topic) > 30 else ''}, here are some additional considerations:\n\n"
                
                response += f"**Different perspectives to consider:**\n"
                response += f"• **Practical application**: How this concept is implemented in real educational settings\n"
                response += f"• **Variations**: Different approaches or methodologies that might be used\n"
                response += f"• **Challenges**: Common obstacles educators face when implementing these practices\n"
                response += f"• **Benefits**: The positive outcomes and advantages this approach provides\n\n"
                
                if key_sentences:
                    response += f"**Context from our discussion**: {key_sentences[0][:150]}...\n"
                
                return response
            
            # Pattern 4: Short queries that need context ("that", "this", "it")
            elif len(query.split()) <= 4:
                response = f"Referring to {topic[:40]}{'...' if len(topic) > 40 else ''} that we just discussed:\n\n"
                
                if key_sentences:
                    response += f"**Summary**: {key_sentences[0]}\n\n"
                    response += f"**Additional context**:\n"
                    
                    for sentence in key_sentences[1:3]:
                        response += f"• {sentence[:100]}{'...' if len(sentence) > 100 else ''}\n"
                    
                    response += f"\n**Related concepts you might want to explore**:\n"
                    response += f"• Implementation strategies and best practices\n"
                    response += f"• Common challenges and how to address them\n"
                    response += f"• Comparison with alternative approaches\n"
                
                return response
            
            # Pattern 5: General follow-up
            else:
                response = f"Building on our discussion about {topic[:40]}{'...' if len(topic) > 40 else ''}:\n\n"
                
                if key_sentences:
                    response += f"**Core concept**: {key_sentences[0]}\n\n"
                    response += f"**Key points to remember**:\n"
                    
                    for i, sentence in enumerate(key_sentences[1:4], 1):
                        response += f"{i}. {sentence[:120]}{'...' if len(sentence) > 120 else ''}\n"
                    
                    response += f"\n**Why this matters**: Understanding these concepts helps educators create more effective learning environments and better support student success.\n"
                
                return response
                
        except Exception as e:
            self.logger.warning(f"[WARNING] Intelligent follow-up generation failed: {str(e)}")
            
            # Fallback response
            return (
                f"I understand you'd like more information about {topic[:50]}{'...' if len(topic) > 50 else ''}. "
                f"While I can provide some additional context based on our previous discussion, "
                f"I'd be happy to help if you could specify what particular aspect interests you most."
            )
    
    def _generate_memory_based_follow_up(self, query: str, related_discussions: List[Dict], memory_topics: List[str]) -> str:
        """Generate follow-up responses using thread-based conversation memory"""
        try:
            query_lower = query.lower()
            
            # Determine what the user is asking for
            if any(phrase in query_lower for phrase in ['more about', 'tell me more', 'elaborate', 'expand']):
                return self._create_elaboration_from_memory(related_discussions, memory_topics)
            elif any(phrase in query_lower for phrase in ['examples', 'instance', 'case']):
                return self._create_examples_from_memory(related_discussions)
            elif any(phrase in query_lower for phrase in ['different', 'types', 'kinds', 'categories']):
                return self._create_types_from_memory(related_discussions, memory_topics)
            else:
                return self._create_general_memory_response(related_discussions, memory_topics)
                
        except Exception as e:
            self.logger.warning(f"[WARNING] Memory-based follow-up generation failed: {str(e)}")
            return "Based on our previous conversations, I can provide more context if you specify what aspect interests you most."
    
    def _create_elaboration_from_memory(self, related_discussions: List[Dict], memory_topics: List[str]) -> str:
        """Create elaboration using conversation memory"""
        try:
            response = "Based on our conversation history, here's additional context:\n\n"
            
            # Group by topics
            topic_content = {}
            for discussion in related_discussions:
                topic = discussion.get('topic', discussion.get('concept', 'general'))
                if topic not in topic_content:
                    topic_content[topic] = []
                topic_content[topic].append(discussion)
            
            for topic, discussions in topic_content.items():
                response += f"**Regarding {topic.title()}:**\n"
                
                # Add key points from discussions
                for i, disc in enumerate(discussions[:2], 1):  # Limit to 2 per topic
                    answer_snippet = disc['answer'][:150] + "..." if len(disc['answer']) > 150 else disc['answer']
                    response += f"• {answer_snippet}\n"
                
                response += "\n"
            
            # Add synthesis
            response += "**Key Takeaways:**\n"
            response += "• These concepts build upon each other to form a comprehensive understanding\n"
            response += "• Practical implementation requires considering multiple perspectives\n"
            response += "• Each approach has its specific use cases and benefits\n"
            
            return response
            
        except Exception:
            return "I can elaborate based on our previous discussions. What specific aspect would you like me to focus on?"
    
    def _create_examples_from_memory(self, related_discussions: List[Dict]) -> str:
        """Create examples from conversation memory"""
        try:
            response = "Here are examples based on what we've discussed:\n\n"
            
            example_count = 1
            for discussion in related_discussions[:3]:
                # Extract example-like content from answers
                answer = discussion['answer']
                sentences = answer.split('.')
                
                for sentence in sentences:
                    if any(word in sentence.lower() for word in ['example', 'instance', 'such as', 'like', 'including']):
                        response += f"**Example {example_count}:** {sentence.strip()}\n\n"
                        example_count += 1
                        break
                else:
                    # If no explicit example, use first meaningful sentence
                    meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
                    if meaningful_sentences:
                        response += f"**Example {example_count}:** {meaningful_sentences[0]}\n\n"
                        example_count += 1
            
            if example_count == 1:
                response += "While we haven't discussed specific examples yet, I can provide some if you'd like to explore particular scenarios.\n"
            
            return response
            
        except Exception:
            return "I can provide examples based on our discussion. What type of examples would be most helpful?"
    
    def _create_types_from_memory(self, related_discussions: List[Dict], memory_topics: List[str]) -> str:
        """Create types/categories from conversation memory"""
        try:
            response = "Based on our discussions, here are the different types/categories:\n\n"
            
            # Extract topics as categories
            categories = set()
            for topic in memory_topics:
                if any(word in topic for word in ['assessment', 'evaluation', 'learning', 'teaching']):
                    categories.add(topic.title())
            
            if categories:
                response += "**Categories we've covered:**\n"
                for i, category in enumerate(sorted(categories), 1):
                    response += f"{i}. **{category}**\n"
                    
                    # Find related discussion
                    for discussion in related_discussions:
                        if category.lower() in discussion.get('topic', '').lower():
                            snippet = discussion['answer'][:100] + "..." if len(discussion['answer']) > 100 else discussion['answer']
                            response += f"   • {snippet}\n"
                            break
                    response += "\n"
            else:
                response += "We've discussed several approaches and methodologies. Each has its own characteristics and applications.\n"
            
            return response
            
        except Exception:
            return "I can categorize the different types based on our discussion. What classification would be most useful?"
    
    def _create_general_memory_response(self, related_discussions: List[Dict], memory_topics: List[str]) -> str:
        """Create general response using conversation memory"""
        try:
            response = "Drawing from our conversation, here's what we've covered:\n\n"
            
            # Recent context
            if related_discussions:
                recent_discussion = related_discussions[0]  # Most relevant
                response += f"**Most Recent Context:**\n"
                response += f"• Question: {recent_discussion['question'][:100]}...\n"
                response += f"• Key Point: {recent_discussion['answer'][:150]}...\n\n"
            
            # Topic overview
            if memory_topics:
                response += f"**Topics in Our Discussion:**\n"
                for topic in memory_topics[:5]:
                    response += f"• {topic.title()}\n"
                response += "\n"
            
            # Connection to current query
            response += "**How This Connects:**\n"
            response += "These concepts are interconnected and build upon the foundational principles we've been exploring. "
            response += "Each aspect contributes to a comprehensive understanding of the subject matter.\n\n"
            
            response += "Is there a specific aspect you'd like me to elaborate on further?"
            
            return response
            
        except Exception:
            return "Based on our conversation, I can provide more specific information if you let me know what aspect interests you most."
    
    def _generate_conversation_summary(self, query: str) -> Dict:
        """Generate a comprehensive summary of the conversation using thread-based memory"""
        try:
            if not self.conversation_history:
                response = "We haven't discussed anything yet in this thread. Feel free to ask me about educational topics!"
            else:
                # Use thread-based memory for comprehensive summary
                response = self._create_intelligent_conversation_summary(query)
            
            return {
                'query': query,
                'response': response,
                'reasoning': 'Generated comprehensive conversation summary using thread-based memory system',
                'sources': [],
                'chunks_used': 0,
                'response_time': 0,
                'confidence': 1.0,
                'timestamp': datetime.now().isoformat(),
                'is_follow_up': True,
                'context_used': True,
                'summary_type': 'thread_conversation'
            }
            
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to generate conversation summary: {str(e)}")
            return {
                'query': query,
                'response': "I encountered an error while trying to summarize our conversation.",
                'sources': [],
                'chunks_used': 0,
                'response_time': 0,
                'confidence': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def _create_intelligent_conversation_summary(self, query: str) -> str:
        """Create ChatGPT-style intelligent conversation summary"""
        try:
            query_lower = query.lower()
            
            # Determine summary type based on query
            if 'topic' in query_lower or 'subject' in query_lower:
                return self._create_topic_based_summary()
            elif 'chronological' in query_lower or 'order' in query_lower:
                return self._create_chronological_summary()
            elif 'key' in query_lower or 'main' in query_lower or 'important' in query_lower:
                return self._create_key_points_summary()
            else:
                return self._create_comprehensive_summary()
                
        except Exception as e:
            self.logger.warning(f"[WARNING] Intelligent summary creation failed: {str(e)}")
            return self._create_basic_summary()
    
    def _create_comprehensive_summary(self) -> str:
        """Create a comprehensive summary like ChatGPT"""
        try:
            summary = "## 📋 **Conversation Summary**\n\n"
            
            # Overview
            total_exchanges = len(self.conversation_memory['question_answer_pairs'])
            topics_count = len(self.conversation_memory['topics_discussed'])
            
            summary += f"**Conversation Overview:**\n"
            summary += f"• Total exchanges: {total_exchanges}\n"
            summary += f"• Topics covered: {topics_count}\n"
            summary += f"• Duration: {self._calculate_conversation_duration()}\n\n"
            
            # Topics discussed
            if self.conversation_memory['topics_discussed']:
                summary += "**Topics Discussed:**\n"
                for topic, indices in list(self.conversation_memory['topics_discussed'].items())[:5]:
                    discussion_count = len(indices)
                    topic_summary = self.conversation_memory['summary_by_topic'].get(topic, {}).get('summary', '')
                    summary += f"• **{topic.title()}** ({discussion_count} discussion{'s' if discussion_count > 1 else ''})\n"
                    if topic_summary:
                        summary += f"  ↳ {topic_summary[:100]}...\n"
                summary += "\n"
            
            # Key insights/highlights
            summary += "**Key Insights:**\n"
            key_insights = self._extract_key_insights()
            for insight in key_insights[:3]:
                summary += f"• {insight}\n"
            
            # Recent discussion
            if self.conversation_memory['question_answer_pairs']:
                last_qa = self.conversation_memory['question_answer_pairs'][-1]
                summary += f"\n**🔄 Most Recent Discussion:**\n"
                summary += f"**Q:** {last_qa['question'][:100]}{'...' if len(last_qa['question']) > 100 else ''}\n"
                summary += f"**A:** {last_qa['answer'][:150]}{'...' if len(last_qa['answer']) > 150 else ''}\n"
            
            return summary
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Comprehensive summary creation failed: {str(e)}")
            return self._create_basic_summary()
    
    def _create_topic_based_summary(self) -> str:
        """Create a topic-organized summary"""
        try:
            summary = "## **Summary by Topics**\n\n"
            
            for topic, topic_data in self.conversation_memory['summary_by_topic'].items():
                summary += f"### {topic.title()}\n"
                summary += f"**Discussions:** {topic_data['discussion_count']}\n"
                summary += f"**Summary:** {topic_data['summary']}\n\n"
                
                # Add key Q&A for this topic
                topic_indices = topic_data['indices']
                if topic_indices:
                    recent_idx = topic_indices[-1]  # Most recent discussion
                    if recent_idx < len(self.conversation_memory['question_answer_pairs']):
                        qa = self.conversation_memory['question_answer_pairs'][recent_idx]
                        summary += f"**Recent Q&A:**\n"
                        summary += f"Q: {qa['question'][:80]}...\n"
                        summary += f"A: {qa['answer'][:120]}...\n\n"
                
                summary += "---\n\n"
            
            return summary
            
        except Exception as e:
            return self._create_basic_summary()
    
    def _create_chronological_summary(self) -> str:
        """Create a chronological summary"""
        try:
            summary = "## ⏰ **Chronological Summary**\n\n"
            
            for i, qa_pair in enumerate(self.conversation_memory['question_answer_pairs'], 1):
                summary += f"**{i}. Exchange {i}**\n"
                if qa_pair['topics']:
                    summary += f"*Topic: {', '.join(qa_pair['topics'][:2])}*\n"
                summary += f"**Q:** {qa_pair['question'][:100]}{'...' if len(qa_pair['question']) > 100 else ''}\n"
                summary += f"**A:** {qa_pair['answer'][:120]}{'...' if len(qa_pair['answer']) > 120 else ''}\n\n"
                
                if i >= 5:  # Limit to last 5 exchanges
                    remaining = len(self.conversation_memory['question_answer_pairs']) - 5
                    if remaining > 0:
                        summary += f"*... and {remaining} earlier exchange{'s' if remaining > 1 else ''}*\n"
                    break
            
            return summary
            
        except Exception as e:
            return self._create_basic_summary()
    
    def _create_key_points_summary(self) -> str:
        """Create a key points summary"""
        try:
            summary = "## 🔑 **Key Points Summary**\n\n"
            
            # Main topics
            main_topics = list(self.conversation_memory['topics_discussed'].keys())[:3]
            summary += "**Main Topics:**\n"
            for topic in main_topics:
                summary += f"• {topic.title()}\n"
            summary += "\n"
            
            # Key insights
            insights = self._extract_key_insights()
            summary += "**Key Insights:**\n"
            for insight in insights:
                summary += f"• {insight}\n"
            summary += "\n"
            
            # Important definitions/concepts
            if self.conversation_memory['key_concepts']:
                concepts = list(self.conversation_memory['key_concepts'].keys())[:5]
                summary += "**Key Concepts Discussed:**\n"
                for concept in concepts:
                    summary += f"• {concept.title()}\n"
            
            return summary
            
        except Exception as e:
            return self._create_basic_summary()
    
    def _extract_key_insights(self) -> List[str]:
        """Extract key insights from the conversation"""
        try:
            insights = []
            
            # Look for definition patterns
            for qa_pair in self.conversation_memory['question_answer_pairs']:
                answer = qa_pair['answer'].lower()
                if any(phrase in answer for phrase in ['is defined as', 'refers to', 'means that', 'is a type of']):
                    # Extract the insight
                    sentences = answer.split('.')
                    for sentence in sentences[:2]:
                        if len(sentence.strip()) > 30 and any(phrase in sentence for phrase in ['is defined', 'refers to', 'means']):
                            insights.append(sentence.strip().capitalize())
                            break
            
            # Add topic-based insights
            for topic in list(self.conversation_memory['topics_discussed'].keys())[:2]:
                insights.append(f"Discussed {topic} in detail with practical examples and applications")
            
            return insights[:4]  # Return top 4 insights
            
        except Exception:
            return ["Covered various educational assessment topics", "Explored practical applications and methodologies"]
    
    def _calculate_conversation_duration(self) -> str:
        """Calculate conversation duration"""
        try:
            if not self.conversation_memory['question_answer_pairs']:
                return "Just started"
            
            first_qa = self.conversation_memory['question_answer_pairs'][0]
            last_qa = self.conversation_memory['question_answer_pairs'][-1]
            
            # Simple duration based on number of exchanges
            duration = len(self.conversation_memory['question_answer_pairs'])
            if duration == 1:
                return "1 exchange"
            else:
                return f"{duration} exchanges"
                
        except Exception:
            return "Unknown duration"
    
    def _create_basic_summary(self) -> str:
        """Create a basic fallback summary"""
        try:
            summary = "**Conversation Summary:**\n\n"
            for i, qa_pair in enumerate(self.conversation_memory['question_answer_pairs'][-3:], 1):
                summary += f"**{i}. Q:** {qa_pair['question'][:80]}...\n"
                summary += f"**A:** {qa_pair['answer'][:100]}...\n\n"
            
            total = len(self.conversation_memory['question_answer_pairs'])
            summary += f"Total interactions: {total}"
            
            return summary
            
        except Exception:
            return "We discussed various educational topics in our conversation."
    
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
            self.logger.warning(f"[WARNING] Failed to update conversation history: {str(e)}")
    
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
            self.logger.warning(f"[WARNING] Failed to update session stats: {str(e)}")
    
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
        self.logger.info("[RESET] Conversation history reset")
    
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
                self.logger.warning("[WARNING] Azure download service not available")
                return None
            
            download_url = self.azure_service.generate_download_url(filename, expiry_hours)
            
            if download_url:
                self.logger.info(f"[SUCCESS] Generated download URL for: {filename}")
            else:
                self.logger.warning(f"[WARNING] Could not generate download URL for: {filename}")
            
            return download_url
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error generating download URL for {filename}: {str(e)}")
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
            self.logger.error(f"[ERROR] Error getting PDF info for {filename}: {str(e)}")
            return None
    
    def list_available_pdfs(self) -> List[Dict]:
        """
        List all available PDF files in Azure storage
        
        Returns:
            List of dictionaries with PDF file information
        """
        try:
            if not self.azure_service:
                self.logger.warning("[WARNING] Azure download service not available")
                return []
            
            return self.azure_service.list_available_pdfs()
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error listing PDF files: {str(e)}")
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
                self.logger.warning("[WARNING] Azure download service not available")
                return {filename: None for filename in filenames}
            
            return self.azure_service.batch_generate_download_urls(filenames, expiry_hours)
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error generating batch download URLs: {str(e)}")
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
            self.logger.error(f"[ERROR] Error getting download service stats: {str(e)}")
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
                            print("\n[WARNING] This link expires in 2 hours for security.")
                        else:
                            print(f"[ERROR] Failed to generate download link for: {filename}")
                    else:
                        print(f"[ERROR] File not found: {filename}")
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
                            print(f"     [FILE] File: {source['filename']} (download not available)")
                
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
