import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { orderService, Order } from '../services/productService';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { encryptRouteParam, fallbackRouteParam } from '../utils/urlCrypto';

export const OrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [orderRouteTokens, setOrderRouteTokens] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadOrders();
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      const pairs = await Promise.all(
        orders.map(async (order) => {
          try {
            return [order.id, await encryptRouteParam(order.id)] as const;
          } catch {
            return [order.id, fallbackRouteParam(order.id)] as const;
          }
        })
      );
      if (!active) return;
      const map: Record<string, string> = {};
      pairs.forEach(([id, token]) => {
        map[id] = token;
      });
      setOrderRouteTokens(map);
    })();
    return () => {
      active = false;
    };
  }, [orders]);

  const loadOrders = async () => {
    try {
      setLoading(true);
      const data = await orderService.getOrders(0, 50);
      setOrders(data);
    } catch (err: any) {
      setMessage('Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    const colors: { [key: string]: string } = {
      pending: '#ff9800',
      confirmed: '#2196f3',
      processing: '#9c27b0',
      shipped: '#00bcd4',
      delivered: '#4caf50',
      cancelled: '#f44336',
      return_requested: '#ff5722',
      returned: '#795548',
    };
    return colors[status] || '#666';
  };

  return (
    <ProtectedRoute>
      <div className="container" style={{ marginTop: '30px', marginBottom: '50px' }}>
        {message && <div className="alert alert-danger">{message}</div>}

        <h1>My Orders</h1>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '50px' }}>Loading orders...</div>
        ) : orders.length === 0 ? (
          <div className="card">
            <p>You don't have any orders yet</p>
            <a href="/products" className="btn btn-primary">Start Shopping</a>
          </div>
        ) : (
          <>
            {/* Desktop: table view */}
            <div className="orders-desktop">
              <table className="table">
                <thead>
                  <tr>
                    <th>Order Number</th>
                    <th>Date</th>
                    <th>Total</th>
                    <th>Items</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map(order => (
                    <tr key={order.id}>
                      <td>{order.order_number}</td>
                      <td>{new Date(order.created_at || '').toLocaleDateString()}</td>
                      <td>₹{order.total.toFixed(2)}</td>
                      <td>{order.items.length}</td>
                      <td>
                        <span style={{
                          backgroundColor: getStatusColor(order.status),
                          color: 'white',
                          padding: '4px 12px',
                          borderRadius: '4px',
                          fontSize: '12px',
                        }}>
                          {order.status.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <Link to={`/orders/${orderRouteTokens[order.id] || fallbackRouteParam(order.id)}`} className="btn btn-primary" style={{ padding: '5px 10px', fontSize: '12px', textDecoration: 'none' }}>
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile: card view */}
            <div className="orders-mobile">
              {orders.map(order => (
                <div key={order.id} className="order-card">
                  <div className="order-card-row">
                    <span className="order-card-label">Order #</span>
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>{order.order_number}</span>
                  </div>
                  <div className="order-card-row">
                    <span className="order-card-label">Date</span>
                    <span>{new Date(order.created_at || '').toLocaleDateString()}</span>
                  </div>
                  <div className="order-card-row">
                    <span className="order-card-label">Total</span>
                    <span style={{ fontWeight: 600, color: '#d32f2f' }}>₹{order.total.toFixed(2)}</span>
                  </div>
                  <div className="order-card-row">
                    <span className="order-card-label">Items</span>
                    <span>{order.items.length}</span>
                  </div>
                  <div className="order-card-row" style={{ marginBottom: '12px' }}>
                    <span className="order-card-label">Status</span>
                    <span style={{
                      backgroundColor: getStatusColor(order.status),
                      color: 'white',
                      padding: '4px 12px',
                      borderRadius: '4px',
                      fontSize: '12px',
                    }}>
                      {order.status.toUpperCase()}
                    </span>
                  </div>
                  <Link
                    to={`/orders/${orderRouteTokens[order.id] || fallbackRouteParam(order.id)}`}
                    className="btn btn-primary"
                    style={{ display: 'block', textAlign: 'center', textDecoration: 'none', width: '100%' }}
                  >
                    View Details
                  </Link>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </ProtectedRoute>
  );
};
