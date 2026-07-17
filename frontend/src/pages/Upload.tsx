import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { docApi } from '../api/services';
import { UploadCloud, File, AlertCircle } from 'lucide-react';

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [collectionId, setCollectionId] = useState<string>('');
  const [error, setError] = useState('');
  
  const queryClient = useQueryClient();
  const { data: collections } = useQuery({ queryKey: ['collections'], queryFn: docApi.getCollections });

  const uploadMutation = useMutation({
    mutationFn: docApi.uploadDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setFile(null);
      setError('');
      alert("Document uploaded and processing started!");
    },
    onError: (err: any) => {
      setError(err.response?.data?.error || 'Failed to upload document');
    }
  });

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) setFile(droppedFile);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a file.");
      return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    if (collectionId) {
      formData.append('collection_id', collectionId);
    }
    
    uploadMutation.mutate(formData);
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl mx-auto">
      <div>
        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Upload Document</h2>
        <p className="mt-2 text-slate-600">Add new documents to your workspace for AI analysis.</p>
      </div>

      <div className="glass-panel p-8 rounded-2xl">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 text-red-700 p-4 rounded-xl flex items-center gap-3">
              <AlertCircle size={20} />
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Select Collection (Optional)</label>
            <select
              value={collectionId}
              onChange={(e) => setCollectionId(e.target.value)}
              className="block w-full rounded-xl border border-slate-200 px-4 py-3 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white/50"
            >
              <option value="">-- No Collection --</option>
              {collections?.map((col: any) => (
                <option key={col.id} value={col.id}>{col.name}</option>
              ))}
            </select>
          </div>

          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            className={`mt-1 flex justify-center px-6 pt-10 pb-12 border-2 border-dashed rounded-2xl transition-colors ${
              file ? 'border-brand-500 bg-brand-50/50' : 'border-slate-300 hover:border-brand-400 bg-slate-50/50'
            }`}
          >
            <div className="space-y-2 text-center">
              {file ? (
                <div className="flex flex-col items-center">
                  <File className="mx-auto h-12 w-12 text-brand-500" />
                  <p className="text-sm font-medium text-slate-900 mt-2">{file.name}</p>
                  <p className="text-xs text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  <button type="button" onClick={() => setFile(null)} className="text-red-500 text-sm mt-2 font-medium hover:underline">
                    Remove
                  </button>
                </div>
              ) : (
                <>
                  <UploadCloud className="mx-auto h-12 w-12 text-slate-400" />
                  <div className="flex text-sm text-slate-600 justify-center">
                    <label className="relative cursor-pointer rounded-md bg-transparent font-medium text-brand-600 hover:text-brand-500 focus-within:outline-none">
                      <span>Upload a file</span>
                      <input type="file" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] || null)} accept=".pdf,.txt,.docx" />
                    </label>
                    <p className="pl-1">or drag and drop</p>
                  </div>
                  <p className="text-xs text-slate-500">PDF, DOCX, TXT up to 10MB</p>
                </>
              )}
            </div>
          </div>

          <div className="pt-4">
            <button
              type="submit"
              disabled={!file || uploadMutation.isPending}
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-brand-600 hover:bg-brand-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500 disabled:opacity-50 transition-all active:scale-[0.98]"
            >
              {uploadMutation.isPending ? 'Uploading & Processing...' : 'Upload Document'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
