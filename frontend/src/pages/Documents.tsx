import React, { useEffect, useState, useCallback } from 'react';
import { documentApi, type Document } from '../lib/api';
import FileUploader from '../components/FileUploader';
import DocumentList from '../components/DocumentList';

export default function Documents() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const data = await documentApi.list();
      setDocuments(data.documents);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch documents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
    // Poll for status updates every 5 seconds if any docs are processing
    const interval = setInterval(() => {
      if (documents.some((d) => d.status === 'processing')) {
        fetchDocuments();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchDocuments, documents]);

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document? This will also remove its vector embeddings.')) {
      return;
    }

    setDeleting(id);
    try {
      await documentApi.delete(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err: any) {
      setError(err.message || 'Failed to delete document');
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
        <p className="text-gray-500 mt-1">
          Upload documents to build your assistant's knowledge base
        </p>
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Document</h2>
        <FileUploader onUploadComplete={fetchDocuments} />
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 mb-6">
          {error}
        </div>
      )}

      {/* Documents List */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            Documents ({documents.length})
          </h2>
        </div>
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
          </div>
        ) : (
          <DocumentList
            documents={documents}
            onDelete={handleDelete}
            isDeleting={deleting}
          />
        )}
      </div>
    </div>
  );
}
