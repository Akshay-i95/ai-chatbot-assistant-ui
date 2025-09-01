import React, { useState, useEffect } from 'react';
import { ExternalLinkIcon, FileIcon, BookIcon, CheckIcon } from 'lucide-react';
import { useSources } from '@/hooks/use-sources';

interface SourceDisplayProps {
  showTitle?: boolean;
  compact?: boolean;
  maxSources?: number;
}

export const SourceDisplay: React.FC<SourceDisplayProps> = ({
  showTitle = true,
  compact = false,
  maxSources = 10
}) => {
  const { sources } = useSources();
  const [downloadStatus, setDownloadStatus] = useState<Record<string, string>>({});
  const [backendUrl, setBackendUrl] = useState<string>('http://localhost:5000');

  // Set backend URL from environment or window global
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setBackendUrl(window.BACKEND_URL || 'http://localhost:5000');
    }
  }, []);

  // No sources, don't render
  if (!sources || sources.length === 0) {
    return null;
  }
  
  // Limit number of sources to display
  const displaySources = sources.slice(0, maxSources);

  const handleDownload = async (e: React.MouseEvent, source: any) => {
    e.preventDefault();
    
    // Check if download is available
    if (source.download_available === false) {
      alert('This document is not available for download.');
      return;
    }
    
    try {
      setDownloadStatus(prev => ({ ...prev, [source.filename]: 'downloading' }));
      
      // Get download URL (either directly or from backend)
      let downloadUrl = source.download_url;
      
      // If URL doesn't start with http, use the backend API endpoint
      if (!downloadUrl || !downloadUrl.startsWith('http')) {
        downloadUrl = `${backendUrl}/api/files/download/${encodeURIComponent(source.filename || '')}`;
      }
      
      console.log('📥 Attempting to download:', downloadUrl);
      
      // Try fetching the file first to check if it exists
      const response = await fetch(downloadUrl, {
        method: 'HEAD', // Just check if file exists
      });
      
      if (!response.ok) {
        throw new Error(`File not available (${response.status})`);
      }
      
      // Create a temporary link and trigger download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.download = source.filename || 'document.pdf'; // Force download with filename
      
      // Add to DOM, click, then remove
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Mark as completed after a short delay
      setTimeout(() => {
        setDownloadStatus(prev => ({ ...prev, [source.filename]: 'downloaded' }));
        
        // Reset status after showing success
        setTimeout(() => {
          setDownloadStatus(prev => ({ ...prev, [source.filename]: '' }));
        }, 2000);
      }, 1000);
      
    } catch (error) {
      console.error('📥 Download error:', error);
      setDownloadStatus(prev => ({ ...prev, [source.filename]: 'error' }));
      
      // Show user-friendly error message
      const errorMessage = error instanceof Error ? error.message : 'Download failed';
      alert(`Failed to download document: ${errorMessage}`);
      
      // Reset error status after a delay
      setTimeout(() => {
        setDownloadStatus(prev => ({ ...prev, [source.filename]: '' }));
      }, 3000);
    }
  };

  return (
    <div className={`${compact ? 'mt-2' : 'mt-4'} pt-3 border-t border-gray-200 dark:border-gray-700 animate-in fade-in duration-300`}>
      <div className="flex flex-col gap-2">
        {showTitle && (
          <p className="text-xs text-gray-500 dark:text-gray-400 font-medium flex items-center gap-1.5">
            <BookIcon className="size-3.5" />
            Sources
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          {displaySources.map((source, index) => {
            // Ensure download URL is properly formatted
            let downloadUrl = source.download_url;
            
            // If URL doesn't start with http, use the backend API endpoint
            if (!downloadUrl || !downloadUrl.startsWith('http')) {
              downloadUrl = `${backendUrl}/api/files/download/${encodeURIComponent(source.filename || '')}`;
            }
            
            return (
              <a 
                key={index}
                href={downloadUrl}
                className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md ${
                  source.download_available !== false
                    ? 'bg-gray-50 hover:bg-gray-100 dark:bg-gray-800/50 dark:hover:bg-gray-800/80 cursor-pointer' 
                    : 'bg-gray-50/50 dark:bg-gray-800/30 cursor-not-allowed'
                } text-gray-600 dark:text-gray-300 transition-colors border border-gray-200 dark:border-gray-700`}
                onClick={(e) => handleDownload(e, source)}
                title={`${source.title || source.filename}${source.department ? ` - ${source.department}` : ''}${source.sub_department ? ` / ${source.sub_department}` : ''}`}
              >
                {downloadStatus[source.filename] === 'downloading' ? (
                  <span className="size-3.5 flex items-center justify-center animate-spin">
                    <svg className="size-full text-blue-500" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                  </span>
                ) : downloadStatus[source.filename] === 'downloaded' ? (
                  <CheckIcon className="size-3.5 text-green-500" />
                ) : downloadStatus[source.filename] === 'error' ? (
                  <svg className="size-3.5 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                  </svg>
                ) : (
                  <FileIcon className="size-3.5 text-red-500" />
                )}
                <span className="truncate max-w-[180px]">
                  {source.title || source.filename || 'Unknown Document'}
                </span>
                {source.download_available !== false && !downloadStatus[source.filename] && (
                  <ExternalLinkIcon className="size-3 text-gray-400" />
                )}
              </a>
            );
          })}
        </div>
        
        {/* Show total count if there are more sources than displayed */}
        {sources.length > maxSources && (
          <div className="text-xs text-gray-400 mt-1">
            +{sources.length - maxSources} more sources available
          </div>
        )}
        
        {/* Show metadata if available */}
        {sources.some(s => s.has_edify_metadata) && (
          <div className="text-xs text-gray-400 mt-1">
            Documents from Edify School System
          </div>
        )}
      </div>
    </div>
  );
};

export default SourceDisplay;
