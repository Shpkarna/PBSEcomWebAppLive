import api from './api';

export type CategoryDiscountType = 'Discount percentage' | 'Discount amount';

export interface CategoryPayload {
  name: string;
  description?: string;
  discount_type?: CategoryDiscountType;
  discount_value?: number;
}

export interface CategoryRow extends CategoryPayload {
  id: string;
}

export const categoryService = {
  async list(skip = 0, limit = 50) {
    const res = await api.get('/categories/', { params: { skip, limit } });
    return res.data as CategoryRow[];
  },

  async create(data: CategoryPayload) {
    const res = await api.post('/categories/', data);
    return res.data;
  },

  async get(id: string) {
    const res = await api.get(`/categories/${id}`);
    return res.data;
  },

  async update(id: string, data: Partial<CategoryPayload>) {
    const res = await api.put(`/categories/${id}`, data);
    return res.data;
  },

  async remove(id: string) {
    await api.delete(`/categories/${id}`);
  },
};
