import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { orderService, Order } from '../services/cartOrderService';
import { encryptRouteParam, fallbackRouteParam } from '../utils/urlCrypto';

const RETURN_STATUSES = ['return_requested', 'returned', 'cancelled'];

const statusStyle = (status: string) => {
  const map: Record<string, { bg: string; color: string }> = {
    return_requested: { bg: '#fff3e0', color: '#e65100' },
    returned: { bg: '#e8f5e9', color: '#2e7d32' },
    cancelled: { bg: '#ffebee', color: '#c62828' },
  };
  return map[status] || { bg: '#eee', color: '#333' };
};

export const ReturnsPage: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [orderRouteTokens, setOrderRouteTokens] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadReturns = async () => {
      try {
        const all: Order[] = await orderService.getOrders(0, 200);
        setOrders(all.filter((o) => RETURN_STATUSES.includes(o.status)));
      } catch {
        setError('Failed to load returned orders. Please ensure you are logged in.');
      } finally {
        setLoading(false);
      }
    };
    loadReturns();
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      const ids = new Set<string>();
      orders.forEach((o) => {
        if (o.id) ids.add(o.id);
        if (o.exchange_order_id) ids.add(o.exchange_order_id);
      });

      const pairs = await Promise.all(
        Array.from(ids).map(async (id) => {
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
        map[id] = token;
      });
      setOrderRouteTokens(map);
    })();
    return () => {
      active = false;
    };
  }, [orders]);

  return (
    <div className="container" style={{ marginTop: '30px', marginBottom: '50px' }}>
      <h1>Returns &amp; Exchanges</h1>
      <p style={{ color: '#666' }}>View your returned, cancelled, and exchange orders below.</p>

      {error && <div className="alert alert-danger">{error}</div>}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>Loading...</div>
      ) : orders.length === 0 ? (
        <div className="alert alert-info">You have no returned or cancelled orders.</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                <th style={{ padding: '10px' }}>Order #</th>
                <th style={{ padding: '10px' }}>Status</th>
                <th style={{ padding: '10px' }}>Reason</th>
                <th style={{ padding: '10px' }}>Items</th>
                <th style={{ padding: '10px' }}>Total</th>
                <th style={{ padding: '10px' }}>Exchange</th>
                <th style={{ padding: '10px' }}>Date</th>
                <th style={{ padding: '10px' }}></th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => {
                const s = statusStyle(o.status);
                return (
                  <tr key={o.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '10px' }}>{o.order_number}</td>
                    <td style={{ padding: '10px' }}>
                      <span style={{ padding: '4px 10px', borderRadius: '4px', fontSize: '13px', backgroundColor: s.bg, color: s.color }}>
                        {o.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td style={{ padding: '10px', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {o.return_reason || '—'}
                    </td>
                    <td style={{ padding: '10px' }}>{o.items?.length ?? 0}</td>
                    <td style={{ padding: '10px' }}>{'\u20B9'}{o.total?.toFixed(2)}</td>
                    <td style={{ padding: '10px' }}>
                      {o.exchange_order_id ? (
                        <Link to={`/orders/${orderRouteTokens[o.exchange_order_id] || fallbackRouteParam(o.exchange_order_id)}`} style={{ color: '#1565c0' }}>View Exchange</Link>
                      ) : '—'}
                    </td>
                    <td style={{ padding: '10px' }}>{o.created_at ? new Date(o.created_at).toLocaleDateString() : '—'}</td>
                    <td style={{ padding: '10px' }}>
                      <Link to={`/orders/${orderRouteTokens[o.id] || fallbackRouteParam(o.id)}`} className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: 12 }}>Details</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
