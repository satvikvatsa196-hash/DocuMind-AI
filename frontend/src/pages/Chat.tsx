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

  const [isStreaming, setIsStreaming] = useState(false);

  const runStreamQuery = async (queryText: string, sessionIdToUse: number, collectionIdToUse?: number) => {
    setIsStreaming(true);
    setLocalMessages(prev => [...prev, { role: 'AI', message: '', citations: [] }]);
    
    await chatApi.streamQuery(
      { query: queryText, session_id: sessionIdToUse, collection_id: collectionIdToUse },
      (chunk) => {
        setLocalMessages(prev => {
          const newMessages = [...prev];
          const lastIndex = newMessages.length - 1;
          const lastMsg = { ...newMessages[lastIndex] };
          
          if (chunk.token) {
            lastMsg.message += chunk.token;
          }
          if (chunk.citations) {
            lastMsg.citations = chunk.citations;
          }
          if (chunk.retrieved_passages) {
            lastMsg.retrieved_passages = chunk.retrieved_passages;
          }
          newMessages[lastIndex] = lastMsg;
          return newMessages;
        });
      },
      () => {
        setIsStreaming(false);
      },
      (err) => {
        console.error("Stream error:", err);
        setIsStreaming(false);
      }
    );
  };

  const sessionMutation = useMutation({
    mutationFn: chatApi.createSession,
    onSuccess: (session, variables) => {
      navigate(`/chat/${session.id}`);
      runStreamQuery((variables as any).initialQuery, session.id, collectionId ? Number(collectionId) : undefined);
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming || sessionMutation.isPending) return;

    const userMessage = input.trim();
    setInput('');
    setLocalMessages(prev => [...prev, { role: 'USER', message: userMessage }]);

    if (!sessionId) {
      sessionMutation.mutate({ 
        collection: collectionId ? Number(collectionId) : undefined,
        initialQuery: userMessage 
      } as any);
    } else {
      runStreamQuery(userMessage, Number(sessionId));
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
                {/* Citations and Retrieved Passages */}
                {(msg.citations?.length > 0 || msg.retrieved_passages?.length > 0) && (
                  <div className="mt-4 pt-4 border-t border-slate-100 space-y-3">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                      <Book size={12} /> Sources & Highlights
                    </p>
                    <div className="flex flex-col gap-3">
                      {(msg.retrieved_passages || msg.citations).map((cite: any, cidx: number) => (
                        <div key={cidx} className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                          <div className="flex justify-between items-center mb-2">
                            <a 
                              href={`#document-viewer-${cite.document_name}`}
                              className="font-medium text-sm text-brand-600 hover:text-brand-700 cursor-pointer hover:underline transition-colors flex items-center gap-1"
                              onClick={(e) => {
                                // Simulate navigating directly to the corresponding page in the document viewer
                                e.preventDefault();
                                alert(`Navigating to ${cite.document_name} on page ${cite.page_number}`);
                              }}
                            >
                              {cite.document_name} {cite.page_number && cite.page_number !== "-1" && cite.page_number !== -1 ? `(Pg ${cite.page_number})` : ''}
                            </a>
                            {cite.relevance_score && (
                              <span className="text-[10px] font-medium text-slate-500 bg-white px-2 py-0.5 rounded-full border border-slate-200 shadow-sm">
                                {Math.round(cite.relevance_score * 100)}% Match
                              </span>
                            )}
                          </div>
                          {cite.chunk_text && (
                            <p className="text-xs text-slate-600 border-l-2 border-brand-400 pl-3 py-1 my-1 bg-white rounded-r-md shadow-sm">
                              ... {cite.chunk_text} ...
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {(isStreaming && localMessages[localMessages.length - 1]?.message === '' || sessionMutation.isPending) && (
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
              disabled={isStreaming || sessionMutation.isPending}
            />
            <button
              type="submit"
              disabled={!input.trim() || isStreaming || sessionMutation.isPending}
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
