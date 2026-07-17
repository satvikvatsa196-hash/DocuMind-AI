import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { docApi } from '../api/services';
import { Folder, Plus } from 'lucide-react';

export default function Collections() {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  
  const queryClient = useQueryClient();
  const { data: collections, isLoading } = useQuery({ queryKey: ['collections'], queryFn: docApi.getCollections });

  const createMutation = useMutation({
    mutationFn: docApi.createCollection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      setIsCreating(false);
      setName('');
      setDescription('');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({ name, description });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Collections</h2>
          <p className="mt-2 text-slate-600">Organize your documents into searchable folders.</p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-xl font-medium shadow-sm hover:bg-brand-500 transition-colors"
        >
          <Plus size={20} />
          New Collection
        </button>
      </div>

      {isCreating && (
        <div className="glass-panel p-6 rounded-2xl animate-slide-up border-l-4 border-l-brand-500">
          <h3 className="text-lg font-medium mb-4 text-slate-900">Create New Collection</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700">Name</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 block w-full rounded-xl border border-slate-200 px-4 py-2 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="mt-1 block w-full rounded-xl border border-slate-200 px-4 py-2 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white/50"
                rows={3}
              />
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="bg-brand-600 text-white px-4 py-2 rounded-xl font-medium hover:bg-brand-500 transition-colors"
              >
                {createMutation.isPending ? 'Creating...' : 'Create'}
              </button>
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="bg-slate-100 text-slate-700 px-4 py-2 rounded-xl font-medium hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          <p className="text-slate-500">Loading collections...</p>
        ) : (
          collections?.map((col: any) => (
            <div key={col.id} className="glass-panel p-6 rounded-2xl hover:shadow-xl transition-shadow cursor-pointer group">
              <div className="w-12 h-12 bg-brand-100 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Folder className="text-brand-600" size={24} />
              </div>
              <h3 className="text-lg font-semibold text-slate-900">{col.name}</h3>
              <p className="text-sm text-slate-500 mt-1 line-clamp-2">{col.description || 'No description provided.'}</p>
              <p className="text-xs text-slate-400 mt-4">{new Date(col.created_at).toLocaleDateString()}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
