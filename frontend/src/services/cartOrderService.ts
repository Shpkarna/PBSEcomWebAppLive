import api from './api';

export interface CartItem {
  product_id: string;
  product_name: string;
  product_spec: string;
  quantity: number;
  price: number;
  line_subtotal?: number;
  discount_amount?: number;
  taxable_amount?: number;
  gst_amount?: number;
  total: number;
}

export interface CartResponse {
  items: CartItem[];
  cart_quote_id?: string;
  subtotal: number;
  total_discount?: number;
  total_gst: number;
  total: number;
}

export interface ShippingAddress {
  street1: string;
  street2?: string;
  landmark: string;
  district: string;
  area?: string;
  state: string;
  country: string;
  pincode: string;
  phone: string;
}

export interface Order {
  id: string;
  order_number: string;
  items: any[];
  subtotal: number;
  total_discount?: number;
  total_gst: number;
  total: number;
  payment_method: string;
  shipping_address?: ShippingAddress;
  shipment_date?: string;
  status: string;
  return_reason?: string;
  exchange_order_id?: string;
  discount?: number;
  payment_status?: string;
  payment_provider?: string;
  payment_reference?: string;
  created_at?: string;
}

export interface RazorpayOrderResponse {
  key_id: string;
  razorpay_order_id: string;
  amount: number;
  currency: string;
  receipt: string;
  total: number;
  subtotal: number;
  total_gst: number;
  total_discount: number;
}

export const cartService = {
  async getCart(): Promise<CartResponse> {
    const response = await api.get('/cart/');
    return response.data;
  },
  async addToCart(productId: string, quantity: number) {
    const response = await api.post('/cart/add', { product_id: productId, quantity });
    return response.data;
  },
  async removeFromCart(productId: string) {
    const response = await api.delete(`/cart/item/${productId}`);
    return response.data;
  },
  async clearCart() {
    const response = await api.delete('/cart/');
    return response.data;
  },
};

export const orderService = {
  async createOrder(
    items: any[],
    paymentMethod: string,
    shippingAddress: ShippingAddress,
    shipmentDate?: string,
    razorpayDetails?: {
      razorpay_order_id?: string;
      razorpay_payment_id?: string;
      razorpay_signature?: string;
    },
    cartQuoteId?: string
  ) {
    const response = await api.post('/orders/', {
      items, payment_method: paymentMethod, shipping_address: shippingAddress,
      shipment_date: shipmentDate || null,
      cart_quote_id: cartQuoteId || null,
      razorpay_order_id: razorpayDetails?.razorpay_order_id,
      razorpay_payment_id: razorpayDetails?.razorpay_payment_id,
      razorpay_signature: razorpayDetails?.razorpay_signature,
    });
    return response.data;
  },
  async createRazorpayOrder(items: any[], paymentMethod: string, shippingAddress: ShippingAddress, shipmentDate?: string, cartQuoteId?: string): Promise<RazorpayOrderResponse> {
    const response = await api.post('/orders/payment/razorpay/order', {
      items,
      payment_method: paymentMethod,
      shipping_address: shippingAddress,
      shipment_date: shipmentDate || null,
      cart_quote_id: cartQuoteId || null,
    });
    return response.data;
  },
  async getOrders(skip = 0, limit = 10) {
    const response = await api.get('/orders/', { params: { skip, limit } });
    return (response.data || []).map((o: any) => ({ ...o, id: o._id || o.id }));
  },
  async getOrder(id: string) {
    const response = await api.get(`/orders/${id}`);
    const o = response.data;
    return { ...o, id: o._id || o.id };
  },
  async updateOrderStatus(id: string, status: string) {
    const response = await api.put(`/orders/${id}/status`, null, { params: { new_status: status } });
    return response.data;
  },
  async returnOrder(id: string, reason: string) {
    const response = await api.post(`/orders/${id}/return`, { reason });
    return response.data;
  },
  async exchangeOrder(id: string, reason: string, newProductId: string, quantity: number = 1) {
    const response = await api.post(`/orders/${id}/exchange`, {
      reason, new_product_id: newProductId, quantity,
    });
    return response.data;
  },
};

export const savedProductService = {
  async getSavedProducts() {
    const response = await api.get('/cart/saved/');
    return response.data;
  },
  async saveProduct(productId: string) {
    const response = await api.post('/cart/saved/add', { product_id: productId });
    return response.data;
  },
  async removeSavedProduct(productId: string) {
    const response = await api.delete(`/cart/saved/${productId}`);
    return response.data;
  },
};
