import api from './api';

// Re-export cart, order, and savedProduct services for backward compatibility
export { cartService, orderService, savedProductService } from './cartOrderService';
export type { CartItem, CartResponse, Order, ShippingAddress } from './cartOrderService';

export interface Product {
  id: string;
  name: string;
  sku: string;
  barcode: string;
  stock_price: number;
  sell_price: number;
  description?: string;
  category?: string;
  discount?: 'Discount percentage' | 'Discount amount';
  discount_value?: number;
  discount_type?: 'per quantity' | 'Total quantity' | 'Category';
  stock_quantity: number;
  gst_rate: number;
  image_media_ids?: string[];
  video_media_ids?: string[];
}

export interface ProductMediaItem {
  id: string;
  filename: string;
  content_type: string;
  media_type: 'image' | 'video';
  size: number;
  created_at?: string;
  url: string;
}

function normalizeProduct(p: any): Product {
  return { ...p, id: p.id || p._id };
}

function resolveApiAssetUrl(pathOrUrl: string): string {
  if (!pathOrUrl) return pathOrUrl;
  if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) return pathOrUrl;
  const baseURL = String(api.defaults.baseURL || '');
  const origin = baseURL.endsWith('/api') ? baseURL.slice(0, -4) : baseURL;
  return `${origin}${pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`}`;
}

export function getProductMediaFileUrl(mediaId: string): string {
  return resolveApiAssetUrl(`/api/products/media/file/${mediaId}`);
}

export const productService = {
  async getProducts(skip = 0, limit = 10, category?: string, sort_by?: string) {
    const response = await api.get('/products', { params: { skip, limit, category, sort_by } });
    const data = response.data;
    const list = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : [];
    return list.map(normalizeProduct);
  },
  async getProduct(id: string) {
    const response = await api.get(`/products/${id}`);
    return normalizeProduct(response.data);
  },
  async getProductByBarcode(barcode: string) {
    const response = await api.get(`/products/barcode/${barcode}`);
    return response.data;
  },
  async createProduct(product: Omit<Product, 'id'>) {
    const response = await api.post('/products', product);
    return normalizeProduct(response.data);
  },
  async updateProduct(id: string, updates: Partial<Product>) {
    const response = await api.put(`/products/${id}`, updates);
    return normalizeProduct(response.data);
  },
  async deleteProduct(id: string) {
    const response = await api.delete(`/products/${id}`);
    return response.data;
  },
  async updateStock(id: string, quantity: number) {
    const response = await api.post(`/products/${id}/stock`, null, { params: { quantity } });
    return response.data;
  },
  async uploadProductMedia(productId: string, imageFiles: File[], videoFiles: File[]) {
    const formData = new FormData();
    imageFiles.forEach((f) => formData.append('files', f));
    videoFiles.forEach((f) => formData.append('files', f));
    const response = await api.post(`/products/${productId}/media`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  async listProductMedia(productId: string): Promise<ProductMediaItem[]> {
    const response = await api.get(`/products/${productId}/media`);
    return (response.data?.items || []).map((item: ProductMediaItem) => ({
      ...item,
      url: resolveApiAssetUrl(item.url),
    }));
  },
};
