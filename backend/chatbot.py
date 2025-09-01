"""
Intelligent Educational Assistant for School Portal - Enhanced Implementation

You are an intelligent educational assistant for a school portal. You should be able to 
understand user questions, retrieve relevant information from the provided knowledge chunks, 
and maintain short-term memory during a session for accurate follow-ups.

Your task:
1. Understand the user's current query.
2. Use the retrieved context chunks (3-4) 
3. Maintain a short-term conversational memory (only within this session) by tracking 
   previous user intents, questions, entities, and references.
4. Resolve pronouns and follow-up references like "that one", "what about this?", 
   "show me more", etc., by inferring meaning from previous questions and retrieved content.
5. Always respond in a helpful, clear, student-friendly tone.

This module provides:
- Intelligent educational query processing and chunk retrieval (3-4 chunks)
- Short-term session memory for follow-up handling
- Context resolution for pronouns and references
- Student-friendly response generation
- Source attribution for educational materials
- Multi-turn conversation support optimized for educational contexts
"""

import os
import sys
import logging
import time
import json
import random
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import re

# Import Azure download service
try:
    from azure_blob_service import create_azure_download_service
    AZURE_DOWNLOAD_AVAILABLE = True
except ImportError:
    AZURE_DOWNLOAD_AVAILABLE = False

# Import Enhanced Metadata service
try:
    from improved_metadata_service import improved_metadata_service
    ENHANCED_METADATA_AVAILABLE = True
except ImportError:
    ENHANCED_METADATA_AVAILABLE = False

# Import Edify API service (fallback)
try:
    from edify_api_service import EdifyAPIService
    EDIFY_API_AVAILABLE = True
