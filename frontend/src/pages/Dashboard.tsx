import { useQuery } from '@tanstack/react-query';
import { docApi, chatApi } from '../api/services';
import { FileText, MessageSquare, Folder } from 'lucide-react';

export default function Dashboard() {
  const { data: documents } = useQuery({ queryKey: ['documents'], queryFn: docApi.getDocuments });
  const { data: collections } = useQuery({ queryKey: ['collections'], queryFn: docApi.getCollections });
  const { data: sessions } = useQuery({ queryKey: ['sessions'], queryFn: chatApi.getSessions });

  const stats = [
    { name: 'Total Documents', value: documents?.length || 0, icon: FileText, color: 'text-blue-600', bg: 'bg-blue-100' },
    { name: 'Collections', value: collections?.length || 0, icon: Folder, color: 'text-indigo-600', bg: 'bg-indigo-100' },
    { name: 'Chat Sessions', value: sessions?.results?.length || 0, icon: MessageSquare, color: 'text-purple-600', bg: 'bg-purple-100' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Dashboard</h2>
        <p className="mt-2 text-slate-600">Overview of your intelligent document workspace.</p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {stats.map((stat) => (
          <div key={stat.name} className="glass-panel overflow-hidden rounded-2xl px-6 py-8 transition-all hover:shadow-2xl hover:-translate-y-1">
            <div className="flex items-center">
              <div className={`p-4 rounded-xl ${stat.bg}`}>
                <stat.icon className={`h-8 w-8 ${stat.color}`} />
              </div>
              <div className="ml-5">
                <p className="text-sm font-medium text-slate-500 truncate">{stat.name}</p>
                <p className="mt-1 text-3xl font-semibold text-slate-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 glass-panel rounded-2xl p-6">
        <h3 className="text-lg font-medium text-slate-900 mb-4">Recent Documents</h3>
        <div className="divide-y divide-slate-100">
          {documents?.slice(0, 5).map((doc: any) => (
            <div key={doc.id} className="py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="text-brand-500 h-5 w-5" />
                <div>
                  <p className="text-sm font-medium text-slate-900">{doc.file_name}</p>
                  <p className="text-xs text-slate-500">{new Date(doc.uploaded_at).toLocaleDateString()}</p>
                </div>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                doc.processing_status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                doc.processing_status === 'FAILED' ? 'bg-red-100 text-red-700' :
                'bg-yellow-100 text-yellow-700'
              }`}>
                {doc.processing_status}
              </span>
            </div>
          ))}
          {documents?.length === 0 && (
            <p className="text-sm text-slate-500 text-center py-4">No documents uploaded yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
