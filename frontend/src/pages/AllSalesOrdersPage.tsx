import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { adminService, SalesOrderFilters } from '../services/adminService';
import { encryptRouteParam, fallbackRouteParam } from '../utils/urlCrypto';

const formatAmount = (value: unknown) => {
  const n = Number(value);
  if (Number.isNaN(n)) return '-';
  return `₹${n.toFixed(2)}`;
};

export const AllSalesOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<any[]>([]);
  const [orderRouteTokens, setOrderRouteTokens] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const [orderId, setOrderId] = useState('');
  const [orderNumber, setOrderNumber] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [amountMin, setAmountMin] = useState('');
  const [amountMax, setAmountMax] = useState('');

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize]);

  const loadOrders = async (targetPage = page) => {
    setLoading(true);
    setMessage('');
    try {
      const skip = (targetPage - 1) * pageSize;
      const filters: SalesOrderFilters = {
        orderId,
        orderNumber,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        amountMin: amountMin === '' ? undefined : Number(amountMin),
        amountMax: amountMax === '' ? undefined : Number(amountMax),
      };

      const data = await adminService.listSalesOrders(skip, pageSize, filters);
      setOrders(data.items || []);
      setTotal(data.total || 0);
      setPage(targetPage);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to load sales orders');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders(1);
  }, [pageSize]);

  const onApplyFilters = () => {
    loadOrders(1);
  };

  const onResetFilters = () => {
    setOrderId('');
    setOrderNumber('');
    setDateFrom('');
    setDateTo('');
    setAmountMin('');
    setAmountMax('');
    setTimeout(() => loadOrders(1), 0);
  };

  useEffect(() => {
    let active = true;
    (async () => {
      const pairs = await Promise.all(
        orders.map(async (order) => {
          const id = String(order.id || '');
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

  return (
    <div className="container" style={{ marginTop: 30, marginBottom: 50 }}>
      <h1>All Sales Orders</h1>
      {message && <div className="alert alert-danger">{message}</div>}

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Filters</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, minmax(140px, 1fr))', gap: 10 }}>
          <div>
            <label>Order ID</label>
            <input
              value={orderId}
              onChange={e => setOrderId(e.target.value)}
              placeholder="Order ID"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
            />
          </div>
          <div>
            <label>Order Number</label>
            <input
              value={orderNumber}
              onChange={e => setOrderNumber(e.target.value)}
              placeholder="e.g. SO-2026"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
            />
          </div>
          <div>
            <label>Date From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
            />
          </div>
          <div>
            <label>Date To</label>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
            />
          </div>
          <div>
            <label>Amount Min</label>
            <input
              type="number"
              min={0}
              value={amountMin}
              onChange={e => setAmountMin(e.target.value)}
              placeholder="0"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
            />
          </div>
          <div>
            <label>Amount Max</label>
            <input
              type="number"
              min={0}
              value={amountMax}
              onChange={e => setAmountMax(e.target.value)}
              placeholder="0"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
            />
          </div>
        </div>

        <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
          <button className="btn btn-primary" onClick={onApplyFilters} disabled={loading}>Apply</button>
          <button className="btn btn-secondary" onClick={onResetFilters} disabled={loading}>Reset</button>
        </div>
      </div>

      <div className="card" style={{ overflowX: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <h3 style={{ margin: 0 }}>Sales Orders ({total})</h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <label>Page Size</label>
            <select
              value={pageSize}
              onChange={e => setPageSize(Number(e.target.value))}
              style={{ padding: '6px 10px', border: '1px solid #ddd', borderRadius: 4 }}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 30 }}>Loading orders...</div>
        ) : orders.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 30 }}>No orders found</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                <th style={{ padding: 8 }}>Order ID</th>
                <th style={{ padding: 8 }}>Order Number</th>
                <th style={{ padding: 8 }}>Date</th>
                <th style={{ padding: 8 }}>Amount</th>
                <th style={{ padding: 8 }}>Status</th>
                <th style={{ padding: 8 }}>Customer ID</th>
              </tr>
            </thead>
            <tbody>
              {orders.map(order => (
                <tr key={order.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: 8 }}>
                    <Link to={`/orders/${orderRouteTokens[order.id] || fallbackRouteParam(String(order.id))}`} style={{ textDecoration: 'underline' }}>
                      {order.id}
                    </Link>
                  </td>
                  <td style={{ padding: 8 }}>{order.order_number || '-'}</td>
                  <td style={{ padding: 8 }}>{order.created_at ? new Date(order.created_at).toLocaleString() : '-'}</td>
                  <td style={{ padding: 8 }}>{formatAmount(order.total)}</td>
                  <td style={{ padding: 8 }}>{order.status || '-'}</td>
                  <td style={{ padding: 8 }}>{order.customer_id || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
          <div>
            Page {page} of {totalPages}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn btn-secondary"
              onClick={() => loadOrders(page - 1)}
              disabled={loading || page <= 1}
            >
              Previous
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => loadOrders(page + 1)}
              disabled={loading || page >= totalPages}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