except ImportError:
    EDIFY_API_AVAILABLE = False

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
        """
        Initialize Intelligent Educational Assistant for School Portal
        
        Provides intelligent educational assistance with:
        - 3-4 chunk retrieval for comprehensive responses
        - Short-term session memory for follow-up handling
        - Pronoun and reference resolution
        - Student-friendly response generation
        - Educational context awareness
        """
        try:
            # Setup logging first
            self.logger = logging.getLogger(__name__)
            
            self.vector_db = vector_db_manager
            self.config = config
            
            # Configuration - Intelligent Educational Assistant for School Portal
            self.max_context_chunks = config.get('max_context_chunks', 5)  # Increased from 4 to 5 for better context
            self.max_context_length = config.get('max_context_length', 4000)  # Increased for comprehensive responses  
            self.min_similarity_threshold = config.get('min_similarity_threshold', 0.25)  # Lowered for better recall
            self.enable_citations = config.get('enable_citations', True)
            self.enable_context_expansion = config.get('enable_context_expansion', True)  # Enable for better educational coverage
            
            # LLM Configuration - Clear, student-friendly responses
            self.llm_model = config.get('llm_model', 'gpt-3.5-turbo')
            self.max_response_tokens = config.get('max_response_tokens', 2000)  # Increased for detailed responses
            self.temperature = config.get('temperature', 0.7)  # Improved balance for accuracy and helpfulness
            
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
            
            # Initialize Improved Metadata service (primary)
            self.enhanced_metadata_service = improved_metadata_service
            self.logger.info("[SUCCESS] Improved Metadata service initialized successfully")
            
            # Get statistics
            stats = self.enhanced_metadata_service.get_statistics()
            self.logger.info(f"[INFO] Enhanced metadata cached {stats['edify_documents_cached']} documents")
            
            # Initialize Edify API service for document metadata (fallback)
            self.edify_service = None
            if EDIFY_API_AVAILABLE and not self.enhanced_metadata_service:
                try:
                    self.logger.info("[INIT] Initializing Edify API service as fallback...")
                    
                    edify_config = {
                        'edify_api_key': config.get('edify_api_key'),
                        'edify_api_base_url': config.get('edify_api_base_url'),
                        'edify_api_endpoint': config.get('edify_api_endpoint'),
                        'edify_api_timeout': config.get('edify_api_timeout')
                    }
                    
                    self.edify_service = EdifyAPIService(edify_config)
                    self.logger.info("[SUCCESS] Edify API service initialized successfully")
                    
                    # Get cache info
                    cache_info = self.edify_service.get_cache_info()
                    self.logger.info(f"[INFO] Edify API cached {cache_info['documents_cached']} documents")
                    
                except Exception as e:
                    self.logger.warning(f"[WARNING] Edify API service initialization failed: {str(e)}")
                    import traceback
                    self.logger.debug(traceback.format_exc())
            elif self.enhanced_metadata_service:
                self.logger.info("[INFO] Using Enhanced Metadata service, skipping Edify API fallback")
            else:
                self.logger.warning("[WARNING] No metadata service available - using basic filename display")
            
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
            
            self.logger.info("[SUCCESS] Intelligent Educational Assistant initialized for school portal with 3-4 chunk retrieval and session memory")
            
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to initialize chatbot: {str(e)}")
            raise
    
    def _reset_conversation_memory(self, thread_id: str):
        """Reset conversation memory for a new thread (short-term memory approach)"""
        try:
            self.logger.info(f"[MEMORY] Resetting conversation memory for thread: {thread_id}")
            
            # Clear ALL conversation state for thread isolation BUT preserve thread_id
            self.conversation_history = []  # Clear conversation history too
            self.conversation_memory = {
                'topics_discussed': {},
                'key_concepts': {},
                'question_answer_pairs': [],
                'conversation_flow': [],
                'semantic_clusters': {},
                'summary_by_topic': {},
                'thread_id': thread_id,  # CRITICAL: Always preserve thread_id
                'last_reset': datetime.now().isoformat()
            }
            
            # Reset session stats for new thread (optional)
            # self.session_stats['queries_processed'] = 0  # Uncomment if you want to reset stats per thread
            
            self.logger.info(f"[MEMORY] Memory reset complete for thread: {thread_id} - fresh start guaranteed")
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Memory reset failed: {str(e)}")
            # Ensure we at least have a basic memory structure with thread_id
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
    
    def _is_casual_conversation(self, query: str) -> Tuple[bool, str]:
        """Detect casual/conversational queries and return appropriate response"""
        try:
            query_lower = query.lower().strip()
            
            # Remove punctuation for better matching
            query_clean = re.sub(r'[^\w\s]', '', query_lower)
            
            # Casual conversation patterns
            casual_patterns = {
                # Greetings
                'greeting': {
                    'patterns': [
                        r'^(hi|hello|hey|hiya|hii+|helloo+)$',
                        r'^(good morning|good afternoon|good evening)$',
                        r'^(greetings|salutations)$'
                    ],
                    'responses': [
                        "Hi there! I'm here to help you with educational questions. What would you like to know?",
                        "Hello! I'm your Edify AI assistant. How can I help you learn today?",
                        "Hey! Ready to explore some educational topics together?"
                    ]
                },
                
                # Goodbyes
                'goodbye': {
                    'patterns': [
                        r'^(bye|goodbye|see you|farewell|cya|see ya)$',
                        r'^(bye bye|good bye|take care)$',
                        r'^(catch you later|talk to you later|ttyl)$'
                    ],
                    'responses': [
                        "Goodbye! Feel free to come back anytime you have educational questions. Happy learning! 📚",
                        "See you later! Remember, I'm always here to help with your studies. Take care! 🎓",
                        "Bye for now! Keep exploring and learning. I'll be here when you need me! ✨"
                    ]
                },
                
                # How are you
                'wellbeing': {
                    'patterns': [
                        r'^(how are you|how r u|how are u|hows it going|whats up)$',
                        r'^(how you doing|how do you do|hru)$',
                        r'^(whats good|how have you been)$'
                    ],
                    'responses': [
                        "I'm doing great and ready to help you learn! What educational topic interests you today?",
                        "I'm wonderful, thank you for asking! I'm here and excited to assist with your studies. What can I help you with?",
                        "I'm fantastic and always eager to help students learn! What would you like to explore today?"
                    ]
                },
                
                # Name questions
                'name': {
                    'patterns': [
                        r'^(what is your name|whats your name|who are you)$',
                        r'^(what should i call you|do you have a name)$',
                        r'^(tell me your name|introduce yourself)$'
                    ],
                    'responses': [
                        "I'm your Edify AI Assistant! I'm here to help you with educational questions and learning. What would you like to know?",
                        "You can call me Edify AI! I'm your dedicated educational assistant. How can I help you learn today?",
                        "I'm Edify - your intelligent educational companion! I'm here to make learning easier and more engaging. What topic interests you?"
                    ]
                },
                
                # Personal life questions
                'personal': {
                    'patterns': [
                        r'^(daily routine|what do you do|your day|your life)$',
                        r'^(how is your day|tell me about yourself)$',
                        r'^(what are you up to|keeping busy)$'
                    ],
                    'responses': [
                        "My day is all about helping students like you learn and grow! Every question you ask makes my day meaningful. What can I help you discover today?",
                        "I spend my time helping students understand complex topics and making learning fun! Speaking of which, what would you like to learn about?",
                        "My routine is simple but fulfilling - I'm here 24/7 ready to help with educational questions! What subject or topic can I assist you with?"
                    ]
                },
                
                # Thanks
                'thanks': {
                    'patterns': [
                        r'^(thanks|thank you|thx|ty|tysm)$',
                        r'^(thank you so much|thanks a lot|much appreciated)$',
                        r'^(cheers|appreciated)$'
                    ],
                    'responses': [
                        "You're very welcome! I'm always happy to help you learn. Feel free to ask me anything else! 😊",
                        "My pleasure! That's what I'm here for. Is there anything else you'd like to explore?",
                        "Glad I could help! Remember, no question is too small when it comes to learning. What's next?"
                    ]
                },
                
                # Small talk
                'smalltalk': {
                    'patterns': [
                        r'^(nice weather|beautiful day|lovely day)$',
                        r'^(how about that|interesting|cool|awesome)$',
                        r'^(random question|just wondering)$'
                    ],
                    'responses': [
                        "That's nice! You know what else is great? Learning something new every day! What educational topic can I help you with?",
                        "Absolutely! Speaking of interesting things, there's so much fascinating knowledge to explore. What subject interests you?",
                        "I'm always up for a good conversation, especially about learning! What would you like to discover today?"
                    ]
                }
            }
            
            # Check each pattern category
            for category, data in casual_patterns.items():
                for pattern in data['patterns']:
                    if re.match(pattern, query_clean):
                        # Return a random response from the category
                        import random
                        response = random.choice(data['responses'])
                        self.logger.info(f"[CASUAL] Detected {category} query: '{query}' -> casual response")
                        return True, response
            
            # Check for very short queries that might be casual
            if len(query_clean.split()) <= 2:
                short_casual = {
                    'hi': "Hi there! I'm your Edify AI assistant. What would you like to learn today?",
                    'hello': "Hello! Ready to explore some educational topics together?",
                    'hey': "Hey! I'm here to help with your studies. What can I assist you with?",
                    'bye': "Goodbye! Feel free to ask me educational questions anytime. Happy learning! 📚",
                    'thanks': "You're welcome! Is there anything else you'd like to know?",
                    'ok': "Great! What educational topic would you like to explore?",
                    'okay': "Perfect! How can I help you learn today?",
                    'cool': "Glad you think so! What else would you like to discover?",
                    'nice': "Thank you! What subject interests you most?",
                    'wow': "Learning can be amazing! What topic fascinates you?"
                }
                
                if query_clean in short_casual:
                    response = short_casual[query_clean]
                    self.logger.info(f"[CASUAL] Detected short casual query: '{query}' -> casual response")
                    return True, response
            
            return False, ""
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Casual conversation detection failed: {str(e)}")
            return False, ""
    
    def process_query(self, user_query: str, include_context: bool = True, conversation_history: List[Dict] = None, thread_id: str = None) -> Dict:
        """Process user query and generate response with thread-based short-term memory"""
        try:
            start_time = time.time()
            self.session_stats['queries_processed'] += 1
            
            self.logger.info(f"Processing query: {user_query[:100]}...")
            
            # STEP 0: Check for casual/conversational queries first
            is_casual, casual_response = self._is_casual_conversation(user_query)
            if is_casual:
                response_time = time.time() - start_time
                return {
                    'response': casual_response,
                    'sources': [],
                    'confidence': 1.0,
                    'response_time': response_time,
                    'reasoning': "Casual conversation detected - friendly response generated",
                    'chunk_count': 0,
                    'model_used': "casual_conversation_handler",
                    'is_follow_up': False,
                    'session_stats': self.session_stats.copy(),
                    'query_type': 'casual'
                }
            
            # THREAD-BASED MEMORY MANAGEMENT - Initialize or reset memory for new threads
            current_thread_id = thread_id or "default_thread"
            
            # Check if this is a new thread - improved logic to handle memory state
            existing_thread_id = self.conversation_memory.get('thread_id') if self.conversation_memory else None
            is_new_thread = existing_thread_id != current_thread_id
            
            # Debug logging
            self.logger.info(f"[THREAD-DEBUG] Current: {current_thread_id}, Existing: {existing_thread_id}, Memory exists: {self.conversation_memory is not None}, New thread: {is_new_thread}")
            
            if is_new_thread:
                self.logger.info(f"[MEMORY] New thread detected: {current_thread_id} (previous: {existing_thread_id}). Resetting follow-up memory...")
                self._reset_conversation_memory(current_thread_id)
                # For new threads, DO NOT use any conversation history for follow-up detection
                # This ensures fresh start for each thread
                effective_conversation_history = []
                self.logger.info(f"[THREAD-ISOLATION] Starting fresh for new thread: {current_thread_id}")
            else:
                # For same thread, use the conversation history as provided
                effective_conversation_history = conversation_history or []
                self.logger.info(f"[THREAD-CONTINUATION] Continuing thread: {current_thread_id} with {len(effective_conversation_history)} history items")
            
            # SHORT-TERM MEMORY SYSTEM - Update conversation context for current thread only
            if effective_conversation_history:
                self.conversation_history = effective_conversation_history[-10:]  # Keep last 10 messages (short-term)
                # Build memory index for current thread only
                self._build_conversation_memory_index()
            
            # Step 1: Real-time query complexity analysis
            query_complexity = self._analyze_query_complexity(user_query)
            self.logger.info(f"[COMPLEXITY] Query complexity: {query_complexity}")
            
            # Step 2: Detect if this is a follow-up query with thread awareness
            # Only check for follow-ups if we're in the same thread and have conversation history
            # For new threads, always treat as fresh query (no follow-ups)
            if is_new_thread:
                is_follow_up, follow_up_context = False, None
                self.logger.info(f"[THREAD-FRESH] New thread - treating query as fresh (no follow-up detection)")
            else:
                is_follow_up, follow_up_context = self._detect_follow_up_with_thread_memory(user_query, effective_conversation_history)
                self.logger.info(f"[THREAD-MEMORY] Thread continuation - follow-up detection: {is_follow_up}")
            
            # Step 3: Query preprocessing with enhanced memory context
            processed_query = self._preprocess_query(user_query, is_follow_up, follow_up_context)
            
            # Step 4: Determine appropriate namespace for search
            search_namespace = self._determine_query_namespace(user_query, processed_query)
            
            # Step 5: Retrieve relevant chunks (adjust based on complexity)
            relevant_chunks = self._retrieve_relevant_chunks(processed_query, is_follow_up, follow_up_context, search_namespace, query_complexity)
            
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
            
            # Step 7: Update conversation history and memory - Ensure memory is updated BEFORE processing concludes
            self._update_conversation_history(user_query, response, relevant_chunks)
            # Pass the current thread_id to memory update
            self._update_conversation_memory(user_query, response, relevant_chunks, current_thread_id)
            
            # Calculate response time
            response_time = time.time() - start_time
            self._update_session_stats(response_time, len(relevant_chunks))
            
            # Format sources with enhanced logging
            formatted_sources = self._format_sources(relevant_chunks)
            self.logger.info(f"[DEBUG] Formatted {len(formatted_sources)} sources for response")
            for idx, source in enumerate(formatted_sources):
                source_info = f"Source {idx+1}: {source.get('title')} (filename: {source.get('filename')}, download: {source.get('download_available')})"
                self.logger.info(f"[DEBUG] {source_info}")
            
            result = {
                'query': user_query,
                'response': response,
                'reasoning': getattr(self, '_last_reasoning', ''),  # Include actual reasoning for detailed analysis
                'sources': formatted_sources,
                'chunks_used': len(relevant_chunks),
                'response_time': response_time,
                'confidence': self._calculate_confidence(relevant_chunks, query_complexity),
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
                
                # Check for pronouns that might indicate a reference to previous content
                pronouns = ['it', 'they', 'them', 'this', 'that', 'these', 'those', 'he', 'she']
                contains_pronoun = any(pronoun.lower() in query.lower().split() for pronoun in pronouns)
                
                # Only enhance with previous context for high-confidence contextual follow-ups
                is_contextual_followup = (
                    (confidence >= 0.85 or contains_pronoun) and  # Pronoun presence is a strong indicator
                    query_focus in ['general_elaboration', 'examples', 'types', 'details'] and
                    (len(query.split()) <= 10 or contains_pronoun) and  # Allow longer queries if they contain pronouns
                    (any(word in query.lower() for word in ['more', 'examples', 'types', 'that', 'this', 'it', 'they', 'them']) or contains_pronoun)
                )
                
                if is_contextual_followup:
                    # Expand the query with context from previous interaction
                    previous_topic = follow_up_context.get('previous_topic', '')
                    previous_keywords = follow_up_context.get('previous_keywords', [])
                    previous_question = follow_up_context.get('previous_question', '')
                    
                    # Check for pronouns that might need resolution
                    pronouns = ['it', 'they', 'them', 'this', 'that', 'these', 'those', 'he', 'she']
                    contains_pronoun = any(pronoun.lower() in query.lower().split() for pronoun in pronouns)
                    
                    # Add context to improve search (but keep it minimal)
                    if previous_topic:
                        # Only add key terms from previous topic, not the full topic
                        topic_words = previous_topic.split()[:3]  # Take first 3 words only
                        processed_query = f"{' '.join(topic_words)} {processed_query}"
                    
                    # If we have pronouns, try to resolve them using the previous question
                    if contains_pronoun and previous_question:
                        # Extract key nouns/entities from the previous question
                        prev_question_keywords = self._extract_core_keywords(previous_question)
                        if prev_question_keywords:
                            # Add relevant nouns that pronouns might refer to
                            relevant_nouns = [kw for kw in prev_question_keywords[:2] 
                                            if kw not in processed_query and len(kw) > 3]
                            if relevant_nouns:
                                processed_query += f" {' '.join(relevant_nouns)}"
                    
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
                'summative assesment': 'summative assessment',
                'assement': 'assessment',
                'asessment': 'assessment',
                'evalutation': 'evaluation',
                'evaulation': 'evaluation',
                'diferent': 'different',
                'diference': 'difference',
                'effecive': 'effective',
                'effectiv': 'effective',
                'tecnique': 'technique',
                'tecniques': 'techniques',
                'strategie': 'strategies',
                'stratagies': 'strategies'
            }
            
            for typo, correct in typo_fixes.items():
                processed_query = re.sub(rf'\\b{typo}\\b', correct, processed_query, flags=re.IGNORECASE)
            
            # Expand abbreviations and common terms
            abbreviations = {
                'AI': 'artificial intelligence',
                'ML': 'machine learning',
                'NLP': 'natural language processing',
                'API': 'application programming interface',
                'LMS': 'learning management system',
                'IEP': 'individualized education program',
                'RTI': 'response to intervention',
                'PBL': 'project based learning',
                'STEM': 'science technology engineering mathematics',
                'STEAM': 'science technology engineering arts mathematics',
                'SEL': 'social emotional learning',
                'ELL': 'english language learner',
                'ESL': 'english second language',
                'SLO': 'student learning objective',
                'PLN': 'professional learning network',
                'PLC': 'professional learning community'
            }
            
            for abbrev, full_form in abbreviations.items():
                processed_query = re.sub(rf'\\b{abbrev}\\b', full_form, processed_query, flags=re.IGNORECASE)
            
            # Add educational context for better matching
            if 'formative' in processed_query and 'assessment' in processed_query:
                processed_query += ' ongoing assessment assessment for learning continuous evaluation'
            elif 'summative' in processed_query and 'assessment' in processed_query:
                processed_query += ' final assessment assessment of learning end evaluation'
            elif 'assessment' in processed_query:
                processed_query += ' evaluation testing grading measurement'
            elif 'evaluation' in processed_query:
                processed_query += ' assessment testing measurement'
            elif 'pedagogy' in processed_query or 'pedagogical' in processed_query:
                processed_query += ' teaching methods instructional strategies educational approaches'
            elif 'differentiation' in processed_query or 'differentiated' in processed_query:
                processed_query += ' individualized instruction personalized learning adaptive teaching'
            elif 'engagement' in processed_query or 'student engagement' in processed_query:
                processed_query += ' motivation participation active learning student involvement'
            elif 'classroom management' in processed_query:
                processed_query += ' behavior management discipline classroom organization'
            elif 'curriculum' in processed_query:
                processed_query += ' learning standards educational content academic program'
            elif 'learning objectives' in processed_query or 'learning goals' in processed_query:
                processed_query += ' educational outcomes student goals academic targets'
            
            # Add context from conversation history
            if self.conversation_history:
                recent_context = self._get_conversation_context(query, is_follow_up)
                if recent_context:
                    processed_query = f"{recent_context} {processed_query}"
            
            return processed_query.strip()
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Query preprocessing failed: {str(e)}")
            return query
    
    def _determine_query_namespace(self, original_query: str, processed_query: str) -> str:
        """Determine the most appropriate namespace for the query"""
        try:
            # Combine original and processed query for analysis
            combined_query = f"{original_query} {processed_query}".lower()
            
            # Preschool indicators
            preschool_keywords = [
                'preschool', 'pre-school', 'daycare', 'nursery', 'toddler', 
                'early childhood', 'kindergarten prep', 'play-based learning',
                'ages 3-5', 'pre-k', 'infant', 'baby', 'developmental milestone'
            ]
            
            # K12 academic indicators
            k12_academic_keywords = [
                'curriculum', 'lesson plan', 'grade', 'subject', 'math', 'science', 
                'english', 'history', 'geography', 'physics', 'chemistry', 'biology',
                'algebra', 'geometry', 'calculus', 'literature', 'writing', 'reading',
                'assessment', 'exam', 'test', 'homework', 'assignment', 'high school',
                'middle school', 'elementary', 'standards', 'learning objective'
            ]
            
            # Administrative indicators
            admin_keywords = [
                'policy', 'procedure', 'admin', 'management', 'staff', 'employee',
                'hr', 'human resources', 'finance', 'budget', 'compliance', 'audit',
                'legal', 'contract', 'agreement', 'governance', 'operations', 'facility',
                'maintenance', 'safety protocol', 'emergency procedure'
            ]
            
            # Score each namespace
            preschool_score = sum(1 for keyword in preschool_keywords if keyword in combined_query)
            k12_score = sum(1 for keyword in k12_academic_keywords if keyword in combined_query)
            admin_score = sum(1 for keyword in admin_keywords if keyword in combined_query)
            
            # Determine best namespace
            if preschool_score > 0:
                namespace = 'preschool'
                self.logger.info(f"[NAMESPACE] Detected preschool content (score: {preschool_score})")
            elif admin_score > k12_score and admin_score > 0:
                namespace = 'administrative'
                self.logger.info(f"[NAMESPACE] Detected administrative content (score: {admin_score})")
            else:
                namespace = 'k12'
                self.logger.info(f"[NAMESPACE] Using K12 namespace (k12: {k12_score}, admin: {admin_score})")
            
            return namespace
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Namespace determination failed: {str(e)}")
            return 'k12'  # Default fallback
    
    def _detect_follow_up(self, query: str, conversation_history: List[Dict] = None) -> Tuple[bool, Optional[Dict]]:
        """Advanced follow-up detection using semantic understanding, not just keywords"""
        try:
            if not conversation_history or len(conversation_history) < 1:  # Need at least 1 message for context
                return False, None
            
            query_lower = query.lower().strip()
            query_words = query.split()
            
            # Enhanced simple follow-up patterns that work with minimal context
            simple_follow_up_patterns = [
                r'^tell\s+(me\s+)?(more|about)',  # "tell me more", "tell about"
                r'^what\s+about',  # "what about"
                r'^how\s+about',  # "how about" 
                r'^more\s+(details|info)',  # "more details"
                r'^continue',  # "continue"
                r'^go\s+on',  # "go on"
                r'^explain\s+(more|further)',  # "explain more"
                r'^elaborate',  # "elaborate"
                r'^details',  # "details"
                r'^specifically',  # "specifically"
                r'^and\s+',  # "and ..."
                r'^also\s+',  # "also ..."
                r'can\s+u\s+tell\s+more',  # "can u tell more"
                r'tell\s+more\s+clearly',  # "tell more clearly"
                r'more\s+clearly',  # "more clearly"
                r'\b(it|this|that|these|those|they|them)\b',  # Contains pronouns
                r'^what\s+(is|are|were|was)\s+(it|that|this|these|those|they)',
                r'^how\s+(is|are|were|was)\s+(it|that|this|these|those|they)'
            ]
            
            # Check for simple patterns first (very fast)
            is_simple_follow_up = any(re.search(pattern, query_lower) for pattern in simple_follow_up_patterns)
            
            if is_simple_follow_up and len(conversation_history) >= 1:
                # Find the previous exchange
                prev_user_msg = None
                prev_assistant_msg = None
                
                for msg in reversed(conversation_history):
                    if msg.get('role') == 'user' and not prev_user_msg:
                        prev_user_msg = msg.get('content', '')
                    elif msg.get('role') == 'assistant' and not prev_assistant_msg:
                        prev_assistant_msg = msg.get('content', '')
                    
                    if prev_user_msg and prev_assistant_msg:
                        break
                
                if prev_user_msg and prev_assistant_msg:
                    # It's a simple follow-up with context
                    topic = self._extract_semantic_topic(prev_assistant_msg)
                    
                    return True, {
                        'type': 'direct_follow_up',
                        'previous_question': prev_user_msg,
                        'previous_response': prev_assistant_msg[:300] + '...' if len(prev_assistant_msg) > 300 else prev_assistant_msg,
                        'previous_topic': topic,
                        'confidence': 0.85,
                        'detection_reason': 'simple_pattern_match',
                        'detected_phrases': [pattern for pattern in simple_follow_up_patterns if re.search(pattern, query_lower)]
                    }
            
            # Get the last assistant response for context
            last_assistant_msg = None
            for msg in reversed(conversation_history):
                if msg.get('role') == 'assistant':
                    last_assistant_msg = msg
                    break

            if not last_assistant_msg:
                return False, None

            # ADVANCED SEMANTIC ANALYSIS FOR FOLLOW-UP DETECTION - Enhanced for Educational Assistant
            
            # Educational follow-up patterns - school portal specific with conversational references
            educational_follow_up_patterns = [
                r'^what about (.*)',  # "what about math?" 
                r'^and (.*)',  # "and exam dates?"
                r'(show|tell).*(more|about).*(that|this|it)',  # "show me more about that"
                r'(what|how).*(that|this|it|one)',  # "what about that one?"
                r'(similar|same).*(for|in|about)',  # "similar for class 11?"
                r'(other|different).*(subjects|classes|grades)',  # "other subjects?"
                r'(when|where|who).*(for|in).*(that|this)',  # "when for that class?"
                r'(describe|explain).*(more|further)',  # "describe more", "explain further"
                r'(above|previous).*(topic|question|discussion)',  # "above topic", "previous discussion"
                r'what we (discussed|talked about)',  # "what we discussed"
                r'(the|that) topic',  # "the topic", "that topic"
                r'can you (describe|explain|tell).*(more)',  # "can you describe more"
                r'^more (about|on|details)',  # "more about", "more details"
            ]
            
            is_educational_follow_up = any(re.search(pattern, query_lower) for pattern in educational_follow_up_patterns)
            
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
                
                # Educational and conversational specific patterns
                r'^what about',  # "what about math?"
                r'^and (exam|test|homework|assignment|class|subject|grade)',  # "and exam dates?"
                r'^(show|tell).*(me|us)$',  # "show me"
                r'^(describe|explain).*(more)$',  # "describe more"
                r'(above|previous).*(topic|question)',  # "above topic"
                r'what we (discussed|talked)',  # "what we discussed"
                r'^(the|that) topic',  # "the topic"
                r'^more (about|details|info)',  # "more about"
                r'^can you (describe|explain|tell).*(more)',  # "can you describe more"
                r'i said above',  # "i said above topic"
                r'what i (asked|said)',  # "what i asked above"
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
            
            # 6. FINAL DECISION LOGIC - Enhanced for Educational Assistant
            total_score = semantic_score + context_score
            
            # EDUCATIONAL FOLLOW-UP DETECTION - Optimized for school portal queries
            
            # Ultra-high confidence: Educational follow-ups or general follow-ups
            if is_ultra_high_confidence or is_educational_follow_up:
                is_follow_up = True
                confidence = 0.99 if is_ultra_high_confidence else 0.95
            # High confidence - educational context with semantic indicators
            elif total_score >= 5 and semantic_score >= 3:
                is_follow_up = True
                confidence = 0.90
            # Medium confidence - requires strong semantic indicators
            elif total_score >= 4 and semantic_score >= 3:
                is_follow_up = True
                confidence = 0.85
            # IMPORTANT: Independent educational questions should NOT be follow-ups
            elif self._is_independent_educational_question(query):
                is_follow_up = False
                confidence = 0.1
            # Low confidence - treat as new query (most cases)
            else:
                is_follow_up = False
                confidence = 0.1
            
            # 7. EXTRACT COMPREHENSIVE CONTEXT
            if is_follow_up:
                # Find the last assistant response for context
                last_assistant_msg = None
                for msg in reversed(conversation_history):
                    if msg.get('role') == 'assistant':
                        last_assistant_msg = msg
                        break
                
                if last_assistant_msg:
                    previous_content = last_assistant_msg.get('content', '')
                else:
                    previous_content = ""
                
                # Find the last user question (for pronoun resolution)
                last_user_msg = None
                for msg in reversed(conversation_history):
                    if msg.get('role') == 'user' and msg != conversation_history[-1]:  # Not current question
                        last_user_msg = msg
                        break
                
                previous_question = last_user_msg.get('content', '') if last_user_msg else ''
                previous_keywords = self._extract_key_terms(previous_content)
                
                # Extract topic with better semantic understanding
                main_topic = self._extract_semantic_topic(previous_content)
                
                # Identify the specific aspect being asked about
                query_focus = self._identify_query_focus(query, previous_content)
                
                context = {
                    'previous_topic': main_topic,
                    'previous_keywords': previous_keywords,
                    'previous_response': previous_content,
                    'previous_question': previous_question,  # Store previous question for reference resolution
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
    
    def _is_independent_educational_question(self, query: str) -> bool:
        """Check if query is an independent educational question that should not be a follow-up"""
        query_lower = query.lower().strip()
        
        # First check if it's clearly a conversational follow-up
        conversational_follow_up_indicators = [
            'above topic', 'what we discussed', 'that topic', 'the topic',
            'describe more', 'tell me more', 'can you describe',
            'i said above', 'what i asked'
        ]
        
        if any(indicator in query_lower for indicator in conversational_follow_up_indicators):
            return False  # These are clearly follow-ups, not independent questions
        
        # Patterns that indicate independent educational questions
        independent_patterns = [
            r'^what is [a-z]',  # "what is summative assessment"
            r'^how (do|does|can|should)',  # "how do teachers implement"
            r'^why (is|are|do|does)',  # "why is formative assessment important"
            r'^when (should|do|does)',  # "when should teachers use"
            r'^where (can|do|does)',  # "where can students find"
            r'^who (is|are|should)',  # "who should be responsible"
            r'^explain [a-z]',  # "explain formative assessment"
            r'^define [a-z]',  # "define summative assessment"
            r'^describe [a-z]',  # "describe the process"
            r'^list [a-z]',  # "list the benefits"
            r'^compare [a-z]',  # "compare formative and summative"
        ]
        
        # Check if query matches independent question patterns
        return any(re.search(pattern, query_lower) for pattern in independent_patterns)
    
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
                    concepts = self._extract_key_concepts(question, answer)  # Fix parameter signature
                    
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
            # CRITICAL: Verify we're in the same thread for follow-up detection
            current_thread_id = self.conversation_memory.get('thread_id', 'unknown')
            
            # If conversation history exists, use it even if memory hasn't been built yet
            # This ensures follow-up detection works before the first memory update
            if not conversation_history:
                self.logger.info(f"[FOLLOW-UP] No conversation history - treating as new query (Thread: {current_thread_id})")
                return False, None
                
            # We need at least one prior exchange to make a follow-up
            if len(conversation_history) < 2:  # At least one user + assistant exchange
                self.logger.info(f"[FOLLOW-UP] Conversation history too short (<2) - treating as new query (Thread: {current_thread_id})")
                return False, None
            
            # THREAD ISOLATION: Check if all conversation history belongs to current thread
            # This is important to prevent cross-thread follow-up contamination
            thread_safe_history = []
            for msg in conversation_history:
                msg_thread_id = msg.get('thread_id', current_thread_id)  # Default to current if not specified
                if msg_thread_id == current_thread_id:
                    thread_safe_history.append(msg)
                else:
                    self.logger.info(f"[THREAD-ISOLATION] Filtering out message from different thread: {msg_thread_id}")
            
            # Use only thread-safe history for follow-up detection
            if not thread_safe_history or len(thread_safe_history) < 2:
                self.logger.info(f"[THREAD-ISOLATION] No valid thread history for follow-up detection (Thread: {current_thread_id})")
                return False, None
            
            # Print debug info for analysis
            memory_qa_count = len(self.conversation_memory.get('question_answer_pairs', []))
            history_count = len(thread_safe_history)
            self.logger.info(f"[FOLLOW-UP] Thread ID: {current_thread_id}, Memory QA Count: {memory_qa_count}, Safe History Count: {history_count}")
            
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
                    'detection_reason': 'thread_summary_request',
                    'thread_id': current_thread_id
                }
            
            # Use the original advanced detection for other follow-ups (within current thread only)
            is_follow_up, follow_up_context = self._detect_follow_up(query, thread_safe_history)
            
            if is_follow_up:
                # Enhance the context with thread memory
                enhanced_context = follow_up_context.copy() if follow_up_context else {}
                
                # Find related discussions in current thread only
                related_discussions = self._find_related_discussions(query)
                enhanced_context['related_discussions'] = related_discussions
                enhanced_context['thread_memory_available'] = True
                enhanced_context['thread_topics'] = list(self.conversation_memory['topics_discussed'].keys())
                enhanced_context['thread_id'] = current_thread_id
                enhanced_context['thread_safe_history_count'] = len(thread_safe_history)
                
                # Add previously detected phrases if available
                if not enhanced_context.get('detected_phrases'):
                    # Extract potentially pronoun references
                    pronouns = ['it', 'this', 'that', 'these', 'those', 'they', 'them']
                    detected_phrases = [word for word in query_words if word.lower() in pronouns]
                    if detected_phrases:
                        enhanced_context['detected_phrases'] = detected_phrases
                
                # Add previous query/topic context if available (from current thread only)
                if len(self.conversation_memory['question_answer_pairs']) > 0:
                    last_qa = self.conversation_memory['question_answer_pairs'][-1]
                    enhanced_context['previous_query'] = last_qa.get('question', '')
                    enhanced_context['previous_topic'] = self._extract_semantic_topic(last_qa.get('answer', ''))
                
                self.logger.info(f"[FOLLOW-UP] Detected follow-up query in thread {current_thread_id}: '{query}'. Reason: {enhanced_context.get('detection_reason', 'pattern_match')}")
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
            query_concepts = self._extract_key_concepts(query, "")  # Pass empty response for concept extraction
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
    
    def _resolve_pronouns(self, query: str, previous_question: str, previous_response: str) -> Dict[str, Any]:
        """
        Analyze a follow-up query for pronouns and attempt to resolve them
        Returns information about detected pronouns and potential referents
        """
        result = {
            "contains_pronoun": False,
            "pronoun_type": None,
            "potential_referents": [],
            "pronoun_context": ""
        }
        
        # Common pronouns to detect
        singular_pronouns = ['it', 'this', 'that']
        plural_pronouns = ['they', 'them', 'these', 'those']
        human_pronouns = ['he', 'she', 'him', 'her']
        all_pronouns = singular_pronouns + plural_pronouns + human_pronouns
        
        # Check if query contains pronouns
        query_words = query.lower().split()
        found_pronouns = [p for p in all_pronouns if p in query_words]
        
        if not found_pronouns:
            return result
            
        result["contains_pronoun"] = True
        
        # Determine the type of pronoun (for providing appropriate context)
        if any(p in found_pronouns for p in singular_pronouns):
            result["pronoun_type"] = "singular"
            # Try to extract the main subject from the previous question
            potential_referents = self._extract_core_keywords(previous_question)[:2]
            result["potential_referents"] = potential_referents
            
            # Create helpful context for resolving the pronoun
            if potential_referents:
                result["pronoun_context"] = (
                    f"Note: The pronouns 'it/this/that' likely refer to '{' or '.join(potential_referents)}' "
                    f"from the previous conversation. Previous question: '{previous_question}'"
                )
                
        elif any(p in found_pronouns for p in plural_pronouns):
            result["pronoun_type"] = "plural"
            # Extract potential plural subjects from previous response
            potential_referents = self._extract_potential_referents(previous_question, previous_response)
            result["potential_referents"] = potential_referents
            
            # Create helpful context for resolving the pronoun
            if potential_referents:
                result["pronoun_context"] = (
                    f"Note: The pronouns 'they/them/these/those' likely refer to '{' or '.join(potential_referents[:2])}' "
                    f"from the previous conversation. Previous question: '{previous_question}'"
                )
        
        elif any(p in found_pronouns for p in human_pronouns):
            result["pronoun_type"] = "human"
            # Try to find person references in the previous conversation
            human_referents = []
            for person_pattern in [r'([A-Z][a-z]+ [A-Z][a-z]+)', r'(teacher|student|parent|child|person)']:
                matches = re.findall(person_pattern, previous_response + " " + previous_question)
                human_referents.extend(matches)
                
            result["potential_referents"] = human_referents
            
            # Create helpful context for resolving the pronoun
            if human_referents:
                result["pronoun_context"] = (
                    f"Note: The pronouns 'he/she/him/her' likely refer to '{human_referents[0]}' "
                    f"mentioned in the previous conversation."
                )
        
        return result
    
    def _retrieve_relevant_chunks(self, query: str, is_follow_up: bool = False, follow_up_context: Dict = None, namespace: str = None, complexity: str = 'MODERATE') -> List[Dict]:
        """Retrieve most relevant chunks using enhanced vector search - optimized for accuracy"""
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
            
            # Adjust search parameters based on query complexity - REAL-TIME ACCURACY
            if complexity == 'SIMPLE':
                search_top_k = 15  # Increased significantly for comprehensive coverage
                max_chunks = 10    # More chunks for better accuracy
            elif complexity == 'COMPLEX':
                search_top_k = 25  # Much higher for complex queries
                max_chunks = 15    # More chunks for complex topics
            else:  # MODERATE
                search_top_k = 20  # Significantly increased for better coverage
                max_chunks = 12    # More chunks for accurate responses
            
            self.logger.info(f"[REAL-TIME SEARCH] Complexity: {complexity}, top_k: {search_top_k}, max_chunks: {max_chunks}")
            
            # COMPREHENSIVE MULTI-STRATEGY SEARCH APPROACH
            all_candidate_chunks = []
            
            # Strategy 1: Primary semantic search
            primary_results = self.vector_db.search_similar_chunks(
                query=query,
                top_k=search_top_k,
                namespace=namespace
            )
            all_candidate_chunks.extend(primary_results)
            self.logger.info(f"[STRATEGY 1] Primary semantic search found {len(primary_results)} chunks")
            
            # Strategy 2: Content-type enhanced searches
            query_lower = query.lower()
            enhanced_searches = []
            
            # Holiday content enhancement
            if any(word in query_lower for word in ['holiday', 'holidays', 'vacation', 'break', 'celebration', 'festival']):
                holiday_enhanced = query + " holiday list academic calendar north campus south campus Independence Day Christmas Diwali festival celebration LOHRI BAISAKHI MAHAVEER"
                enhanced_searches.append(("HOLIDAY", holiday_enhanced))
                
            # Form content enhancement
            if any(word in query_lower for word in ['form', 'slip', 'observation', 'report', 'signature', 'template']):
                form_enhanced = query + " form template observation slip fields signature date name student class section undertaking"
                enhanced_searches.append(("FORM", form_enhanced))
                
            # Execute enhanced searches
            for search_type, enhanced_query in enhanced_searches:
                enhanced_results = self.vector_db.search_similar_chunks(
                    query=enhanced_query,
                    top_k=search_top_k,
                    namespace=namespace
                )
                # Mark chunks with their search strategy
                for chunk in enhanced_results:
                    chunk['search_strategy'] = search_type
                    
                all_candidate_chunks.extend([chunk for chunk in enhanced_results if chunk not in all_candidate_chunks])
                self.logger.info(f"[STRATEGY 2-{search_type}] Enhanced search found {len(enhanced_results)} additional chunks")
            
            # Strategy 3: Keyword-focused search
            core_keywords = self._extract_core_keywords(query)
            if core_keywords:
                keyword_query = " ".join(core_keywords) + " " + query
                keyword_results = self.vector_db.search_similar_chunks(
                    query=keyword_query,
                    top_k=search_top_k // 2,
                    namespace=namespace
                )
                for chunk in keyword_results:
                    chunk['search_strategy'] = 'KEYWORD'
                    
                all_candidate_chunks.extend([chunk for chunk in keyword_results if chunk not in all_candidate_chunks])
                self.logger.info(f"[STRATEGY 3] Keyword search found {len(keyword_results)} additional chunks")
            
            # INTELLIGENT CONTENT FILTERING
            relevant_chunks = []
            
            for chunk in all_candidate_chunks:
                content = chunk.get('content', '').lower()
                text = chunk.get('text', '').lower()
                combined_text = (content + ' ' + text).lower()
                similarity_score = chunk.get('similarity_score', 0)
                
                # Dynamic relevance scoring
                relevance_score = similarity_score
                
                # Holiday-specific boost
                if any(word in query_lower for word in ['holiday', 'holidays']):
                    holiday_indicators = [
                        'academic holidays', 'holiday list', 'list of holidays', 'north campus', 'south campus',
                        'independence day', 'christmas', 'diwali', 'lohri', 'baisakhi', 'mahaveer jayanthi', 
                        'varalakshmi vratham', 'ugadi', 'ganesh chaturthi'
                    ]
                    
                    holiday_matches = sum(1 for indicator in holiday_indicators if indicator in combined_text)
                    if holiday_matches > 0:
                        relevance_score += 0.3 + (holiday_matches * 0.1)
                        
                    # Extra boost for campus-specific holidays
                    if 'north campus' in combined_text or 'south campus' in combined_text:
                        relevance_score += 0.4
                
                # Form-specific boost
                elif any(word in query_lower for word in ['form', 'slip', 'observation']):
                    form_indicators = [
                        'observation slip', 'disciplinary action', 'class report', 'name of student',
                        'class & section', 'date of observation', 'signature', 'teacher signature'
                    ]
                    
                    form_matches = sum(1 for indicator in form_indicators if indicator in combined_text)
                    if form_matches > 0:
                        relevance_score += 0.3 + (form_matches * 0.1)
                
                # Query keyword matching boost
                query_words = query_lower.split()
                keyword_matches = sum(1 for word in query_words if word in combined_text)
                keyword_ratio = keyword_matches / len(query_words) if query_words else 0
                relevance_score += keyword_ratio * 0.2
                
                # Store enhanced relevance score
                chunk['enhanced_relevance'] = relevance_score
                
                # Adaptive threshold
                threshold = 0.15 if len(relevant_chunks) < 5 else 0.20
                
                if relevance_score >= threshold:
                    relevant_chunks.append(chunk)
                    self.logger.info(f"[CONTENT ANALYSIS] Included chunk with relevance {relevance_score:.3f} (strategy: {chunk.get('search_strategy', 'PRIMARY')})")
            
            # Sort by enhanced relevance and limit results
            relevant_chunks.sort(key=lambda x: x.get('enhanced_relevance', 0), reverse=True)
            final_chunks = relevant_chunks[:max_chunks]
            
            # Quality validation and results
            if final_chunks:
                avg_relevance = sum(chunk.get('enhanced_relevance', 0) for chunk in final_chunks) / len(final_chunks)
                strategy_distribution = {}
                for chunk in final_chunks:
                    strategy = chunk.get('search_strategy', 'PRIMARY')
                    strategy_distribution[strategy] = strategy_distribution.get(strategy, 0) + 1
                    
                self.logger.info(f"[REAL-TIME SEARCH SUCCESS] Retrieved {len(final_chunks)} high-quality chunks")
                self.logger.info(f"[QUALITY METRICS] Avg relevance: {avg_relevance:.3f}, Strategy distribution: {strategy_distribution}")
            else:
                self.logger.warning(f"[REAL-TIME SEARCH] No chunks met enhanced relevance criteria for query: {query[:100]}")
            
            return final_chunks
        except Exception as e:
            self.logger.error(f"[ERROR] Real-time chunk retrieval failed: {str(e)}")
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
            
        except Exception as e:
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
                    expanded_chunks.extend([n for n in neighbors if n not in expanded_chunks])
            
            return expanded_chunks[:15]  # Limit expanded context
            
        except Exception as e:
            self.logger.warning(f"Context expansion failed: {str(e)}")
            return chunks  # Return original chunks if expansion fails
    
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
                max_context_for_comprehensive = 12000  # SIGNIFICANTLY INCREASED for accuracy
                if current_length + chunk_length > max_context_for_comprehensive and context_parts:
                    self.logger.info(f"[CONTEXT] Limiting context to {max_context_for_comprehensive} chars for comprehensive responses")
                    break
                
                # Format chunk with source information
                source_file = chunk.get('metadata', {}).get('filename', 'unknown')
                formatted_chunk = f"Source: {source_file}\\n{chunk_text}\\n"
                
                context_parts.append(formatted_chunk)
                current_length += chunk_length
            
            final_context = "\\n".join(context_parts)
            self.logger.info(f"[CONTEXT] Optimized context: {len(final_context)} chars from {len(chunks)} chunks")
            
            return final_context
            
        except Exception as e:
            self.logger.error(f"Context optimization failed: {str(e)}")
            # Return basic concatenation as fallback
            return "\\n".join([chunk.get('text', '') for chunk in chunks[:5]])
    
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
            
            # Sort within each document by chunk order
            sorted_chunks = []
            for filename, group_chunks in doc_groups.items():
                # Sort by chunk index within document
                group_chunks.sort(key=lambda x: x.get('metadata', {}).get('chunk_index', 0))
                sorted_chunks.extend(group_chunks)
            
            return sorted_chunks
            
        except Exception as e:
            self.logger.warning(f"Chunk sorting failed: {str(e)}")
            return chunks  # Return original order if sorting fails

    def _analyze_query_complexity(self, query: str) -> str:
        """
        Real-time query complexity analysis for response optimization
        Returns: 'SIMPLE', 'MODERATE', or 'COMPLEX'
        """
        query_lower = query.lower().strip()
        word_count = len(query.split())
        
        # Simple query indicators
        simple_indicators = [
            'what is', 'who is', 'when is', 'where is', 'define',
            'list', 'name', 'show', 'find', 'get', 'tell me'
        ]
        
        # Complex query indicators  
        complex_indicators = [
            'compare', 'analyze', 'evaluate', 'explain why', 'how does',
            'what are the differences', 'pros and cons', 'advantages and disadvantages',
            'implement', 'strategy', 'methodology', 'framework', 'comprehensive',
            'in-depth', 'detailed analysis', 'step-by-step'
        ]
        
        # Multi-part query indicators
        multi_part_indicators = ['and', 'also', 'additionally', 'furthermore', 'moreover']
        
        # Determine complexity
        if word_count <= 5:
            return 'SIMPLE'
        elif any(indicator in query_lower for indicator in complex_indicators):
            return 'COMPLEX'
        elif word_count > 15 or sum(1 for indicator in multi_part_indicators if indicator in query_lower) >= 2:
            return 'COMPLEX'
        elif word_count > 10 or any(indicator in query_lower for indicator in ['how', 'why', 'explain']):
            return 'MODERATE'
        elif any(indicator in query_lower for indicator in simple_indicators):
            return 'SIMPLE'
        else:
            return 'MODERATE'

    def _generate_llm_response(self, query: str, context: str, is_follow_up: bool = False, follow_up_context: Dict = None) -> str:
        """Generate response using LLM service with optimized context"""
        try:
            # Determine if a short response is requested - Default to comprehensive for Edify expertise
            should_be_concise = False  # Default to comprehensive responses with Edify persona
            concise_indicators = ['brief', 'short', 'quick', 'summary', 'bullet points']
            if any(indicator in query.lower() for indicator in concise_indicators):
                should_be_concise = True
                self.logger.info("[CONCISE] User requested a brief response")
            else:
                self.logger.info("[COMPREHENSIVE] Using default comprehensive response mode for Edify expertise")
                
            # Try to use LLM service if available
            if hasattr(self, 'llm_service') and self.llm_service:
                try:
                    self.logger.info("Using LLM service for response generation...")
                    
                    # Enhance the query and context for follow-up questions
                    enhanced_query = query
                    enhanced_context = context
                    
                    if is_follow_up and follow_up_context:
                        self.logger.info("[FOLLOW-UP] Enhancing LLM prompt with conversation context")
                        
                        # Extract previous question and response for context
                        previous_question = follow_up_context.get('previous_question', '')
                        previous_response = follow_up_context.get('previous_response', '')
                        previous_topic = follow_up_context.get('previous_topic', '')
                        
                        # Use our specialized pronoun resolution method
                        pronoun_info = self._resolve_pronouns(query, previous_question, previous_response)
                        
                        # Get the context for the prompt
                        pronoun_context = pronoun_info.get("pronoun_context", "")
                        
                        # Add follow-up instructions to the query with pronoun resolution if needed
                        follow_up_instruction = (
                            f"STRICT INSTRUCTION: You must ONLY use information from the provided documents. "
                            f"Do NOT use your general knowledge or training data. "
                            f"If the documents don't contain enough information, say so explicitly. "
                            f"This is a follow-up question to a previous conversation. "
                            f"Previous topic: {follow_up_context.get('previous_topic', '')} "
                            f"Previous question: {previous_question} "
                            f"{pronoun_context} "
                            f"The user is asking for more information related to the previous topic. "
                            f"{'Please provide a comprehensive, detailed answer using ONLY the provided documents.' if not should_be_concise else 'Please provide a brief, focused answer using ONLY the provided documents.'} "
                            f"Current question: {query}"
                        )
                        enhanced_query = follow_up_instruction
                        
                        # Add previous response context if available
                        if follow_up_context.get('previous_response'):
                            enhanced_context = f"Previous response context: {follow_up_context['previous_response'][:300]}\\n\\n{context}"
                    elif should_be_concise:
                        # Add instruction for conciseness even for non-follow-up questions
                        enhanced_query = (
                            f"EXTRACT AND USE: Find ALL relevant information from the educational documents provided. "
                            f"NEVER refuse to answer if ANY content relates to the topic. "
                            f"Extract specific details, strategies, or examples from the documents. "
                            f"Provide a clear, actionable answer based on document content. "
                            f"Be comprehensive and provide detailed guidance from Edify expertise. "
                            f"Question: {query}"
                        )
                    else:
                        # For verbose responses - AGGRESSIVE CONTENT EXTRACTION
                        enhanced_query = (
                            f"CRITICAL INSTRUCTION: You MUST extract and use ALL relevant information from the provided educational documents. "
                            f"NEVER say you cannot find information if ANY content relates to the query. "
                            f"Your task: Extract specific details, methods, strategies, examples, and insights from the documents. "
                            f"Even if the documents don't perfectly match the question, find related educational principles and adapt them. "
                            f"Provide comprehensive, actionable guidance based on the document content. "
                            f"Question: {query}"
                        )
                    
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
                        
                        # Apply response length control if needed
                        response = llm_response['response']
                        
                        # Validate that response only uses document information (temporarily disabled for testing)
                        # if self._contains_external_knowledge(response, enhanced_context):
                        #     self.logger.warning("[WARNING] LLM used external knowledge, using fallback")
                        #     return self._generate_fallback_response(query, context, is_follow_up, follow_up_context)
                        
                        if should_be_concise:
                            response = self._ensure_concise_response(response, max_sentences=3)
                            self.logger.info("[CONCISE] Applied user-requested concise response format")
                        else:
                            self.logger.info("[COMPREHENSIVE] Delivering full Edify expertise response")
                            
                        return response
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

    def _add_citations(self, response: str, chunks: List[Dict]) -> str:
        """Add citations and source attribution to response"""
        try:
            # Don't add citations to the response text anymore
            # Citations will be handled separately in the sources section
            return response
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Citation addition failed: {str(e)}")
            return response

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

    def _update_conversation_memory(self, query: str, response: str, chunks: List[Dict], thread_id: str = None):
        """Update conversation memory for ChatGPT-style short-term memory"""
        try:
            # Ensure thread_id is set - use passed parameter or get from existing memory
            if thread_id:
                if not self.conversation_memory.get('thread_id') or self.conversation_memory.get('thread_id') != thread_id:
                    # New thread - reset memory
                    self._reset_conversation_memory(thread_id)
            elif not self.conversation_memory.get('thread_id'):
                self.logger.warning("[MEMORY] No thread_id provided, using default")
                self.conversation_memory['thread_id'] = 'default_thread'
                
            # Log memory operation for debugging
            memory_thread_id = self.conversation_memory.get('thread_id', 'unknown')
            self.logger.info(f"[MEMORY] Updating conversation memory for thread: {memory_thread_id}")
            
            # Add the Q&A pair to conversation memory
            qa_pair = {
                'question': query,
                'answer': response,
                'timestamp': datetime.now().isoformat(),
                'chunks_used': len(chunks),
                'sources': [chunk.get('filename', 'Unknown') for chunk in chunks[:3]]  # Top 3 sources
            }
            
            # Initialize question_answer_pairs if not present
            if 'question_answer_pairs' not in self.conversation_memory:
                self.conversation_memory['question_answer_pairs'] = []
                
            self.conversation_memory['question_answer_pairs'].append(qa_pair)
            
            # Extract and store topics from the query and response
            combined_text = f"{query} {response}"
            words = combined_text.lower().split()
            
            # Initialize topics_discussed if not present
            if 'topics_discussed' not in self.conversation_memory:
                self.conversation_memory['topics_discussed'] = {}
            
            # Simple topic extraction - look for educational keywords
            educational_topics = ['holiday', 'assessment', 'discipline', 'policy', 'student', 'teacher', 
                                'school', 'preschool', 'form', 'observation', 'behavior', 'curriculum',
                                'admission', 'fee', 'uniform', 'schedule', 'academic', 'examination']
            
            current_index = len(self.conversation_memory['question_answer_pairs']) - 1
            
            for topic in educational_topics:
                if topic in words:
                    if topic not in self.conversation_memory['topics_discussed']:
                        self.conversation_memory['topics_discussed'][topic] = []
                    self.conversation_memory['topics_discussed'][topic].append(current_index)
            
            # Keep only last 10 Q&A pairs for short-term memory
            if len(self.conversation_memory['question_answer_pairs']) > 10:
                self.conversation_memory['question_answer_pairs'] = self.conversation_memory['question_answer_pairs'][-10:]
                
                # Update topic indices after trimming
                trim_offset = len(self.conversation_memory['question_answer_pairs']) - 10
                for topic in self.conversation_memory['topics_discussed']:
                    self.conversation_memory['topics_discussed'][topic] = [
                        idx - trim_offset for idx in self.conversation_memory['topics_discussed'][topic] 
                        if idx >= trim_offset
                    ]
            
            self.logger.info(f"[MEMORY] Successfully updated conversation memory: {len(self.conversation_memory['question_answer_pairs'])} Q&A pairs, "
                           f"Thread: {self.conversation_memory.get('thread_id', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to update conversation memory: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())

    def _update_session_stats(self, response_time: float = 0, chunk_count: int = 0):
        """Update session statistics"""
        try:
            # Simple stub implementation for now
            pass
        except Exception as e:
            self.logger.warning(f"[WARNING] Failed to update session stats: {str(e)}")
            
    def _get_display_name_from_filename(self, filename: str) -> str:
        """Extract a user-friendly display name from a filename"""
        try:
            # Remove file extension
            if '.' in filename:
                base_name = filename.rsplit('.', 1)[0]
            else:
                base_name = filename
                
            # Extract last part of path if present
            if '/' in base_name or '\\' in base_name:
                base_name = base_name.replace('\\', '/').split('/')[-1]
                
            # Replace underscores and hyphens with spaces
            display_name = base_name.replace('_', ' ').replace('-', ' ')
            
            # Capitalize first letter of each word
            display_name = ' '.join(word.capitalize() for word in display_name.split())
            
            return display_name
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Failed to get display name: {str(e)}")
            return filename
            
    def _calculate_confidence(self, chunks: List[Dict], query_complexity: str = 'MODERATE') -> float:
        """Calculate confidence score based on relevance and complexity"""
        try:
            if not chunks:
                return 0.3  # Low confidence if no results
            
            # Extract relevance scores from chunks
            relevance_scores = [chunk.get('enhanced_relevance', chunk.get('similarity_score', 0)) for chunk in chunks]
            
            if not relevance_scores:
                return 0.3  # Low confidence if no valid scores
                
            # Calculate average relevance score
            avg_relevance = sum(relevance_scores) / len(relevance_scores)
            
            # Adjust confidence based on query complexity
            if query_complexity == 'SIMPLE':
                base_confidence = 0.8 if avg_relevance > 0.7 else 0.6
            elif query_complexity == 'MODERATE':
                base_confidence = 0.7 if avg_relevance > 0.6 else 0.5
            else:  # COMPLEX
                base_confidence = 0.6 if avg_relevance > 0.5 else 0.4
                
            # Adjust for number of results
            if len(relevance_scores) >= 5:
                base_confidence += 0.1
            
            # Ensure confidence is within range [0.1, 1.0]
            return min(max(base_confidence, 0.1), 1.0)
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Failed to calculate confidence: {str(e)}")
            return 0.5  # Default moderate confidence
            
    def _format_sources(self, chunks: List[Dict]) -> List[Dict]:
        """Format source information for response with download URLs and original filenames"""
        try:
            # Extract unique filenames from chunks
            file_sources = {}
            
            for chunk in chunks:
                # Extract filename from chunk metadata
                filename = chunk.get('metadata', {}).get('filename', '')
                
                if filename:
                    # Use the full filename as the key instead of extracting UUID
                    if filename not in file_sources:
                        # Initialize source entry
                        source_entry = {
                            'filename': filename,  # Use actual filename for download
                            'title': self._get_display_name_from_filename(filename),
                            'download_url': None,
                            'excerpt': chunk.get('text', '')[:200] + '...' if chunk.get('text') else None
                        }
                        
                        # Try to generate download URL if Azure service is available
                        if hasattr(self, 'azure_service') and self.azure_service:
                            try:
                                # Use the actual filename for Azure download
                                download_url = self.azure_service.generate_download_url(filename)
                                source_entry['download_url'] = download_url
                                source_entry['download_available'] = download_url is not None
                                self.logger.info(f"Generated download URL for {filename}: {'SUCCESS' if download_url else 'FAILED'}")
                            except Exception as e:
                                self.logger.warning(f"[WARNING] Failed to generate download URL for {filename}: {str(e)}")
                                source_entry['download_url'] = None
                                source_entry['download_available'] = False
                        else:
                            source_entry['download_available'] = False
                        
                        file_sources[filename] = source_entry
            
            # Format sources for response
            formatted_sources = []
            for filename, source_info in file_sources.items():
                # Create source object with correct filename for download
                source = {
                    'title': source_info.get('title', ''),
                    'filename': filename,  # Use actual filename that Azure recognizes
                    'name': source_info.get('title', ''),
                    'excerpt': source_info.get('excerpt'),
                    'download_url': source_info.get('download_url'),
                    'download_available': source_info.get('download_available', False)
                }
                
                formatted_sources.append(source)
            
            self.logger.info(f"[SUCCESS] Formatted {len(formatted_sources)} sources for download")
            return formatted_sources
            
        except Exception as e:
            self.logger.error(f"[ERROR] Source formatting failed: {str(e)}")
            return []
            
    def _generate_fallback_response(self, query: str, context: str, is_follow_up: bool = False, follow_up_context: Dict = None) -> str:
        """Generate fallback response when LLM service is unavailable"""
        try:
            # Extract educational content from context
            context_lines = context.split('\n')
            content_snippets = []
            
            # Extract meaningful content from context
            for line in context_lines:
                line = line.strip()
                if line and len(line) > 20 and not line.startswith('[Source:'):
                    content_snippets.append(line)
            
            # Handle insufficient content case
            if not content_snippets:
                return "I couldn't find specific information about that in the current materials."
            
            # Generate simple response based on context
            response = content_snippets[0]
            
            # Add supplementary information if available
            if len(content_snippets) > 1 and len(response) < 200:
                response += f"\n\n{content_snippets[1]}"
            
            # Ensure response is within reasonable length
            if len(response) > 400:
                response = response[:400] + "..."
            
            return response
            
        except Exception as e:
            self.logger.error(f"[ERROR] Fallback response generation failed: {str(e)}")
            return "I encountered an issue processing your question. Please try again."


# DUAL CHATBOT CONFIGURATION
class DualChatbotConfig:
    """Configuration for dual chatbot with fallback"""
    
    def __init__(self):
        self.primary_config = {
            'model': 'gemini-2.0-flash-exp',
            'temperature': 0.1,
            'max_tokens': 4000
        }
        self.fallback_config = {
            'model': 'gemini-1.5-pro',
            'temperature': 0.2,
            'max_tokens': 3000
        }


class AIChildrensChatbotInterface:
    """Dual AI Children's Educational Chatbot Interface with fallback support"""
    
    def __init__(self, vector_db_manager, azure_service, llm_service, config: Dict):
        """Initialize the dual chatbot system"""
        self.vector_db = vector_db_manager
        self.azure_service = azure_service
        self.llm_service = llm_service
        self.config = config
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Configuration settings
        self.max_conversation_history = config.get('max_conversation_history', 10)
        self.conversation_memory = {}
        self.session_stats = {}
        
        self.logger.info("AIChildrensChatbotInterface initialized")
    
    def process_simple_query(self, query: str) -> str:
        """Simple query processing for children's interface"""
        try:
            # Basic implementation - can be expanded
            return f"Processing query: {query}"
        except Exception as e:
            self.logger.error(f"Error in simple query processing: {str(e)}")
            return "Sorry, I couldn't process that question."
            
            self.logger.info(f"[EDUCATIONAL_SEARCH] Found {len(primary_results)} chunks passed filtering")
            
            # If we have too few results, apply even more lenient threshold for educational content
            if len(primary_results) < 3 and primary_results:
                # Educational content strategy: Very low threshold for maximum coverage
                lower_threshold = 0.15  # Very low threshold for comprehensive results
                additional_results = self.vector_db.search_similar_chunks(
                    query=query, 
                    top_k=search_top_k + 5, 
                    namespace=namespace
                )
                primary_results.extend([
                    chunk for chunk in additional_results
                    if chunk.get('similarity_score', 0) >= lower_threshold and chunk not in primary_results
                ])
                self.logger.info(f"[EDUCATIONAL_SEARCH] Applied very low threshold {lower_threshold:.2f} to find {len(primary_results)} chunks")
            
            # Select ALL relevant chunks for comprehensive educational response
            relevant_chunks = primary_results[:max_chunks]  # Use increased complexity-based limit
            
            # Additional quality check - ensure chunks are actually relevant
            if relevant_chunks:
                # Log chunk quality for monitoring
                avg_similarity = sum(chunk.get('similarity_score', 0) for chunk in relevant_chunks) / len(relevant_chunks)
                self.logger.info(f"[SEARCH] Retrieved {len(relevant_chunks)} high-quality chunks (avg similarity: {avg_similarity:.3f})")
            else:
                self.logger.warning(f"[SEARCH] No chunks met quality threshold {self.min_similarity_threshold}")
            
            return relevant_chunks
            
        except Exception as e:
            self.logger.error(f"[ERROR] Chunk retrieval failed: {str(e)}")
            return []
            
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
                max_context_for_comprehensive = 12000  # SIGNIFICANTLY INCREASED for accuracy (from 3000)
                if current_length + chunk_length > max_context_for_comprehensive and context_parts:
                    self.logger.info(f"[CONTEXT] Limiting context to {max_context_for_comprehensive} chars for comprehensive responses")
                    break
                
                # Format chunk with source information (simplified for better extraction)
                source_file = chunk.get('metadata', {}).get('filename', 'unknown')
                chunk_index = chunk.get('metadata', {}).get('chunk_index', 0)
                
                # Simpler formatting that's easier to parse
                formatted_chunk = f"[Source: {source_file}, Section {int(chunk_index) + 1}]\n{chunk_text}\n"
                
                context_parts.append(formatted_chunk)
                current_length += len(formatted_chunk)
            
            # Combine context with clear separators
            optimized_context = "\n--- RELEVANT INFORMATION ---\n".join(context_parts)
            
            self.logger.info(f"[CONTEXT] Optimized context: {len(context_parts)} chunks, {current_length} characters")
            # Log a sample of the context for debugging
            if optimized_context:
                sample_context = optimized_context[:200] + "..." if len(optimized_context) > 200 else optimized_context
                self.logger.info(f"[CONTEXT] Sample context: {sample_context}")
            
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
    

    def _extract_potential_referents(self, previous_question: str, previous_response: str) -> List[str]:
        """Extract potential referents for pronouns from previous conversation"""
        try:
            referents = []
            # Look for plural nouns in the previous response that might be referenced by "they"
            plural_patterns = [
                r'(\w+s)\b(?=\s+are\b)',  # Words ending in 's' followed by 'are'
                r'(\w+s)\b(?=\s+(were|have|do))',  # Words ending in 's' followed by 'were', 'have', 'do'
                r'(students|teachers|people|children|parents|schools|districts|resources|tools|methods)',  # Common educational plural nouns
                r'(assessments|evaluations|tests|quizzes|exams|scores|grades|results|standards)',  # Educational assessment terms
                r'(\w+s)\b(?=\s+include\b)',  # Words ending in 's' followed by 'include'
                r'(\w+s)\b(?=\s+have\b)',  # Words ending in 's' followed by 'have'
                r'(\w+ies)\b',  # Words ending in 'ies' (potential plurals like strategies)
                r'several\s+(\w+s)\b',  # "several X" patterns
                r'various\s+(\w+s)\b',  # "various X" patterns
                r'different\s+(\w+s)\b',  # "different X" patterns
                r'many\s+(\w+s)\b'  # "many X" patterns
            ]
            
            # Common educational plural concepts that might be referenced
            common_educational_plurals = [
                'strategies', 'methods', 'techniques', 'approaches', 'assessments',
                'evaluations', 'tools', 'resources', 'standards', 'objectives',
                'outcomes', 'goals', 'practices', 'activities', 'exercises'
            ]
            
            # First try to find referents in previous question - more likely the focus
            for pattern in plural_patterns:
                matches = re.findall(pattern, previous_question, re.IGNORECASE)
                if matches:
                    for match in matches:
                        # If this is a tuple from a capturing group, take the first item
                        if isinstance(match, tuple):
                            match = match[0]
                        if match.lower() not in [r.lower() for r in referents]:
                            referents.append(match.lower())
            
            # Then look in previous response
            for pattern in plural_patterns:
                matches = re.findall(pattern, previous_response, re.IGNORECASE)
                if matches:
                    for match in matches:
                        # If this is a tuple from a capturing group, take the first item
                        if isinstance(match, tuple):
                            match = match[0]
                        if match.lower() not in [r.lower() for r in referents]:
                            referents.append(match.lower())
            
            # Look for specific plural keywords in both question and response
            for plural in common_educational_plurals:
                if plural in previous_question.lower() and plural not in [r.lower() for r in referents]:
                    referents.append(plural)
                elif plural in previous_response.lower() and plural not in [r.lower() for r in referents]:
                    referents.append(plural)
            
            # Extract key phrases that might be referenced
            if 'formative assessment' in previous_question.lower() or 'formative assessment' in previous_response.lower():
                if "formative assessment strategies" not in [r.lower() for r in referents]:
                    referents.append("formative assessment strategies")
                if "teachers" not in [r.lower() for r in referents]:
                    referents.append("teachers")
            elif 'assessment' in previous_question.lower() or 'assessment' in previous_response.lower():
                if "assessment methods" not in [r.lower() for r in referents]:
                    referents.append("assessment methods")
            
            # Special handling for educational professionals
            if 'teachers' in previous_question.lower() or 'teachers' in previous_response.lower():
                if "teachers" not in [r.lower() for r in referents]:
                    referents.append("teachers")
            
            # If we found referents, return them
            if referents:
                return referents
                
            # Fallback to generic educational term
            return ["educational strategies discussed"]
        
        except Exception as e:
            self.logger.warning(f"[WARNING] Error extracting referents: {str(e)}")
            return ["items mentioned"]

    def _ensure_concise_response(self, response: str, max_sentences: int = 2) -> str:
        """Ensure the response is concise by truncating if necessary"""
        try:
            # If response is already very short, return it as is
            word_count = len(response.split())
            if word_count <= 30:  # Very short responses (1-2 sentences)
                return response
                
            # Try to find a logical breakpoint for truncation
            sentences = re.split(r'(?<=[.!?])\s+', response)
            
            # Keep only the specified number of sentences for a concise response
            if len(sentences) > max_sentences:
                concise_response = ' '.join(sentences[:max_sentences])
                
                # Only add truncation note if we removed significant content
                if len(response) > len(concise_response) * 1.5:
                    concise_response += " ..."
                    
                return concise_response
            
            # If we can't split by sentences properly, truncate by word count
            if word_count > 40:  # ~2-3 sentences worth
                words = response.split()
                truncated = ' '.join(words[:40]) + "..."
                return truncated
                
            return response
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Error ensuring concise response: {str(e)}")
            # Emergency fallback - just take first 200 characters
            return response[:200] + "..." if len(response) > 200 else response
    
    def _contains_external_knowledge(self, response: str, context: str) -> bool:
        """Check if the response contains information not present in the provided context"""
        try:
            # Remove common phrases that might appear in both
            response_words = set(re.findall(r'\b\w{4,}\b', response.lower()))
            context_words = set(re.findall(r'\b\w{4,}\b', context.lower()))
            
            # Common educational terms that might appear in general knowledge
            external_knowledge_indicators = {
                "smart", "measurable", "achievable", "relevant", "time-bound",
                "think-pair-share", "cold call", "thumbs-up", "thumbs-down",
                "exit tickets", "polling software", "online quizzes"
            }
            
            # Check if response contains specific terms not in context
            response_specific = response_words - context_words
            external_terms_found = response_specific.intersection(external_knowledge_indicators)
            
            if external_terms_found:
                self.logger.warning(f"[EXTERNAL KNOWLEDGE] Found terms not in documents: {external_terms_found}")
                return True
                
            # Check for phrases that suggest general knowledge
            external_phrases = [
                "based on best practices", "research shows", "studies indicate",
                "it is recommended", "experts suggest", "common strategies include",
                "typically involves", "generally includes", "often used"
            ]
            
            for phrase in external_phrases:
                if phrase in response.lower() and phrase not in context.lower():
                    self.logger.warning(f"[EXTERNAL KNOWLEDGE] Found external phrase: {phrase}")
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Error checking for external knowledge: {str(e)}")
            return False  # If we can't check, assume it's okay
    
    def _extract_main_topic_for_followup(self, previous_response: str, previous_topic: str) -> str:
        """Extract a clear, human-friendly topic description for follow-up responses"""
        try:
            # Look for key educational concepts in the previous response
            educational_patterns = {
                'formative assessment': 'formative assessment strategies',
                'summative assessment': 'summative assessment methods', 
                'assessment': 'assessment techniques',
                'evaluation': 'evaluation methods',
                'learning objectives': 'learning objectives',
                'student performance': 'student performance evaluation',
                'feedback': 'feedback strategies',
                'grading': 'grading approaches',
                'curriculum': 'curriculum design',
                'instruction': 'instructional strategies'
            }
            
            response_lower = previous_response.lower()
            
            # Find the most relevant educational concept
            for pattern, description in educational_patterns.items():
                if pattern in response_lower:
                    return description
            
            # Fallback to previous topic if available
            if previous_topic:
                return previous_topic
                
            # Final fallback
            return "the educational topic we were discussing"
            
        except Exception:
            return "the topic we were discussing"

    def _generate_fallback_response(self, query: str, context: str, is_follow_up: bool = False, follow_up_context: Dict = None) -> str:
        """Generate clear, concise student-friendly responses as an intelligent educational assistant"""
        try:
            # Log the raw context for debugging
            self.logger.info(f"[EDUCATIONAL_ASSISTANT] Processing query with context length: {len(context)}")
            self.logger.info(f"[EDUCATIONAL_ASSISTANT] Context preview: {context[:300]}...")
            
            # Extract educational content from context with intelligent parsing
            context_lines = context.split('\n')
            content_snippets = []
            
            # Strategy 1: Extract meaningful educational content (limit for conciseness)
            for line in context_lines:
                line = line.strip()
                # Keep educational content, skip only metadata
                if (line and 
                    not line.startswith('[Source:') and 
                    not line.startswith('---') and 
                    not line.startswith('RELEVANT INFORMATION') and
                    len(line) > 15):  # Reasonable threshold for educational content
                    
                    # Clean content while preserving educational meaning
                    clean_content = re.sub(r'<[^>]+>', '', line)
                    clean_content = re.sub(r'&\w+;', ' ', clean_content)
                    clean_content = ' '.join(clean_content.split())
                    
                    # Limit content for conciseness - take only the most relevant snippets
                    if len(clean_content) > 20 and len(content_snippets) < 3:  # Reduced from 6 to 3 for shorter responses
                        content_snippets.append(clean_content)
            
            # Strategy 2: If insufficient content, extract from structured context
            if len(content_snippets) < 2:
                self.logger.info(f"[EDUCATIONAL_ASSISTANT] Applying secondary extraction strategy")
                # Remove metadata and split into meaningful segments
                clean_context = re.sub(r'\[Source:[^\]]*\]', '', context)
                clean_context = re.sub(r'---[^-]*---', '', clean_context)
                clean_context = ' '.join(clean_context.split())
                
                # Split into sentences and extract educational content
                sentences = re.split(r'[.!?]+', clean_context)
                for sentence in sentences[:8]:  # Check more sentences for educational content
                    sentence = sentence.strip()
                    if len(sentence) > 25 and len(content_snippets) < 4:  # Educational content threshold
                        content_snippets.append(sentence)
            
            # Log extracted content for debugging
            self.logger.info(f"[EDUCATIONAL_ASSISTANT] Extracted {len(content_snippets)} content segments")
            for i, snippet in enumerate(content_snippets[:3]):
                self.logger.info(f"[EDUCATIONAL_ASSISTANT] Segment {i+1}: {snippet[:100]}...")
            
            # Handle insufficient content case with human-like ChatGPT-style responses
            if not content_snippets:
                self.logger.warning(f"[EDUCATIONAL_ASSISTANT] Insufficient content for educational response")
                
                # If it's a follow-up, provide a more contextual response with conversational memory
                if is_follow_up and follow_up_context:
                    previous_topic = follow_up_context.get('previous_topic', 'that topic')
                    previous_question = follow_up_context.get('previous_question', '')
                    previous_response = follow_up_context.get('previous_response', '')
                    topic_context = self._extract_main_topic_for_followup(previous_response, previous_topic)
                    
                    # Handle specific pronoun references (what are they, etc.)
                    pronoun_references = ['they', 'them', 'these', 'those', 'that', 'this', 'it']
                    has_pronoun = any(pronoun in query_lower.split() for pronoun in pronoun_references)
                    
                    if has_pronoun and previous_question and previous_response:
                        # Extract what the pronoun might refer to from previous response
                        potential_referents = self._extract_potential_referents(previous_question, previous_response)
                        if potential_referents:
                            return f"Based on our conversation about {topic_context}, I believe you're asking about {potential_referents}. However, I don't have specific details about that in the current materials. Could you ask a more specific question about {potential_referents}?"
                    
                    if any(phrase in query_lower for phrase in ['more', 'describe more', 'tell me more', 'above topic', 'what we discussed']):
                        return f"I understand you'd like more details about {topic_context.lower()}, but I couldn't find additional specific information in the current materials. Could you ask about a particular aspect of {topic_context.lower()} that interests you?"
                    else:
                        return f"I don't have specific information about that aspect of {topic_context.lower()} in the current materials. Could you rephrase your question or ask about something else related to {topic_context.lower()}?"
                else:
                    return "I couldn't find details in the current materials. Would you like me to search further or rephrase your question?"
            
            # Generate educational response based on query type and context
            query_lower = query.lower()
            
            # Handle follow-up queries with session memory and pronoun resolution
            if is_follow_up and follow_up_context:
                previous_topic = follow_up_context.get('previous_topic', '')
                previous_response = follow_up_context.get('previous_response', '')
                self.logger.info(f"[EDUCATIONAL_ASSISTANT] Handling follow-up about: {previous_topic[:50]}...")
                
                # Resolve references like "that", "this", "it", "above topic", "what we discussed"
                if any(ref in query_lower for ref in ['that', 'this', 'it', 'those', 'these', 'above', 'what we discussed', 'what i asked', 'the topic']):
                    # Extract the main topic from previous response for context
                    topic_context = self._extract_main_topic_for_followup(previous_response, previous_topic)
                    
                    if 'more' in query_lower or 'describe more' in query_lower or 'tell me more' in query_lower:
                        # User wants more details about the previous topic
                        response = f"Here are more details about {topic_context.lower()}:\n\n{content_snippets[0]}"
                    elif 'what about' in query_lower:
                        # User asking "what about X?" - extract the X and provide info
                        response = content_snippets[0]
                    elif any(phrase in query_lower for phrase in ['above topic', 'what we discussed', 'what i asked', 'the topic']):
                        # Direct reference to previous conversation
                        response = f"Regarding {topic_context.lower()}: {content_snippets[0]}"
                    else:
                        response = f"About {topic_context.lower()}: {content_snippets[0]}"
                elif 'what about' in query_lower or 'and' in query_lower[:10]:
                    # Handle "what about math?" or "and exam dates?"
                    response = content_snippets[0]
                else:
                    response = content_snippets[0]
            else:
                # Handle new queries with appropriate educational formatting
                main_content = content_snippets[0]
                
                # Format response based on query type
                if any(phrase in query_lower for phrase in ['what is', 'what are', 'define', 'explain']):
                    response = main_content
                elif any(phrase in query_lower for phrase in ['how to', 'how can', 'steps', 'process']):
                    response = main_content
                elif any(phrase in query_lower for phrase in ['why', 'reason', 'purpose', 'importance']):
                    response = main_content
                elif any(phrase in query_lower for phrase in ['when', 'schedule', 'date', 'time']):
                    response = main_content
                else:
                    response = main_content
            
            # Add supplementary information if available and response is not too long
            if len(content_snippets) > 1 and len(response) < 200:
                additional = content_snippets[1]
                if len(additional) > 150:
                    additional = additional[:150] + "..."
                response += f"\n\n{additional}"
            
            # Ensure response is helpful and within reasonable length
            if len(response) > 400:
                response = response[:400] + "..."
            
            self.logger.info(f"[EDUCATIONAL_ASSISTANT] Generated response length: {len(response)}")
            return response
            
        except Exception as e:
            self.logger.error(f"[ERROR] Educational assistant response generation failed: {str(e)}")
            return "I encountered an issue processing your question. Please try rephrasing or ask about a different topic."
    


    def _get_display_name_from_filename(self, filename: str) -> str:
        """Extract a user-friendly display name from a filename"""
        try:
            # Remove file extension
            if '.' in filename:
                base_name = filename.rsplit('.', 1)[0]
            else:
                base_name = filename
                
            # Extract UUID from path if present
            if '/' in base_name or '\\' in base_name:
                # Get the last part of the path
                path_parts = base_name.replace('\\', '/').split('/')
                base_name = path_parts[-1]
                
                # Determine document type from path
                path_str = '/'.join(path_parts[:-1]).lower()
                if 'k12' in path_str:
                    doc_type = "K12 Document"
                elif 'preschool' in path_str:
                    doc_type = "Preschool Document"
                elif 'administrative' in path_str or 'admin' in path_str:
                    doc_type = "Administrative Document"
                elif 'edifyho' in path_str:
                    doc_type = "Educational Document"
                else:
                    doc_type = "Document"
                    
                # If it's a UUID, return a meaningful name
                if len(base_name) == 36 and base_name.count('-') == 4:
                    # Extract first 8 characters of UUID for reference
                    uuid_short = base_name[:8]
                    return f"{doc_type} {uuid_short}"
                    
            # Handle UUID-style filenames (full UUID)
            if len(base_name) == 36 and base_name.count('-') == 4:
                uuid_short = base_name[:8]
                return f"Document {uuid_short}"
                
            # Handle shortened UUID (8 characters)
            if len(base_name) == 8 and base_name.isalnum():
                return f"Document {base_name}"
                
            # Convert underscores and dashes to spaces for regular filenames
            display_name = base_name.replace('_', ' ').replace('-', ' ')
            
            # Capitalize words
            display_name = ' '.join(word.capitalize() for word in display_name.split())
            
            # Remove numbers at the start if present
            display_name = display_name.strip()
            if display_name and display_name[0].isdigit():
                # If it starts with numbers followed by period/space, remove that part
                parts = display_name.split(' ', 1)
                if len(parts) > 1 and parts[0].replace('.', '').isdigit():
                    display_name = parts[1]
                    
            return display_name or "Document"
            
        except Exception:
            return "Document"
    
    def _format_sources(self, chunks: List[Dict]) -> List[Dict]:
        """Format source information for response with download URLs and original filenames"""
        try:
            # First, try to enhance document metadata if enhanced service is available
            if self.enhanced_metadata_service:
                try:
                    self.logger.info("[METADATA] Using Enhanced Metadata service for document information")
                    
                    # Process chunks with enhanced metadata
                    enhanced_chunks = []
                    for chunk in chunks:
                        enhanced_chunk = self.enhanced_metadata_service.enhance_chunk_metadata(chunk)
                        enhanced_chunks.append(enhanced_chunk)
                    
                    # Use enhanced chunks for source formatting
                    chunks = enhanced_chunks
                    self.logger.info(f"[SUCCESS] Enhanced metadata for {len(chunks)} chunks")
                    
                except Exception as e:
                    self.logger.warning(f"[WARNING] Enhanced metadata processing failed: {str(e)}")
                    # Continue with original chunks
            
            # Extract unique filenames from chunks
            file_sources = {}
            
            for chunk in chunks:
                # Extract filename from chunk metadata
                filename = chunk.get('metadata', {}).get('filename', '')
                
                if filename:
                    # Extract UUID from filename (last part of path before extension)
                    file_uuid = None
                    if '/' in filename:
                        base_filename = filename.split('/')[-1]
                    else:
                        base_filename = filename
                    
                    # Remove extension and get UUID
                    if '.' in base_filename:
                        file_uuid = base_filename.split('.')[0]
                    else:
                        file_uuid = base_filename
                    
                    if file_uuid and file_uuid not in file_sources:
                        # Initialize source entry
                        source_entry = {
                            'filename': filename,
                            'file_uuid': file_uuid,
                            'original_filename': None,
                            'title': None,
                            'download_url': None,
                            'metadata': {},
                            'chunk_metadata': chunk.get('metadata', {})
                        }
                        
                        # Use improved metadata service for all metadata needs
                        enhanced_metadata = self.enhanced_metadata_service.enhance_chunk_metadata(chunk.get('metadata', {}))
                        
                        source_entry.update({
                            'original_filename': enhanced_metadata.get('original_filename'),
                            'title': enhanced_metadata.get('document_title'),
                            'display_name': enhanced_metadata.get('display_name'),
                            'metadata': {
                                'department': enhanced_metadata.get('department', 'Unknown'),
                                'school_types': enhanced_metadata.get('school_types', []),
                                'document_type': enhanced_metadata.get('document_type', 'unknown'),
                                'metadata_source': enhanced_metadata.get('metadata_source', 'fallback'),
                                'match_confidence': enhanced_metadata.get('match_confidence', 0.0),
                                'match_strategy': enhanced_metadata.get('match_strategy', 'unknown')
                            }
                        })
                        
                        self.logger.debug(f"[ENHANCED] Enhanced metadata for {file_uuid}: {enhanced_metadata.get('display_name')} (confidence: {enhanced_metadata.get('match_confidence', 0.0):.3f})")
                        
                        # Generate download URL using Azure blob service
                        if self.azure_service:
                            try:
                                download_url = self.azure_service.generate_download_url(filename)
                                source_entry['download_url'] = download_url
                                self.logger.debug(f"[DOWNLOAD] Generated URL for {filename}")
                            except Exception as e:
                                self.logger.warning(f"[WARNING] Failed to generate download URL for {filename}: {str(e)}")
                        
                        file_sources[file_uuid] = source_entry
            
            # Format sources for response
            formatted_sources = []
            for file_uuid, source_info in file_sources.items():
                # Use the display name from improved metadata service
                display_name = source_info.get('display_name') or source_info.get('title') or source_info.get('original_filename')
                
                # Fallback processing if no metadata available
                if not display_name:
                    filename = source_info['filename']
                    display_name = self._get_display_name_from_filename(filename)
                
                # Extract chunk metadata for additional info
                chunk_metadata = source_info.get('chunk_metadata', {})
                
                # Create source object with comprehensive information
                source = {
                    'name': display_name,
                    'filename': display_name,  # For compatibility
                    'url': source_info.get('download_url'),
                    'download_url': source_info.get('download_url'),
                    'download_available': bool(source_info.get('download_url')),
                    'file_id': file_uuid,
                    'chunk_filename': source_info['filename'],
                    'metadata': source_info.get('metadata', {}),
                    
                    # Additional metadata from chunks
                    'total_pages': chunk_metadata.get('file_pages', 0),
                    'extraction_method': chunk_metadata.get('extraction_method', 'unknown'),
                    'ocr_used': chunk_metadata.get('ocr_used', False),
                    'relevance_score': chunk_metadata.get('similarity_score', 0),
                    
                    # Enhanced metadata fields if available
                    'title': source_info.get('title', display_name),
                    'department': source_info.get('metadata', {}).get('department', 'Unknown'),
                    'sub_department': source_info.get('metadata', {}).get('sub_department', ''),
                    'document_type': source_info.get('metadata', {}).get('document_type', 'unknown'),
                    'school_types': source_info.get('metadata', {}).get('school_types', []),
                    'has_edify_metadata': bool(source_info.get('metadata'))
                }
                
                formatted_sources.append(source)
                self.logger.debug(f"[SOURCE] Formatted: {display_name} -> {source_info.get('download_url', 'No URL')}")
            
            self.logger.info(f"[SUCCESS] Formatted {len(formatted_sources)} unique sources")
            return formatted_sources
            
        except Exception as e:
            self.logger.error(f"[ERROR] Source formatting failed: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
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
                        'reasoning': getattr(self, '_last_reasoning', 'Used memory-based conversation analysis to provide contextually relevant follow-up response.'),
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
                    'reasoning': getattr(self, '_last_reasoning', 'Analyzed conversation history to generate intelligent follow-up response with contextual awareness.'),
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
            'reasoning': getattr(self, '_last_reasoning', 'Provided clarification request based on incomplete query context and conversation analysis.'),
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
            summary = "## LIST: **Conversation Summary**\n\n"
            
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
                summary += f"\n**REFRESH: Most Recent Discussion:**\n"
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
    

    def _update_conversation_memory(self, query: str, response: str, chunks: List[Dict]):
        """Update conversation memory for ChatGPT-style short-term memory"""
        try:
            if not hasattr(self, 'conversation_memory') or not self.conversation_memory:
                return
            
            # Extract topics from query
            query_topics = self._extract_topics_from_text(query.lower())
            response_topics = self._extract_topics_from_text(response.lower())
            all_topics = set(query_topics + response_topics)
            
            # Update question-answer pairs
            qa_pair = (query[:200], response[:300], len(self.conversation_memory['question_answer_pairs']))
            self.conversation_memory['question_answer_pairs'].append(qa_pair)
            
            # Update topics discussed with message indices
            current_index = len(self.conversation_memory['question_answer_pairs']) - 1
            for topic in all_topics:
                if topic not in self.conversation_memory['topics_discussed']:
                    self.conversation_memory['topics_discussed'][topic] = []
                self.conversation_memory['topics_discussed'][topic].append(current_index)
            
            # Update key concepts with message indices
            key_concepts = self._extract_key_concepts(query, response)
            for concept in key_concepts:
                if concept not in self.conversation_memory['key_concepts']:
                    self.conversation_memory['key_concepts'][concept] = []
                self.conversation_memory['key_concepts'][concept].append(current_index)
            
            # Update conversation flow
            if all_topics:
                self.conversation_memory['conversation_flow'].extend(list(all_topics))
            
            # Limit memory size (keep last 10 Q&A pairs)
            if len(self.conversation_memory['question_answer_pairs']) > 10:
                # Remove oldest Q&A pair
                self.conversation_memory['question_answer_pairs'] = self.conversation_memory['question_answer_pairs'][-10:]
                
                # Clean up topics and concepts references to removed indices
                for topic in list(self.conversation_memory['topics_discussed'].keys()):
                    self.conversation_memory['topics_discussed'][topic] = [
                        idx for idx in self.conversation_memory['topics_discussed'][topic] 
                        if idx >= len(self.conversation_memory['question_answer_pairs']) - 10
                    ]
                    if not self.conversation_memory['topics_discussed'][topic]:
                        del self.conversation_memory['topics_discussed'][topic]
                
                for concept in list(self.conversation_memory['key_concepts'].keys()):
                    self.conversation_memory['key_concepts'][concept] = [
                        idx for idx in self.conversation_memory['key_concepts'][concept] 
                        if idx >= len(self.conversation_memory['question_answer_pairs']) - 10
                    ]
                    if not self.conversation_memory['key_concepts'][concept]:
                        del self.conversation_memory['key_concepts'][concept]
            
            # Limit conversation flow (keep last 20 entries)
            if len(self.conversation_memory['conversation_flow']) > 20:
                self.conversation_memory['conversation_flow'] = self.conversation_memory['conversation_flow'][-20:]
            
            self.logger.info(f"[MEMORY] Updated memory: {len(self.conversation_memory['question_answer_pairs'])} Q&A pairs, "
                           f"{len(self.conversation_memory['topics_discussed'])} topics, "
                           f"{len(self.conversation_memory['key_concepts'])} concepts")
                
        except Exception as e:
            self.logger.warning(f"[WARNING] Failed to update conversation memory: {str(e)}")

    def _preprocess_query_for_retrieval(self, query: str) -> str:
        """Enhanced query preprocessing for better retrieval from Streamlit version"""
        try:
            # Clean and normalize query
            processed_query = query.strip().lower()
            
            # Remove common question patterns to extract core terms
            question_patterns = [
                r'^what\s+(is|are|do|does|can)\s+',
                r'^how\s+(do|does|can|to)\s+',
                r'^tell\s+me\s+about\s+',
                r'^explain\s+',
                r'^describe\s+',
                r'^define\s+',
                r'^what\s+type\s+of\s+',
                r'^what\s+types\s+of\s+',
                r'^different\s+types\s+of\s+',
                r'^list\s+of\s+',
                r'\?$'  # Remove question marks
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
                processed_query = re.sub(rf'\b{typo}\b', correct, processed_query, flags=re.IGNORECASE)
            
            # Expand abbreviations and common terms
            abbreviations = {
                'AI': 'artificial intelligence',
                'ML': 'machine learning',
                'NLP': 'natural language processing',
                'API': 'application programming interface'
            }
            
            for abbrev, full_form in abbreviations.items():
                processed_query = re.sub(rf'\b{abbrev}\b', full_form, processed_query, flags=re.IGNORECASE)
            
            # Add educational context for better matching
            if 'formative' in processed_query and 'assessment' in processed_query:
                processed_query += ' ongoing assessment assessment for learning continuous evaluation'
            elif 'summative' in processed_query and 'assessment' in processed_query:
                processed_query += ' final assessment assessment of learning end evaluation'
            elif 'assessment' in processed_query:
                processed_query += ' evaluation testing grading'
            elif 'evaluation' in processed_query:
                processed_query += ' assessment testing'
            
            return processed_query.strip()
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Query preprocessing failed: {str(e)}")
            return query

    def _extract_core_keywords(self, query: str) -> List[str]:
        """Extract core keywords from query for fallback search"""
        try:
            # Remove stop words and extract meaningful terms
            words = re.findall(r'\b\w{3,}\b', query.lower())
            
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

    def _enhance_retrieval_results(self, chunks: List[Dict], query: str) -> List[Dict]:
        """Enhance retrieval results with additional context"""
        try:
            enhanced_chunks = []
            
            for chunk in chunks:
                # Add relevance score calculation
                relevance_score = self._calculate_relevance_score(chunk, query)
                chunk['relevance_score'] = relevance_score
                
                # Add source attribution
                metadata = chunk.get('metadata', {})
                chunk['source_info'] = {
                    'source_file': metadata.get('filename', 'unknown'),
                    'chunk_location': f"Chunk {int(metadata.get('chunk_index', 0)) + 1}",
                    'content_type': metadata.get('content_type', 'general')
                }
                
                enhanced_chunks.append(chunk)
            
            # Sort by relevance score
            enhanced_chunks.sort(key=lambda x: x.get('relevance_score', x.get('similarity_score', 0)), reverse=True)
            
            return enhanced_chunks
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Result enhancement failed: {str(e)}")
            return chunks

    def _calculate_relevance_score(self, chunk: Dict, query: str) -> float:
        """Calculate relevance score for a chunk"""
        try:
            base_score = chunk.get('similarity_score', 0.0)
            
            # Bonus for exact keyword matches
            chunk_text = chunk.get('text', '').lower()
            query_words = set(query.lower().split())
            chunk_words = set(chunk_text.split())
            
            keyword_match_ratio = len(query_words.intersection(chunk_words)) / max(len(query_words), 1)
            keyword_bonus = keyword_match_ratio * 0.1
            
            # Bonus for educational terms
            educational_terms = ['assessment', 'formative', 'summative', 'evaluation', 'learning', 'teaching', 'student']
            edu_matches = sum(1 for term in educational_terms if term in chunk_text)
            edu_bonus = min(edu_matches * 0.05, 0.15)
            
            return min(base_score + keyword_bonus + edu_bonus, 1.0)
            
        except Exception:
            return chunk.get('similarity_score', 0.0)
    
    def _extract_key_concepts(self, query: str, response: str) -> List[str]:
        """Extract key educational concepts from query and response"""
        try:
            concepts = set()
            text = f"{query} {response}".lower()
            
            # Educational concept patterns
            concept_patterns = [
                r'\b(?:theorem|formula|equation|principle|law|rule|method|process|technique|concept|theory|model|algorithm|procedure)\b',
                r'\b(?:definition|meaning|explanation|example|solution|proof|derivation|analysis|calculation|application)\b',
                r'\b(?:chapter|lesson|topic|subject|course|grade|level|standard|curriculum|syllabus)\b',
                r'\b(?:mathematics|science|physics|chemistry|biology|history|geography|literature|english|language)\b'
            ]
            
            for pattern in concept_patterns:
                matches = re.findall(pattern, text)
                concepts.update(matches)
            
            # Extract key nouns (educational terms)
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text)
            educational_words = [word for word in words if any(term in word.lower() for term in 
                               ['study', 'learn', 'teach', 'school', 'class', 'test', 'exam', 'quiz', 'homework', 'assignment'])]
            concepts.update(educational_words[:5])  # Top 5
            
            return list(concepts)[:10]  # Limit to 10 concepts
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Failed to extract key concepts: {str(e)}")
            return []
    
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
    
    def _calculate_confidence(self, chunks: List[Dict]) -> float:
        """Calculate confidence score based on retrieved chunks quality"""
        try:
            if not chunks:
                return 0.0
            
            # Base confidence on number and quality of chunks
            base_confidence = min(len(chunks) / 3.0, 1.0)  # Max confidence with 3+ chunks
            
            # Adjust based on similarity scores if available
            similarity_scores = []
            for chunk in chunks:
                if 'similarity_score' in chunk:
                    similarity_scores.append(chunk['similarity_score'])
                elif 'score' in chunk:
                    similarity_scores.append(chunk['score'])
            
            if similarity_scores:
                avg_similarity = sum(similarity_scores) / len(similarity_scores)
                confidence = base_confidence * avg_similarity
            else:
                confidence = base_confidence * 0.8  # Default adjustment
            
            return round(min(confidence, 1.0), 2)
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Failed to calculate confidence: {str(e)}")
            return 0.75  # Default confidence
    
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

    def _extract_key_concepts(self, question: str, response: str = "") -> List[str]:
        """Extract key concepts from text for memory indexing"""
        try:
            combined_text = f"{question} {response}".lower()
            
            # Educational concepts to look for
            concepts = []
            educational_keywords = [
                'assessment', 'evaluation', 'formative', 'summative', 'learning', 'teaching',
                'education', 'student', 'grading', 'testing', 'feedback', 'performance',
                'curriculum', 'instruction', 'pedagogy', 'discipline', 'policy', 'observation',
                'behavior', 'schedule', 'academic', 'examination', 'holiday'
            ]
            
            for keyword in educational_keywords:
                if keyword in combined_text:
                    concepts.append(keyword)
            
            return concepts[:5]  # Return top 5 concepts
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Key concept extraction failed: {str(e)}")
            return []
    
    def _get_conversation_context(self, query: str, is_follow_up: bool = False) -> str:
        """Get conversation context for enhanced query processing"""
        try:
            if not is_follow_up or not self.conversation_memory.get('question_answer_pairs'):
                return ""
            
            # Get recent Q&A pairs for context
            recent_pairs = self.conversation_memory['question_answer_pairs'][-3:]  # Last 3 exchanges
            context_parts = []
            
            for pair in recent_pairs:
                context_parts.append(f"Q: {pair['question']}")
                context_parts.append(f"A: {pair['answer'][:100]}...")  # Truncate for brevity
            
            return " ".join(context_parts)
            
        except Exception as e:
            self.logger.warning(f"[WARNING] Conversation context extraction failed: {str(e)}")
            return ""

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
            'max_context_chunks': 6,  # Increased for better context (was 4)
            'min_similarity_threshold': 0.25,  # Lowered for better recall (was 0.35)
            'enable_citations': True,
            'enable_context_expansion': True,
            'max_context_length': 5000,  # Increased for comprehensive responses (was 4000)
            'max_response_tokens': 1200,  # Increased for detailed responses (was 1000)
            'temperature': 0.2,  # Lowered for more focused responses (was 0.7)
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
                            print(f"     RECEIVE: Download available{size_info}")
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
