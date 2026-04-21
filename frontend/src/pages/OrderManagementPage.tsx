import React, { useEffect, useState } from 'react';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { adminService } from '../services/adminService';
import { encryptRouteParam, fallbackRouteParam } from '../utils/urlCrypto';

const STATUS_OPTIONS = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'return_requested', 'returned'];

const getStatusColor = (s: string) => {
  const m: Record<string, string> = {
    pending: '#ff9800', confirmed: '#2196f3', processing: '#9c27b0',
    shipped: '#00bcd4', delivered: '#4caf50', cancelled: '#f44336',
    return_requested: '#ff5722', returned: '#795548',
  };
  return m[s] || '#666';
};

export const OrderManagementPage: React.FC = () => {
  const [orders, setOrders] = useState<any[]>([]);
  const [orderRouteTokens, setOrderRouteTokens] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  const load = async () => {
    try { setOrders(await adminService.listOrders(0, 100, filterStatus || undefined)); } catch { setMessage('Failed to load orders'); }
  };

  useEffect(() => { load(); }, [filterStatus]);

  useEffect(() => {
    let active = true;
    (async () => {
      const pairs = await Promise.all(
        orders.map(async (o) => {
          const id = String(o.id || '');
          if (!id) return ['', ''] as const;
          try {
            return [id, await encryptRouteParam(id)] as const;
          } catch {
            return [id, fallbackRouteParam(id)] as const;
          }
        })
      );
      if (!active) return;
      const map: Record<string, string> = {};
      pairs.forEach(([id, token]) => {
        if (id) map[id] = token;
      });
      setOrderRouteTokens(map);
    })();
    return () => {
      active = false;
    };
  }, [orders]);

  const updateStatus = async (id: string, status: string) => {
    try {
      await adminService.updateOrderStatus(id, status);
      setMessage(`Order updated to ${status}`);
      await load();
    } catch { setMessage('Failed to update order'); }
  };

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="container" style={{ marginTop: 30, marginBottom: 50 }}>
        <h1>Order Management</h1>
        {message && <div className="alert alert-info">{message}</div>}

        <div style={{ marginBottom: 16, display: 'flex', gap: 10, alignItems: 'center' }}>
          <label style={{ fontWeight: 600 }}>Filter by Status:</label>
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
            style={{ padding: '6px 12px', border: '1px solid #ddd', borderRadius: 4 }}>
            <option value="">All</option>
            {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div className="card" style={{ overflowX: 'auto' }}>
          <h3>Orders ({orders.length})</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                <th style={{ padding: 8 }}>Order No</th>
                <th style={{ padding: 8 }}>Customer</th>
                <th style={{ padding: 8 }}>Total</th>
                <th style={{ padding: 8 }}>Payment</th>
                <th style={{ padding: 8 }}>Status</th>
                <th style={{ padding: 8 }}>Date</th>
                <th style={{ padding: 8 }}>Update</th>
                <th style={{ padding: 8 }}>Details</th>
              </tr>
            </thead>
            <tbody>{orders.map(o => (
              <tr key={o.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 8 }}>{o.order_number || o.id}</td>
                <td style={{ padding: 8 }}>{o.customer_id}</td>
                <td style={{ padding: 8 }}>₹{o.total?.toFixed?.(2) || o.total}</td>
                <td style={{ padding: 8 }}>{o.payment_method || '-'}</td>
                <td style={{ padding: 8 }}>
                  <span style={{
                    backgroundColor: getStatusColor(o.status), color: '#fff',
                    padding: '3px 10px', borderRadius: 4, fontSize: 12,
                  }}>{o.status}</span>
                </td>
                <td style={{ padding: 8, fontSize: 12 }}>{o.created_at ? new Date(o.created_at).toLocaleDateString() : '-'}</td>
                <td style={{ padding: 8 }}>
                  <select value={o.status} onChange={e => updateStatus(o.id, e.target.value)}
                    style={{ padding: '4px 8px', border: '1px solid #ddd', borderRadius: 4 }}>
                    {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
                <td style={{ padding: 8 }}>
                  <a
                    href={`/orders/${orderRouteTokens[o.id] || fallbackRouteParam(String(o.id))}`}
                    className="btn btn-primary"
                    style={{ padding: '4px 10px', fontSize: 12, textDecoration: 'none' }}
                  >
                    View
                  </a>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </ProtectedRoute>
  );
};
