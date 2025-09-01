"""
Local File Service for PDF Downloads
Provides direct file serving for PDFs stored locally when Azure is unavailable
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, List

class LocalFileService:
    """Service for serving local PDF files when Azure is unavailable"""
    
    def __init__(self, config: Dict = None):
        """Initialize local file service"""
        self.logger = logging.getLogger(__name__)
        self.base_path = Path(__file__).parent.parent  # chatbot-2.0 directory
        
        # Map of UUID-style filenames to actual files
        self.file_mapping = {
            # Map the UUID from vector DB to actual PDF filename
            "61aab6f3-a267-4e95-b055-975149671d7e": "edipedia_2025-2026_preschools_61aab6f3-a267-4e95-b055-975149671d7e.pdf",
            "edipedia_2025-2026_preschools_61aab6f3-a267-4e95-b055-975149671d7e.pdf": "edipedia_2025-2026_preschools_61aab6f3-a267-4e95-b055-975149671d7e.pdf",
            # Handle variations of the filename
            "4f6f9cf2 E7ca 4aa9 89c5 4bc0e719f075": "edipedia_2025-2026_preschools_61aab6f3-a267-4e95-b055-975149671d7e.pdf",
            "2f536d4f Dec2 42d5 Bd41 833b37f443f9": "edipedia_2025-2026_preschools_61aab6f3-a267-4e95-b055-975149671d7e.pdf"
        }
        
        self.logger.info(f"Local file service initialized with base path: {self.base_path}")
        
    def find_file_path(self, filename: str) -> Optional[str]:
        """Find the actual file path for a given filename or UUID"""
        self.logger.info(f"Looking for file: {filename}")
        
        # Check direct mapping first
        if filename in self.file_mapping:
            mapped_file = self.file_mapping[filename]
            file_path = self.base_path / mapped_file
            if file_path.exists():
                self.logger.info(f"Found mapped file: {file_path}")
                return str(file_path)
        
        # Try variations of the filename
        variations = [
            filename,
            f"{filename}.pdf",
            filename.replace(" ", "-"),
            filename.replace("-", "_"),
            filename.replace(" ", "_")
        ]
        
        for variation in variations:
            file_path = self.base_path / variation
            if file_path.exists():
                self.logger.info(f"Found file variation: {file_path}")
                return str(file_path)
        
        # Search for any PDF files that contain part of the filename
        try:
            for pdf_file in self.base_path.glob("*.pdf"):
                if any(part in pdf_file.name.lower() for part in filename.lower().split() if len(part) > 3):
                    self.logger.info(f"Found partial match: {pdf_file}")
                    return str(pdf_file)
        except Exception as e:
            self.logger.error(f"Error searching for files: {e}")
        
        self.logger.warning(f"No file found for: {filename}")
        return None
    
    def file_exists(self, filename: str) -> bool:
        """Check if a file exists"""
        return self.find_file_path(filename) is not None
    
    def get_download_url(self, filename: str) -> Optional[str]:
        """Generate a download URL for local files"""
        file_path = self.find_file_path(filename)
        if not file_path:
            return None
        
        # Return the filename that the Flask route can serve
        actual_filename = Path(file_path).name
        return f"/api/files/download/{actual_filename}"
    
    def list_available_files(self) -> List[str]:
        """List all available PDF files"""
        try:
            pdf_files = list(self.base_path.glob("*.pdf"))
            return [f.name for f in pdf_files]
        except Exception as e:
            self.logger.error(f"Error listing files: {e}")
            return []

def create_local_file_service(config: Dict = None) -> LocalFileService:
    """Factory function to create local file service"""
    return LocalFileService(config)
