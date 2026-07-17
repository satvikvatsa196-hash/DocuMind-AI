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
};
