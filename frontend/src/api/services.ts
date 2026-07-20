import api from './client';

export const authApi = {
  login: async (data: any) => {
    const res = await api.post('/users/login/', data);
    return res.data;
  },
  register: async (data: any) => {
    const res = await api.post('/users/register/', data);
    return res.data;
  },
};

export const docApi = {
  getDocuments: async () => {
    const res = await api.get('/documents/');
    return res.data;
  },
  getCollections: async () => {
    const res = await api.get('/documents/collections/');
    return res.data;
  },
  createCollection: async (data: { name: string; description?: string }) => {
    const res = await api.post('/documents/collections/', data);
    return res.data;
  },
  uploadDocument: async (formData: FormData) => {
    const res = await api.post('/documents/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
};

export const chatApi = {
  getSessions: async () => {
    const res = await api.get('/chat/sessions/');
    return res.data;
  },
  createSession: async (data: { collection?: number }) => {
    const res = await api.post('/chat/sessions/', data);
    return res.data;
  },
  getMessages: async (sessionId: number) => {
    const res = await api.get(`/chat/sessions/${sessionId}/messages/`);
    return res.data;
  },
  query: async (data: { query: string; session_id?: number; collection_id?: number }) => {
    const res = await api.post('/chat/query/', data);
    return res.data;
  },
  streamQuery: async (
    data: { query: string; session_id?: number; collection_id?: number },
    onMessage: (chunk: { token?: string; citations?: any[] }) => void,
    onComplete: () => void,
    onError: (err: any) => void
  ) => {
    const token = localStorage.getItem('access_token');
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    
    try {
      const res = await fetch(`${baseUrl}/chat/fastapi/stream/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(data)
      });

      if (!res.ok) {
        throw new Error('Stream request failed');
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) return;

      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          onComplete();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || ''; // Keep the incomplete part

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr.trim() === '{}') continue;
            try {
              const parsed = JSON.parse(dataStr);
              onMessage(parsed);
            } catch (e) {
              // Ignore parse error
            }
          } else if (line.startsWith('event: end')) {
            onComplete();
            return; // Terminate reading
          } else if (line.startsWith('event: error')) {
            onError(new Error('Stream returned error event'));
            return;
          }
        }
      }
    } catch (err) {
      onError(err);
    }
  },
};
