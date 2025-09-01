"""
Lightweight Educational Assistant - No Vector DB Version
Uses Edify API for document search instead of local vector database
"""

import os
import logging
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# Import services
from llm_service import LLMService
from edify_api_service import EdifyAPIService
from azure_blob_service import create_azure_download_service

class LightweightChatbot:
    """Lightweight chatbot that uses Edify API instead of local vector DB"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.llm_service = LLMService(config)
        
        # Initialize Edify API service
        self.edify_service = EdifyAPIService(config) if config.get('edify_api_url') else None
        
        # Initialize Azure service for file downloads
        self.azure_service = create_azure_download_service(config) if config.get('azure_storage_connection_string') else None
        
        logging.info("✅ Lightweight chatbot initialized successfully")
    
    def get_relevant_context(self, query: str, top_k: int = 3) -> List[Dict]:
        """Get relevant context using Edify API instead of vector search"""
        try:
            if not self.edify_service:
                logging.warning("Edify API not configured, returning empty context")
                return []
            
            # Use Edify API to search for relevant documents
            results = self.edify_service.search_documents(query, top_k=top_k)
            
            # Convert Edify results to chatbot format
            context_chunks = []
            for result in results:
                chunk = {
                    'content': result.get('content', ''),
                    'metadata': {
                        'filename': result.get('filename', ''),
                        'source': result.get('source', 'Edify API'),
                        'relevance_score': result.get('score', 0.0),
                        'chunk_id': result.get('id', ''),
                        'download_url': self._get_download_url(result.get('filename'))
                    }
                }
                context_chunks.append(chunk)
            
            logging.info(f"Retrieved {len(context_chunks)} context chunks from Edify API")
            return context_chunks
            
        except Exception as e:
            logging.error(f"Error getting context from Edify API: {e}")
            return []
    
    def _get_download_url(self, filename: str) -> str:
        """Generate download URL for a file"""
        if not filename:
            return ""
        
        try:
            if self.azure_service:
                return self.azure_service.get_download_url(filename)
            else:
                # Fallback to local file endpoint
                return f"/api/files/download/{filename}"
        except Exception as e:
            logging.error(f"Error generating download URL for {filename}: {e}")
            return ""
    
    def process_message(self, message: str, conversation_history: List[Dict] = None) -> Dict:
        """Process a user message and return AI response"""
        try:
            # Get relevant context
            context_chunks = self.get_relevant_context(message)
            
            # Prepare context for LLM
            context_text = ""
            sources = []
            
            for chunk in context_chunks:
                context_text += f"\n\nDocument: {chunk['metadata'].get('filename', 'Unknown')}\n"
                context_text += chunk['content']
                
                # Prepare source metadata
                source = {
                    'filename': chunk['metadata'].get('filename', ''),
                    'title': chunk['metadata'].get('filename', '').replace('.pdf', ''),
                    'download_url': chunk['metadata'].get('download_url', ''),
                    'excerpt': chunk['content'][:200] + "..." if len(chunk['content']) > 200 else chunk['content']
                }
                sources.append(source)
            
            # Generate AI response using LLM service
            response_data = self.llm_service.generate_response(
                message=message,
                context=context_text,
                conversation_history=conversation_history or []
            )
            
            # Add sources to response
            response_data['sources'] = sources
            response_data['context_used'] = len(context_chunks)
            
            return response_data
            
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            return {
                'content': "I apologize, but I encountered an error processing your request. Please try again.",
                'sources': [],
                'reasoning': f"Error: {str(e)}",
                'context_used': 0
            }


def create_lightweight_app():
    """Create Flask app with lightweight chatbot"""
    app = Flask(__name__)
    CORS(app)
    
    # Configuration
    config = {
        'groq_api_key': os.getenv('GROQ_API_KEY'),
        'groq_model': 'groq/mixtral-8x7b-32768',
        'edify_api_url': os.getenv('EDIFY_API_URL'),
        'edify_api_key': os.getenv('EDIFY_API_KEY'),
        'azure_storage_connection_string': os.getenv('AZURE_STORAGE_CONNECTION_STRING'),
        'azure_container_name': os.getenv('AZURE_CONTAINER_NAME', 'documents')
    }
    
    # Initialize chatbot
    chatbot = LightweightChatbot(config)
    
    @app.route('/api/chat', methods=['POST'])
    def chat():
        try:
            data = request.get_json()
            message = data.get('message', '')
            conversation_history = data.get('conversation_history', [])
            
            if not message.strip():
                return jsonify({'error': 'Empty message'}), 400
            
            # Process message
            response = chatbot.process_message(message, conversation_history)
            
            return jsonify({
                'ai_message': {
                    'content': response['content'],
                    'reasoning': response.get('reasoning', ''),
                    'metadata': {
                        'sources': response.get('sources', []),
                        'context_used': response.get('context_used', 0),
                        'confidence': response.get('confidence', 0.8)
                    }
                }
            })
            
        except Exception as e:
            logging.error(f"Chat API error: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({'status': 'healthy', 'version': 'lightweight'})
    
    return app

if __name__ == '__main__':
    app = create_lightweight_app()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
