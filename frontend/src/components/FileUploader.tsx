import React, { useCallback, useState } from 'react';
import { Upload, FileText, X, Loader2 } from 'lucide-react';
import { documentApi } from '../lib/api';

interface FileUploaderProps {
  onUploadComplete: () => void;
}

export default function FileUploader({ onUploadComplete }: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const allowedTypes = ['.pdf', '.docx', '.txt'];

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) validateAndSetFile(file);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) validateAndSetFile(file);
  };

  const validateAndSetFile = (file: File) => {
    setError(null);
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowedTypes.includes(ext)) {
      setError(`Unsupported file type. Allowed: ${allowedTypes.join(', ')}`);
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError('File too large. Maximum size is 50 MB.');
      return;
    }
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);

    try {
      await documentApi.upload(selectedFile);
      setSelectedFile(null);
      onUploadComplete();
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
          isDragging
            ? 'border-indigo-400 bg-indigo-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-600 mb-2">
          Drag and drop your document here, or{' '}
          <label className="text-indigo-600 font-medium cursor-pointer hover:text-indigo-700">
            browse
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={handleFileSelect}
              className="hidden"
            />
          </label>
        </p>
        <p className="text-xs text-gray-400">PDF, DOCX, or TXT up to 50 MB</p>
      </div>

      {/* Selected file */}
      {selectedFile && (
        <div className="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-4 py-3">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-indigo-500" />
            <div>
              <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
              <p className="text-xs text-gray-500">{formatFileSize(selectedFile.size)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleUpload}
              disabled={isUploading}
              className="px-4 py-1.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                'Upload'
              )}
            </button>
            <button
              onClick={() => setSelectedFile(null)}
              className="p-1.5 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  );
}
