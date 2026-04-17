import React, { useEffect, useState } from 'react';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { stockService } from '../services/stockService';
import { productService } from '../services/productService';

export const StockLedgerPage: React.FC = () => {
  const [entries, setEntries] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [productMap, setProductMap] = useState<Record<string, string>>({});
  const [form, setForm] = useState({ product_id: '', transaction_type: 'inbound', quantity: 1, reference: '', notes: '' });
  const [message, setMessage] = useState('');
  const [filterProduct, setFilterProduct] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const load = async () => {
    try {
      const [ledgerRows, productRows] = await Promise.all([
        stockService.list(filterProduct || undefined), productService.getProducts(0, 200),
      ]);
      setEntries(ledgerRows);
      setProducts(productRows);
      const map: Record<string, string> = {};
      productRows.forEach((p: any) => { map[p.id || p._id] = p.name; });
      setProductMap(map);
    } catch { setMessage('Failed to load stock data'); }
  };

  useEffect(() => { load(); }, [filterProduct]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await stockService.addEntry(form);
      setForm({ product_id: '', transaction_type: 'inbound', quantity: 1, reference: '', notes: '' });
      setMessage('Stock entry added successfully');
      await load();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to add stock entry');
    }
  };

  const getTypeColor = (t: string) => {
    if (t === 'inbound') return '#4caf50';
    if (t === 'outbound') return '#f44336';
    return '#ff9800';
  };

  const normalizedSearch = searchTerm.trim().toLowerCase();
  const filteredEntries = entries.filter((e: any) => {
    if (!normalizedSearch) return true;
    const productName = (productMap[e.product_id] || e.product_id || '').toLowerCase();
    return (
      productName.includes(normalizedSearch)
      || (e.transaction_type || '').toLowerCase().includes(normalizedSearch)
      || (e.reference || '').toLowerCase().includes(normalizedSearch)
      || (e.created_by || '').toLowerCase().includes(normalizedSearch)
    );
  });

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="container" style={{ marginTop: 30, marginBottom: 50 }}>
        <h1>Stock Ledger</h1>
        {message && <div className="alert alert-info">{message}</div>}
        <form className="card" onSubmit={submit} style={{ marginBottom: 20 }}>
          <h3 style={{ marginTop: 0 }}>Add Stock Entry</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Product</label>
              <select style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                value={form.product_id} onChange={e => setForm({ ...form, product_id: e.target.value })} required>
                <option value="">Select Product</option>
                {products.map((p: any) => <option key={p._id || p.id} value={p._id || p.id}>{p.name} (Stock: {p.stock_quantity})</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Type</label>
              <select style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                value={form.transaction_type} onChange={e => setForm({ ...form, transaction_type: e.target.value })}>
                <option value="inbound">Inbound</option><option value="outbound">Outbound</option><option value="adjustment">Adjustment</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Quantity</label>
              <input type="number" style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                value={form.quantity} onChange={e => setForm({ ...form, quantity: Number(e.target.value) })} required />
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Reference</label>
              <input style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                placeholder="Reference" value={form.reference} onChange={e => setForm({ ...form, reference: e.target.value })} />
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Notes</label>
            <input style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
              placeholder="Notes" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
          </div>
          <button className="btn btn-primary" type="submit" style={{ marginTop: 12 }}>Add Entry</button>
        </form>

        <div className="card" style={{ overflowX: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Ledger Entries ({filteredEntries.length})</h3>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                type="text"
                placeholder="Search product, type, reference, or user"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ padding: '4px 8px', border: '1px solid #ddd', borderRadius: 4, minWidth: 280 }}
              />
              <label style={{ fontWeight: 600, fontSize: 13 }}>Filter:</label>
              <select value={filterProduct} onChange={e => setFilterProduct(e.target.value)}
                style={{ padding: '4px 8px', border: '1px solid #ddd', borderRadius: 4 }}>
                <option value="">All Products</option>
                {products.map((p: any) => <option key={p._id || p.id} value={p._id || p.id}>{p.name}</option>)}
              </select>
            </div>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                <th style={{ padding: 8 }}>Product</th><th style={{ padding: 8 }}>Type</th>
                <th style={{ padding: 8 }}>Qty</th><th style={{ padding: 8 }}>Stock After</th>
                <th style={{ padding: 8 }}>Reference</th><th style={{ padding: 8 }}>By</th>
                <th style={{ padding: 8 }}>Time</th>
              </tr>
            </thead>
            <tbody>{filteredEntries.map((e: any) => (
              <tr key={e.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 8 }}>{productMap[e.product_id] || e.product_id}</td>
                <td style={{ padding: 8 }}>
                  <span style={{ backgroundColor: getTypeColor(e.transaction_type), color: '#fff', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>
                    {e.transaction_type}
                  </span>
                </td>
                <td style={{ padding: 8 }}>{e.quantity}</td>
                <td style={{ padding: 8 }}>{e.adjusted_quantity ?? '-'}</td>
                <td style={{ padding: 8 }}>{e.reference || '-'}</td>
                <td style={{ padding: 8 }}>{e.created_by || '-'}</td>
                <td style={{ padding: 8, fontSize: 12 }}>{new Date(e.created_at).toLocaleString()}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </ProtectedRoute>
  );
};
