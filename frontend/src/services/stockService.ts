import api from './api';

export const stockService = {
  async list(productId?: string, skip = 0, limit = 50) {
    const params: Record<string, unknown> = { skip, limit };
    if (productId) params.product_id = productId;
    const res = await api.get('/stock/', { params });
    return res.data;
  },

  async addEntry(data: {
    product_id: string;
    transaction_type: string;
    quantity: number;
    reference?: string;
    notes?: string;
  }) {
    const res = await api.post('/stock/', data);
    return res.data;
  },
};
