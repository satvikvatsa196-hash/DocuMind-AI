import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { chatApi, docApi } from '../api/services';
import { Send, Bot, User, Book, Loader2 } from 'lucide-react';

export default function Chat() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [collectionId, setCollectionId] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [localMessages, setLocalMessages] = useState<any[]>([]);

  const { data: collections } = useQuery({ queryKey: ['collections'], queryFn: docApi.getCollections });
  const { data: history } = useQuery({ 
    queryKey: ['messages', sessionId], 
    queryFn: () => chatApi.getMessages(Number(sessionId)),
    enabled: !!sessionId
  });

  useEffect(() => {
    if (history?.results) {
      setLocalMessages(history.results);
    }
  }, [history]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [localMessages]);

  const queryMutation = useMutation({
    mutationFn: chatApi.query,
    onSuccess: (data, variables) => {
      setLocalMessages(prev => [...prev, { role: 'AI', message: data.answer, citations: data.citations }]);
    }
  });

  const sessionMutation = useMutation({
    mutationFn: chatApi.createSession,
    onSuccess: (session, variables) => {
      navigate(`/chat/${session.id}`);
      // Immediately fire the query with new session
      queryMutation.mutate({ query: variables.initialQuery, session_id: session.id, collection_id: collectionId ? Number(collectionId) : undefined });
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || queryMutation.isPending) return;

    const userMessage = input.trim();
    setInput('');
    setLocalMessages(prev => [...prev, { role: 'USER', message: userMessage }]);

    if (!sessionId) {
      sessionMutation.mutate({ 
        collection: collectionId ? Number(collectionId) : undefined,
        initialQuery: userMessage 
      } as any);
    } else {
      queryMutation.mutate({ query: userMessage, session_id: Number(sessionId) });
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] max-w-4xl mx-auto animate-fade-in">
      <div className="flex justify-between items-end mb-6">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">AI Assistant</h2>
          <p className="mt-1 text-slate-600">Ask questions about your documents.</p>
        </div>
        {!sessionId && (
          <select
            value={collectionId}
            onChange={(e) => setCollectionId(e.target.value)}
            className="rounded-xl border border-slate-200 px-4 py-2 bg-white text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 shadow-sm"
          >
            <option value="">Search All Documents</option>
            {collections?.map((col: any) => (
              <option key={col.id} value={col.id}>Only {col.name}</option>
            ))}
          </select>
        )}
      </div>

      <div className="flex-1 glass-panel rounded-2xl flex flex-col overflow-hidden shadow-2xl shadow-brand-500/5">
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {localMessages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-4">
              <Bot size={48} className="text-brand-300" />
              <p>How can I help you with your documents today?</p>
            </div>
          )}
          
          {localMessages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === 'USER' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                msg.role === 'USER' ? 'bg-brand-600 text-white' : 'bg-gradient-to-br from-purple-500 to-indigo-600 text-white'
              }`}>
                {msg.role === 'USER' ? <User size={18} /> : <Bot size={18} />}
              </div>
              <div className={`max-w-[80%] rounded-2xl p-4 ${
                msg.role === 'USER' 
                  ? 'bg-brand-600 text-white rounded-tr-none' 
                  : 'bg-white border border-slate-100 shadow-sm rounded-tl-none text-slate-800'
              }`}>
                <p className="whitespace-pre-wrap">{msg.message}</p>
                
                {/* Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-slate-100 space-y-2">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                      <Book size={12} /> Sources
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {msg.citations.map((cite: any, cidx: number) => (
                        <span key={cidx} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 text-xs text-slate-600 font-medium">
                          {cite.document_name} {cite.page_number && cite.page_number !== "-1" ? `(Pg ${cite.page_number})` : ''}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {(queryMutation.isPending || sessionMutation.isPending) && (
             <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 text-white flex items-center justify-center shrink-0">
                <Bot size={18} />
              </div>
              <div className="bg-white border border-slate-100 shadow-sm rounded-2xl rounded-tl-none p-4 flex items-center gap-2 text-slate-500">
                <Loader2 size={16} className="animate-spin text-brand-500" />
                Thinking...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 bg-white border-t border-slate-100">
          <form onSubmit={handleSubmit} className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about your documents..."
              className="w-full pl-4 pr-12 py-4 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white transition-all shadow-inner"
              disabled={queryMutation.isPending || sessionMutation.isPending}
            />
            <button
              type="submit"
              disabled={!input.trim() || queryMutation.isPending || sessionMutation.isPending}
              className="absolute right-2 p-2 bg-brand-600 text-white rounded-lg hover:bg-brand-500 disabled:opacity-50 disabled:hover:bg-brand-600 transition-colors"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
