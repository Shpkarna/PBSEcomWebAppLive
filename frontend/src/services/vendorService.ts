import api from './api';

export const vendorService = {
  async list(skip = 0, limit = 50) {
    const res = await api.get('/vendors/', { params: { skip, limit } });
    return res.data;
  },

  async create(data: Record<string, string | undefined>) {
    const res = await api.post('/vendors/', data);
    return res.data;
  },

  async get(id: string) {
    const res = await api.get(`/vendors/${id}`);
    return res.data;
  },

  async update(id: string, data: Record<string, string | undefined>) {
    const res = await api.put(`/vendors/${id}`, data);
    return res.data;
  },

  async remove(id: string) {
    await api.delete(`/vendors/${id}`);
  },
};
