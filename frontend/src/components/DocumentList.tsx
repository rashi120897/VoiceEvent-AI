import React from 'react';
import { FileText, Trash2, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import type { Document } from '../lib/api';

interface DocumentListProps {
  documents: Document[];
  onDelete: (id: string) => void;
  isDeleting: string | null;
}

export default function DocumentList({ documents, onDelete, isDeleting }: DocumentListProps) {
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ready':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
            <CheckCircle2 className="w-3 h-3" />
            Ready
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
            <Loader2 className="w-3 h-3 animate-spin" />
            Processing
          </span>
        );
      case 'error':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
            <XCircle className="w-3 h-3" />
            Error
          </span>
        );
      default:
        return null;
    }
  };

  if (documents.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500 text-sm">No documents uploaded yet</p>
        <p className="text-gray-400 text-xs mt-1">Upload your first document above to build your knowledge base</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead>
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Document</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Size</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Chunks</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Uploaded</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {documents.map((doc) => (
            <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-500 flex-shrink-0" />
                  <span className="text-sm font-medium text-gray-900 truncate max-w-[200px]">{doc.filename}</span>
                </div>
              </td>
              <td className="px-4 py-3 text-sm text-gray-500 uppercase">{doc.file_type}</td>
              <td className="px-4 py-3 text-sm text-gray-500">{formatFileSize(doc.file_size_bytes)}</td>
              <td className="px-4 py-3 text-sm text-gray-500">{doc.chunk_count}</td>
              <td className="px-4 py-3">{getStatusBadge(doc.status)}</td>
              <td className="px-4 py-3 text-sm text-gray-500">{formatDate(doc.created_at)}</td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() => onDelete(doc.id)}
                  disabled={isDeleting === doc.id}
                  className="p-1.5 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                  title="Delete document"
                >
                  {isDeleting === doc.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
