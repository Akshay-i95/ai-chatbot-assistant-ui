import React, { useState, useRef } from 'react';
import { apiService } from '../lib/api';
import { Button } from './ui/button';
import { Upload, File, CheckCircle, AlertCircle } from 'lucide-react';

interface FileUploadProps {
  onUploadComplete?: () => void;
}

export function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{
    type: 'success' | 'error' | null;
    message: string;
  }>({ type: null, message: '' });
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file.type.includes('pdf')) {
      setUploadStatus({
        type: 'error',
        message: 'Only PDF files are supported'
      });
      return;
    }

    setIsUploading(true);
    setUploadStatus({ type: null, message: '' });

    try {
      const result = await apiService.uploadFile(file);
      setUploadStatus({
        type: 'success',
        message: `File "${file.name}" uploaded successfully`
      });
      
      if (onUploadComplete) {
        onUploadComplete();
      }
    } catch (error) {
      setUploadStatus({
        type: 'error',
        message: error instanceof Error ? error.message : 'Upload failed'
      });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2">Upload Documents</h2>
        <p className="text-muted-foreground">
          Upload PDF files to enhance the AI's knowledge base. The system will process 
          and index your documents for better contextual responses.
        </p>
      </div>

      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-primary bg-primary/5'
            : 'border-border hover:border-primary/50'
        } ${isUploading ? 'pointer-events-none opacity-50' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="flex flex-col items-center gap-4">
          <div className="p-4 rounded-full bg-muted">
            {isUploading ? (
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            ) : (
              <Upload size={32} className="text-muted-foreground" />
            )}
          </div>
          
          <div>
            <h3 className="text-lg font-semibold mb-2">
              {isUploading ? 'Uploading...' : 'Drop your PDF files here'}
            </h3>
            <p className="text-muted-foreground mb-4">
              or click to browse and select files
            </p>
            
            <Button 
              onClick={openFileDialog}
              disabled={isUploading}
              variant="outline"
            >
              <File size={16} className="mr-2" />
              Choose Files
            </Button>
          </div>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Status Messages */}
      {uploadStatus.type && (
        <div className={`mt-4 p-4 rounded-lg flex items-center gap-3 ${
          uploadStatus.type === 'success' 
            ? 'bg-green-50 text-green-800 border border-green-200' 
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {uploadStatus.type === 'success' ? (
            <CheckCircle size={20} />
          ) : (
            <AlertCircle size={20} />
          )}
          <span>{uploadStatus.message}</span>
        </div>
      )}

      {/* Upload Guidelines */}
      <div className="mt-8 p-4 bg-muted rounded-lg">
        <h4 className="font-semibold mb-2">Upload Guidelines</h4>
        <ul className="text-sm text-muted-foreground space-y-1">
          <li>• Only PDF files are supported</li>
          <li>• Maximum file size: 16MB</li>
          <li>• Files will be processed and indexed automatically</li>
          <li>• Processing may take a few moments for large documents</li>
        </ul>
      </div>
    </div>
  );
}
