import api from './api';

export const contactService = {
  async submit(data: { name: string; email: string; subject: string; message: string }) {
    const res = await api.post('/contact/', data);
    return res.data;
  },
  async list(skip = 0, limit = 50, status?: string) {
    const params: Record<string, unknown> = { skip, limit };
    if (status) params.inquiry_status = status;
    const res = await api.get('/contact/', { params });
    return res.data;
  },
  async update(id: string, data: { status?: string; admin_notes?: string }) {
    const res = await api.put(`/contact/${id}`, data);
    return res.data;
  },
};
