'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  Upload,
  Search,
  Trash2,
  Database,
  Sparkles,
  FileCheck,
  AlertCircle,
  Clock,
  Layers,
  ArrowRight,
  RotateCw,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/shared/EmptyState';
import { TableRowSkeleton } from '@/components/shared/LoadingStates';
import {
  uploadDocument,
  getDocuments,
  deleteDocument,
  searchDocuments,
} from '@/lib/api';
import { DocumentResponse, SearchResult } from '@/lib/types';
import { formatDate } from '@/lib/utils';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Upload state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [brandName, setBrandName] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchBrand, setSearchBrand] = useState<string>('');
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [isSearching, setIsSearching] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setIsLoading(true);
      const docs = await getDocuments();
      setDocuments(docs || []);
    } catch {
      setDocuments([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setUploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError('Please choose a document to upload (PDF, TXT, MD, DOCX)');
      return;
    }
    if (!brandName.trim()) {
      setUploadError('Please provide a brand name for this document');
      return;
    }

    try {
      setIsUploading(true);
      setUploadError(null);
      setUploadSuccess(null);

      await uploadDocument(uploadFile, brandName.trim());
      setUploadSuccess(`Successfully uploaded and indexed "${uploadFile.name}"!`);
      setUploadFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await loadDocuments();
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Are you sure you want to remove this document from the vector store?')) return;
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err: any) {
      alert(`Error deleting document: ${err.message}`);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    try {
      setIsSearching(true);
      const res = await searchDocuments(
        searchQuery.trim(),
        searchBrand.trim() || undefined,
        5
      );
      setSearchResults(res.results || []);
    } catch (err: any) {
      alert(`Search error: ${err.message}`);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="flex-1 p-6 md:p-10 space-y-10 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="pb-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
            <Database className="w-7 h-7 text-indigo-400" />
            Brand Knowledge & RAG Documents
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Store product datasheets, guidelines, and pitch decks in ChromaDB for grounded ad copy generation
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={loadDocuments}
          leftIcon={<RotateCw className="w-4 h-4" />}
        >
          Refresh Store
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Upload Form */}
        <div className="space-y-6">
          <Card className="p-6 border-slate-800 bg-slate-900/60">
            <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <Upload className="w-4 h-4 text-indigo-400" />
              Upload Brand Document
            </h2>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <Input
                label="Associated Brand"
                placeholder="e.g. ApexGear, Lumina"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                required
              />

              {/* Drag and drop box */}
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
                  uploadFile
                    ? 'border-indigo-500 bg-indigo-500/10'
                    : 'border-slate-800 hover:border-slate-700 bg-slate-950/60'
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  className="hidden"
                  accept=".pdf,.txt,.md,.docx,.csv"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setUploadFile(e.target.files[0]);
                    }
                  }}
                />
                <div className="flex flex-col items-center justify-center space-y-2">
                  <div className="w-10 h-10 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                    <FileText className="w-5 h-5" />
                  </div>
                  {uploadFile ? (
                    <div>
                      <p className="text-xs font-semibold text-white break-all">
                        {uploadFile.name}
                      </p>
                      <p className="text-[11px] text-indigo-300 mt-0.5">
                        {(uploadFile.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs font-semibold text-slate-300">
                        Click or drag document here
                      </p>
                      <p className="text-[11px] text-slate-500 mt-1">
                        Supports PDF, TXT, Markdown, DOCX
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {uploadError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                  {uploadError}
                </div>
              )}

              {uploadSuccess && (
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-1.5">
                  <FileCheck className="w-4 h-4" />
                  <span>{uploadSuccess}</span>
                </div>
              )}

              <Button
                type="submit"
                variant="primary"
                className="w-full"
                isLoading={isUploading}
                leftIcon={<Upload className="w-4 h-4" />}
                disabled={!uploadFile || !brandName.trim()}
              >
                Index Into ChromaDB
              </Button>
            </form>
          </Card>

          {/* Semantic Search Panel */}
          <Card className="p-6 border-slate-800 bg-slate-900/60 space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Search className="w-4 h-4 text-cyan-400" />
              Semantic Search Tester
            </h2>
            <p className="text-xs text-slate-400">
              Query vector embeddings directly to inspect matching context chunks.
            </p>

            <form onSubmit={handleSearch} className="space-y-3">
              <Input
                placeholder="Search prompt or query..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                required
              />
              <Input
                placeholder="Filter by brand (optional)..."
                value={searchBrand}
                onChange={(e) => setSearchBrand(e.target.value)}
              />
              <Button
                type="submit"
                variant="secondary"
                className="w-full"
                size="sm"
                isLoading={isSearching}
                leftIcon={<Search className="w-4 h-4" />}
              >
                Search Knowledge Base
              </Button>
            </form>
          </Card>
        </div>

        {/* Right Column: Document Table & Search Results */}
        <div className="lg:col-span-2 space-y-8">
          {/* Search Results Display */}
          {searchResults !== null && (
            <Card className="p-6 border-slate-800 bg-slate-900/70 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-cyan-400" />
                  Vector Results for &ldquo;{searchQuery}&rdquo;
                </h3>
                <button
                  onClick={() => setSearchResults(null)}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Clear Results
                </button>
              </div>

              {searchResults.length === 0 ? (
                <p className="text-xs text-slate-400">No matching chunks found.</p>
              ) : (
                <div className="space-y-3">
                  {searchResults.map((res, i) => (
                    <div
                      key={res.chunk_id || i}
                      className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-mono text-cyan-400 font-semibold">
                          Relevance Score: {(res.score * 100).toFixed(1)}%
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          Chunk #{res.chunk_id?.slice(0, 8)}
                        </span>
                      </div>
                      <p className="text-slate-200 leading-relaxed italic">
                        &ldquo;{res.text}&rdquo;
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* Uploaded Documents Table */}
          <Card className="border-slate-800 bg-slate-900/60 overflow-hidden">
            <CardHeader className="p-6 border-b border-slate-800">
              <CardTitle className="text-base font-bold text-white flex items-center justify-between">
                <span>Indexed Documents ({documents.length})</span>
                <span className="text-xs font-normal text-slate-400">
                  Vector Collections
                </span>
              </CardTitle>
            </CardHeader>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Filename</th>
                    <th className="py-3 px-4">Brand</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Chunks</th>
                    <th className="py-3 px-4">Indexed Date</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {isLoading ? (
                    <TableRowSkeleton columns={6} />
                  ) : documents.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400">
                        No documents indexed yet. Upload brand materials on the left to ground the generation agents.
                      </td>
                    </tr>
                  ) : (
                    documents.map((doc) => (
                      <tr key={doc.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-3.5 px-4 font-medium text-white flex items-center gap-2">
                          <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                          <span className="truncate max-w-[180px]">{doc.filename}</span>
                        </td>
                        <td className="py-3.5 px-4 text-slate-300">{doc.brand_name}</td>
                        <td className="py-3.5 px-4">
                          <Badge
                            variant={
                              doc.status === 'indexed'
                                ? 'success'
                                : doc.status === 'processing'
                                ? 'warning'
                                : 'error'
                            }
                            dot
                          >
                            {doc.status}
                          </Badge>
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 font-mono">
                          {doc.chunks_count || 'Auto'}
                        </td>
                        <td className="py-3.5 px-4 text-slate-400">
                          {formatDate(doc.created_at)}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={() => handleDelete(doc.id)}
                            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                            title="Delete Document"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
