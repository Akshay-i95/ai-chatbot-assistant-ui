"""
Edify API Service for Document Metadata
Provides mapping between chunk filenames and original document names
"""

import os
import logging
import requests
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

class EdifyAPIService:
    """Service for fetching document metadata from Edify API"""
    
    def __init__(self, config: Dict):
        """Initialize Edify API service with configuration"""
        self.logger = logging.getLogger(__name__)
        
        # Load Edify API configuration
        self.api_key = config.get('edify_api_key', os.getenv('EDIFY_API_KEY'))
        self.api_base_url = config.get('edify_api_base_url', os.getenv('EDIFY_API_BASE_URL', 'https://api.edifyschool.in/v1'))
        self.api_endpoint = config.get('edify_api_endpoint', os.getenv('EDIFY_API_ENDPOINT', '/edi-pedia/sop-all'))
        self.api_timeout = int(config.get('edify_api_timeout', os.getenv('EDIFY_API_TIMEOUT', '30')))
        
        # Document metadata cache
        self.document_cache = {}
        self.uuid_to_filename_map = {}
        self.filename_to_metadata_map = {}
        self.cache_timestamp = None
        self.cache_duration_hours = 24  # Cache for 24 hours
        
        # Initialize document metadata
        self._initialize_metadata()
        
        self.logger.info("✅ Edify API service initialized successfully")
    
    def _initialize_metadata(self):
        """Initialize document metadata from Edify API"""
        try:
            if self._is_cache_valid():
                self.logger.info("📋 Using cached document metadata")
                return
            
            self.logger.info("🔄 Fetching document metadata from Edify API...")
            documents = self._fetch_all_documents()
            
            if documents:
                self._build_metadata_maps(documents)
                self.cache_timestamp = datetime.now()
                self.logger.info(f"✅ Document metadata initialized: {len(self.document_cache)} documents")
            else:
                self.logger.warning("⚠️ No documents fetched from Edify API")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize document metadata: {str(e)}")
    
    def _is_cache_valid(self) -> bool:
        """Check if the current cache is still valid"""
        if not self.cache_timestamp or not self.document_cache:
            return False
        
        cache_age = datetime.now() - self.cache_timestamp
        return cache_age < timedelta(hours=self.cache_duration_hours)
    
    def _fetch_all_documents(self) -> List[Dict]:
        """Fetch all documents from Edify API with pagination"""
        try:
            all_documents = []
            page_index = 0
            page_size = 100
            
            headers = {'Content-Type': 'application/json'}
            if self.api_key and self.api_key != 'no_auth_required':
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            while True:
                url = f"{self.api_base_url}{self.api_endpoint}"
                params = {
                    'PageIndex': page_index,
                    'PageSize': page_size
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=self.api_timeout)
                
                if response.status_code != 200:
                    self.logger.error(f"❌ API request failed: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                
                # Handle different response formats
                if isinstance(data, list):
                    documents = data
                else:
                    documents = data.get('data', data.get('items', data.get('response', {}).get('items', [])))
                
                if not documents:
                    break
                
                all_documents.extend(documents)
                
                # Check if we've fetched all documents
                if len(documents) < page_size:
                    break
                
                page_index += 1
                
                # Safety check to prevent infinite loops
                if page_index > 100:  # Max 10,000 documents
                    self.logger.warning("⚠️ Reached maximum page limit, stopping fetch")
                    break
            
            self.logger.info(f"📄 Fetched {len(all_documents)} documents from Edify API")
            return all_documents
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching documents: {str(e)}")
            return []
    
    def _build_metadata_maps(self, documents: List[Dict]):
        """Build metadata mapping from documents"""
        try:
            for doc in documents:
                doc_id = doc.get('id')
                sop_file = doc.get('sopFile', {})
                filename = sop_file.get('name', '') if isinstance(sop_file, dict) else str(sop_file)
                
                if not doc_id or not filename:
                    continue
                
                # Store full document metadata
                self.document_cache[doc_id] = {
                    'id': doc_id,
                    'title': doc.get('sopTitle', ''),
                    'original_filename': filename,
                    'department': doc.get('departmentName', ''),
                    'sub_department': doc.get('subDepartmentName', ''),
                    'document_type': doc.get('documentType', ''),
                    'school_types': doc.get('schoolTypeNames', []),
                    'is_approved': doc.get('isApproved', False),
                    'modified_on': doc.get('modifiedOn', ''),
                    'created_on': doc.get('createdOn', ''),
                    'description': doc.get('description', ''),
                    'file_url': sop_file.get('url', '') if isinstance(sop_file, dict) else ''
                }
                
                # Build UUID to filename mapping (for chunk filenames like "uuid.pdf")
                self.uuid_to_filename_map[f"{doc_id}.pdf"] = filename
                self.uuid_to_filename_map[doc_id] = filename
                
                # Build filename to metadata mapping
                self.filename_to_metadata_map[filename] = self.document_cache[doc_id]
                self.filename_to_metadata_map[f"{doc_id}.pdf"] = self.document_cache[doc_id]
            
            self.logger.info(f"📋 Built metadata maps: {len(self.document_cache)} documents")
            
        except Exception as e:
            self.logger.error(f"❌ Error building metadata maps: {str(e)}")
    
    def get_original_filename(self, chunk_filename: str) -> Optional[str]:
        """Get original filename from chunk filename (UUID-based)"""
        try:
            # Refresh cache if needed
            if not self._is_cache_valid():
                self._initialize_metadata()
            
            # Check direct mapping first
            if chunk_filename in self.uuid_to_filename_map:
                return self.uuid_to_filename_map[chunk_filename]
            
            # Extract UUID from filename if it's in UUID format
            uuid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', chunk_filename.lower())
            if uuid_match:
                uuid_str = uuid_match.group(1)
                if uuid_str in self.uuid_to_filename_map:
                    return self.uuid_to_filename_map[uuid_str]
                if f"{uuid_str}.pdf" in self.uuid_to_filename_map:
                    return self.uuid_to_filename_map[f"{uuid_str}.pdf"]
            
            # If no mapping found, return the original filename
            return chunk_filename
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting original filename for {chunk_filename}: {str(e)}")
            return chunk_filename
    
    def get_document_metadata(self, filename: str) -> Optional[Dict]:
        """Get full document metadata by filename"""
        try:
            # Refresh cache if needed
            if not self._is_cache_valid():
                self._initialize_metadata()
            
            # Check direct mapping
            if filename in self.filename_to_metadata_map:
                return self.filename_to_metadata_map[filename]
            
            # Extract UUID and try again
            uuid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', filename.lower())
            if uuid_match:
                uuid_str = uuid_match.group(1)
                if uuid_str in self.document_cache:
                    return self.document_cache[uuid_str]
            
            return None
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting document metadata for {filename}: {str(e)}")
            return None
    
    def get_document_download_info(self, chunk_filename: str) -> Dict:
        """Get comprehensive download info for a document"""
        try:
            metadata = self.get_document_metadata(chunk_filename)
            original_filename = self.get_original_filename(chunk_filename)
            
            if metadata:
                return {
                    'original_filename': original_filename,
                    'display_title': metadata.get('title', original_filename),
                    'department': metadata.get('department', ''),
                    'sub_department': metadata.get('sub_department', ''),
                    'document_type': metadata.get('document_type', ''),
                    'school_types': metadata.get('school_types', []),
                    'file_url': metadata.get('file_url', ''),
                    'has_metadata': True
                }
            else:
                return {
                    'original_filename': original_filename or chunk_filename,
                    'display_title': original_filename or chunk_filename,
                    'department': 'Unknown',
                    'sub_department': 'Unknown',
                    'document_type': 'unknown',
                    'school_types': [],
                    'file_url': '',
                    'has_metadata': False
                }
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting download info for {chunk_filename}: {str(e)}")
            return {
                'original_filename': chunk_filename,
                'display_title': chunk_filename,
                'department': 'Unknown',
                'sub_department': 'Unknown',
                'document_type': 'unknown',
                'school_types': [],
                'file_url': '',
                'has_metadata': False
            }
    
    def refresh_cache(self):
        """Manually refresh the document metadata cache"""
        try:
            self.logger.info("🔄 Manually refreshing document metadata cache...")
            self.cache_timestamp = None  # Force refresh
            self._initialize_metadata()
            
        except Exception as e:
            self.logger.error(f"❌ Error refreshing cache: {str(e)}")
    
    def get_cache_info(self) -> Dict:
        """Get information about the current cache state"""
        cache_age = None
        if self.cache_timestamp:
            cache_age = (datetime.now() - self.cache_timestamp).total_seconds() / 3600  # Hours
        
        return {
            'documents_cached': len(self.document_cache),
            'cache_age_hours': cache_age,
            'cache_valid': self._is_cache_valid(),
            'last_updated': self.cache_timestamp.isoformat() if self.cache_timestamp else None
        }


def create_edify_api_service(config: Dict) -> Optional[EdifyAPIService]:
    """Factory function to create an instance of EdifyAPIService"""
    try:
        return EdifyAPIService(config)
    except Exception as e:
        logging.error(f"❌ Failed to create EdifyAPIService: {str(e)}")
        return None
