import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { orderService, Order } from '../services/cartOrderService';
import { productService, Product } from '../services/productService';
import { authService } from '../services/authService';
import { adminService } from '../services/adminService';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { decryptRouteParamOrFallback, encryptRouteParam, fallbackRouteParam } from '../utils/urlCrypto';

const STATUS_STEPS = ['pending', 'confirmed', 'processing', 'shipped', 'delivered'];
const STATUS_OPTIONS = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'return_requested', 'returned'];

const getStatusColor = (s: string) => {
  const m: Record<string, string> = {
    pending: '#ff9800', confirmed: '#2196f3', processing: '#9c27b0',
    shipped: '#00bcd4', delivered: '#4caf50', cancelled: '#f44336',
    return_requested: '#ff5722', returned: '#795548',
  };
  return m[s] || '#666';
};

export const OrderDetailPage: React.FC = () => {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const [resolvedOrderId, setResolvedOrderId] = useState('');
  const [exchangeOrderToken, setExchangeOrderToken] = useState('');
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);

  // Admin edit state
  const [editStatus, setEditStatus] = useState('');
  const [statusSaving, setStatusSaving] = useState(false);

  // Return/Exchange state
  const [showReturnForm, setShowReturnForm] = useState(false);
  const [showExchangeForm, setShowExchangeForm] = useState(false);
  const [returnReason, setReturnReason] = useState('');
  const [exchangeReason, setExchangeReason] = useState('');
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [exchangeQty, setExchangeQty] = useState(1);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const init = async () => {
      const user = await authService.getCurrentUser();
      if (user) setIsAdmin(user.role === 'admin');
      if (orderId) {
        const resolved = await decryptRouteParamOrFallback(orderId);
        setResolvedOrderId(resolved);
      }
    };
    init();
  }, [orderId]);

  useEffect(() => {
    if (!resolvedOrderId) return;
    void loadOrder();
  }, [resolvedOrderId]);

  useEffect(() => {
    if (!order?.exchange_order_id) {
      setExchangeOrderToken('');
      return;
    }
    let active = true;
    (async () => {
      try {
        const token = await encryptRouteParam(order.exchange_order_id!);
        if (active) setExchangeOrderToken(token);
      } catch {
        if (active) setExchangeOrderToken(fallbackRouteParam(order.exchange_order_id!));
      }
    })();
    return () => {
      active = false;
    };
  }, [order?.exchange_order_id]);

  const loadOrder = async () => {
    try {
      setLoading(true);
      const data = await orderService.getOrder(resolvedOrderId);
      setOrder(data);
      setEditStatus(data.status);
    } catch {
      setError('Failed to load order details');
    } finally {
      setLoading(false);
    }
  };

  const handleAdminStatusUpdate = async () => {
    if (!editStatus) return;
    setStatusSaving(true);
    setError('');
    try {
      await adminService.updateOrderStatus(resolvedOrderId, editStatus);
      setMessage(`Order status updated to "${editStatus.replace(/_/g, ' ')}"`);
      await loadOrder();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update order status');
    } finally {
      setStatusSaving(false);
    }
  };

  const loadProducts = async () => {
    try {
      const data = await productService.getProducts(0, 100);
      setProducts(data);
    } catch {}
  };

  const handleReturn = async () => {
    if (!returnReason.trim()) return;
    setSubmitting(true);
    try {
      await orderService.returnOrder(resolvedOrderId, returnReason);
      setMessage('Order returned successfully');
      setShowReturnForm(false);
      loadOrder();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to return order');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExchange = async () => {
    if (!exchangeReason.trim() || !selectedProduct) return;
    setSubmitting(true);
    try {
      const result = await orderService.exchangeOrder(resolvedOrderId, exchangeReason, selectedProduct, exchangeQty);
      setMessage(
        `Exchange order created! Discount applied: ₹${result.discount_applied?.toFixed(2) || '0.00'}. ` +
        `You pay: ₹${result.adjusted_total?.toFixed(2) || '0.00'}`
      );
      setShowExchangeForm(false);
      loadOrder();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create exchange');
    } finally {
      setSubmitting(false);
    }
  };

  const openExchangeForm = () => {
    setShowExchangeForm(true);
    loadProducts();
  };

  if (loading) return <div style={{ textAlign: 'center', padding: '50px' }}>Loading...</div>;
  if (error && !order) return <div className="container" style={{ marginTop: 30 }}><div className="alert alert-danger">{error}</div></div>;
  if (!order) return <div className="container" style={{ marginTop: 30 }}><div className="alert alert-danger">Order not found</div></div>;

  const currentStep = STATUS_STEPS.indexOf(order.status);
  const isReturnable = !isAdmin && order.status === 'delivered';
  const isExchangeable = !isAdmin && (order.status === 'delivered' || order.status === 'returned');
  const appliedDiscount = Number((order as any).total_discount ?? (order as any).discount ?? 0);
  const hasDiscount = !Number.isNaN(appliedDiscount) && appliedDiscount > 0;

  return (
    <ProtectedRoute>
      <div className="container" style={{ marginTop: '30px', marginBottom: '50px', maxWidth: '800px' }}>

        {/* Top navigation */}
        <div style={{ marginBottom: 20 }}>
          <button
            className="btn btn-secondary"
            onClick={() => navigate('/orders')}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            ← Back to My Orders
          </button>
        </div>

        {message && <div className="alert alert-success">{message}</div>}
        {error && <div className="alert alert-danger">{error}</div>}

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <h1 style={{ margin: 0 }}>Order #{order.order_number}</h1>
          {isAdmin && (
            <span style={{
              backgroundColor: '#1565c0', color: '#fff',
              padding: '4px 12px', borderRadius: 4, fontSize: 12, fontWeight: 600,
            }}>
              Admin View
            </span>
          )}
        </div>

        {/* Admin Controls — editable panel for admin users */}
        {isAdmin && (
          <div className="card" style={{ marginBottom: 20, backgroundColor: '#e3f2fd', border: '1px solid #90caf9' }}>
            <h3 style={{ marginTop: 0, color: '#1565c0' }}>Admin Controls</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <div>
                <label style={{ fontWeight: 600, marginRight: 8 }}>Order Status:</label>
                <select
                  value={editStatus}
                  onChange={e => setEditStatus(e.target.value)}
                  style={{ padding: '8px 12px', border: '1px solid #90caf9', borderRadius: 4, fontSize: 14 }}
                >
                  {STATUS_OPTIONS.map(s => (
                    <option key={s} value={s}>
                      {s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </option>
                  ))}
                </select>
              </div>
              <button
                className="btn btn-primary"
                onClick={handleAdminStatusUpdate}
                disabled={statusSaving || editStatus === order.status}
                style={{ minWidth: 120 }}
              >
                {statusSaving ? 'Saving...' : 'Save Status'}
              </button>
            </div>
          </div>
        )}

        {/* Status timeline — read-only */}
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 style={{ marginTop: 0 }}>Order Status</h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 10 }}>
            {STATUS_STEPS.map((step, i) => (
              <React.Fragment key={step}>
                <div style={{ textAlign: 'center', flex: 1 }}>
                  <div style={{
                    width: 32, height: 32, borderRadius: '50%', margin: '0 auto 4px',
                    backgroundColor: i <= currentStep ? getStatusColor(order.status) : '#ddd',
                    color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 14, fontWeight: 600,
                  }}>{i + 1}</div>
                  <div style={{ fontSize: 11, textTransform: 'capitalize', color: i <= currentStep ? '#333' : '#aaa' }}>{step}</div>
                </div>
                {i < STATUS_STEPS.length - 1 && (
                  <div style={{ flex: 1, height: 3, backgroundColor: i < currentStep ? getStatusColor(order.status) : '#ddd' }} />
                )}
              </React.Fragment>
            ))}
          </div>
          {(order.status === 'cancelled' || order.status === 'returned' || order.status === 'return_requested') && (
            <div style={{
              padding: '8px 16px', borderRadius: 4, marginTop: 8,
              backgroundColor: getStatusColor(order.status), color: '#fff', display: 'inline-block',
            }}>
              {order.status.replace(/_/g, ' ').toUpperCase()}
              {order.return_reason && <span> — {order.return_reason}</span>}
            </div>
          )}
        </div>

        {/* Order info — read-only */}
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 style={{ marginTop: 0 }}>Order Details</h3>
          <div className="order-detail-info-grid">
            <div><strong>Order Number:</strong> {order.order_number}</div>
            <div><strong>Date:</strong> {order.created_at ? new Date(order.created_at).toLocaleString() : '—'}</div>
            <div><strong>Payment:</strong> {order.payment_method}</div>
            <div><strong>Preferred Shipment Date:</strong> {order.shipment_date || 'Not specified'}</div>
            <div className="order-detail-full-width">
              <strong>Delivery Address:</strong>{' '}
              {order.shipping_address
                ? (typeof order.shipping_address === 'string'
                    ? order.shipping_address
                    : [order.shipping_address.street1, order.shipping_address.street2, order.shipping_address.landmark, order.shipping_address.district, order.shipping_address.area, order.shipping_address.state, order.shipping_address.country, order.shipping_address.pincode].filter(Boolean).join(', '))
                : '—'}
            </div>
          </div>
        </div>

        {/* Exchange order link */}
        {order.exchange_order_id && (
          <div className="alert alert-info">
            This order was exchanged. <Link to={`/orders/${exchangeOrderToken || fallbackRouteParam(order.exchange_order_id)}`}>View exchange order</Link>
          </div>
        )}

        {/* Items table — read-only */}
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 style={{ marginTop: 0 }}>Items</h3>
          <div className="order-detail-items-desktop">
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                  <th style={{ padding: 8 }}>Product</th>
                  <th style={{ padding: 8 }}>Qty</th>
                  <th style={{ padding: 8 }}>Unit Price</th>
                  <th style={{ padding: 8 }}>GST</th>
                  <th style={{ padding: 8 }}>Total</th>
                </tr>
              </thead>
              <tbody>
                {order.items.map((item: any, i: number) => (
                  <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: 8 }}>{item.product_name}</td>
                    <td style={{ padding: 8 }}>{item.quantity}</td>
                    <td style={{ padding: 8 }}>₹{item.sell_price?.toFixed(2)}</td>
                    <td style={{ padding: 8 }}>₹{item.gst_amount?.toFixed(2)}</td>
                    <td style={{ padding: 8 }}>₹{item.total?.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="order-detail-items-mobile">
            {order.items.map((item: any, i: number) => (
              <div key={i} className="order-detail-item-card">
                <div className="order-detail-item-name">{item.product_name}</div>
                <div className="order-detail-item-row">
                  <span>Qty</span>
                  <strong>{item.quantity}</strong>
                </div>
                <div className="order-detail-item-row">
                  <span>Unit Price</span>
                  <span>₹{item.sell_price?.toFixed(2)}</span>
                </div>
                <div className="order-detail-item-row">
                  <span>GST</span>
                  <span>₹{item.gst_amount?.toFixed(2)}</span>
                </div>
                <div className="order-detail-item-row" style={{ marginBottom: 0, fontWeight: 600 }}>
                  <span>Total</span>
                  <span>₹{item.total?.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
          <div style={{ textAlign: 'right', marginTop: 10, borderTop: '1px solid #ddd', paddingTop: 10 }}>
            <div>Subtotal: ₹{order.subtotal?.toFixed(2)}</div>
            <div>GST: ₹{order.total_gst?.toFixed(2)}</div>
            {hasDiscount && (
              <div style={{ color: '#4caf50' }}>Discount: -₹{appliedDiscount.toFixed(2)}</div>
            )}
            <div style={{ fontWeight: 700, fontSize: 18 }}>Total: ₹{order.total?.toFixed(2)}</div>
          </div>
        </div>

        {/* Customer-only: Return / Exchange action buttons */}
        {(isReturnable || isExchangeable) && (
          <div className="order-detail-action-row">
            {isReturnable && (
              <button className="btn btn-secondary" onClick={() => setShowReturnForm(!showReturnForm)}>
                Return Order
              </button>
            )}
            {isExchangeable && (
              <button className="btn btn-primary" onClick={openExchangeForm}>
                Exchange for Another Product
              </button>
            )}
          </div>
        )}

        {/* Customer-only: Return form */}
        {!isAdmin && showReturnForm && (
          <div className="card" style={{ marginBottom: 20, backgroundColor: '#fff3e0' }}>
            <h3 style={{ marginTop: 0 }}>Return Order</h3>
            <div className="form-group">
              <label>Reason for Return</label>
              <textarea value={returnReason} onChange={e => setReturnReason(e.target.value)}
                placeholder="Please describe why you want to return this order..."
                style={{ width: '100%', height: 80, padding: 10, border: '1px solid #ddd', borderRadius: 4 }} />
            </div>
            <div className="order-detail-form-actions">
              <button className="btn btn-primary" onClick={handleReturn} disabled={submitting || !returnReason.trim()}>
                {submitting ? 'Processing...' : 'Confirm Return'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowReturnForm(false)}>Cancel</button>
            </div>
          </div>
        )}

        {/* Customer-only: Exchange form */}
        {!isAdmin && showExchangeForm && (
          <div className="card" style={{ marginBottom: 20, backgroundColor: '#e8f5e9' }}>
            <h3 style={{ marginTop: 0 }}>Exchange Order</h3>
            <p style={{ color: '#666', fontSize: 13 }}>
              Select a replacement product. If the new product costs more, you'll get a discount to match your original order price.
              If it costs less, it's issued at no extra charge.
            </p>
            <div className="form-group">
              <label>Reason for Exchange</label>
              <textarea value={exchangeReason} onChange={e => setExchangeReason(e.target.value)}
                placeholder="Please describe why you want to exchange..."
                style={{ width: '100%', height: 60, padding: 10, border: '1px solid #ddd', borderRadius: 4 }} />
            </div>
            <div className="form-group">
              <label>Select New Product</label>
              <select value={selectedProduct} onChange={e => setSelectedProduct(e.target.value)}
                style={{ width: '100%', padding: 10, border: '1px solid #ddd', borderRadius: 4 }}>
                <option value="">-- Select a product --</option>
                {products.filter(p => p.stock_quantity > 0).map(p => (
                  <option key={p.id} value={p.id}>{p.name} — ₹{p.sell_price} (Stock: {p.stock_quantity})</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Quantity</label>
              <input type="number" value={exchangeQty} onChange={e => setExchangeQty(Math.max(1, Number(e.target.value)))}
                min={1} style={{ width: '100%', maxWidth: 100, padding: 10, border: '1px solid #ddd', borderRadius: 4 }} />
            </div>
            <div className="order-detail-form-actions">
              <button className="btn btn-primary" onClick={handleExchange}
                disabled={submitting || !exchangeReason.trim() || !selectedProduct}>
                {submitting ? 'Processing...' : 'Confirm Exchange'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowExchangeForm(false)}>Cancel</button>
            </div>
          </div>
        )}

        {/* Bottom navigation */}
        <div style={{ marginTop: 10 }}>
          <button
            className="btn btn-secondary"
            onClick={() => navigate('/orders')}
          >
            ← Back to My Orders
          </button>
        </div>
      </div>
    </ProtectedRoute>
  );
};
