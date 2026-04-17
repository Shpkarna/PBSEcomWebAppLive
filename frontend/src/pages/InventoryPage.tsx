import React, { useEffect, useState } from 'react';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { productService, Product } from '../services/productService';
import { stockService } from '../services/stockService';
import { categoryService } from '../services/categoryService';

const LOW_STOCK_THRESHOLD = 10;

export const InventoryPage: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [stockEntries, setStockEntries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // Filters
  const [filterCategory, setFilterCategory] = useState('');
  const [filterStockStatus, setFilterStockStatus] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Batch stock update
  const [batchProduct, setBatchProduct] = useState('');
  const [batchType, setBatchType] = useState('inbound');
  const [batchQty, setBatchQty] = useState(1);
  const [batchRef, setBatchRef] = useState('');
  const [batchNotes, setBatchNotes] = useState('');

  // Selected product detail
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [productLedger, setProductLedger] = useState<any[]>([]);

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      setLoading(true);
      const [prods, cats] = await Promise.all([
        productService.getProducts(0, 500),
        categoryService.list(),
      ]);
      setProducts(prods);
      setCategories(cats);
    } catch {
      setError('Failed to load inventory data');
    } finally {
      setLoading(false);
    }
  };

  const loadProductLedger = async (productId: string) => {
    try {
      const entries = await stockService.list(productId);
      setProductLedger(entries);
    } catch {}
  };

  const handleBatchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(''); setError('');
    try {
      await stockService.addEntry({
        product_id: batchProduct,
        transaction_type: batchType,
        quantity: batchQty,
        reference: batchRef || undefined,
        notes: batchNotes || undefined,
      });
      setMessage('Stock entry added successfully');
      setBatchProduct(''); setBatchQty(1); setBatchRef(''); setBatchNotes('');
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to add stock entry');
    }
  };

  const selectProduct = (p: Product) => {
    setSelectedProduct(p);
    loadProductLedger(p.id);
  };

  // Filtered products
  const filtered = products.filter(p => {
    if (filterCategory && p.category !== filterCategory) return false;
    if (filterStockStatus === 'low' && p.stock_quantity >= LOW_STOCK_THRESHOLD) return false;
    if (filterStockStatus === 'out' && p.stock_quantity > 0) return false;
    if (filterStockStatus === 'in' && p.stock_quantity <= 0) return false;
    if (searchTerm && !p.name.toLowerCase().includes(searchTerm.toLowerCase()) && !p.sku.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  // Stats
  const totalProducts = products.length;
  const totalStockValue = products.reduce((a, p) => a + p.stock_price * p.stock_quantity, 0);
  const totalSellValue = products.reduce((a, p) => a + p.sell_price * p.stock_quantity, 0);
  const lowStockCount = products.filter(p => p.stock_quantity > 0 && p.stock_quantity < LOW_STOCK_THRESHOLD).length;
  const outOfStockCount = products.filter(p => p.stock_quantity <= 0).length;

  if (loading) return <div style={{ textAlign: 'center', padding: 50 }}>Loading inventory...</div>;

  return (
    <ProtectedRoute requiredFunctionality="inventory_manage">
      <div className="container" style={{ marginTop: 30, marginBottom: 50 }}>
        <h1>Inventory Management</h1>

        {message && <div className="alert alert-success">{message}</div>}
        {error && <div className="alert alert-danger">{error}</div>}

        {/* Summary Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 16, marginBottom: 24 }}>
          <div className="card" style={{ backgroundColor: '#e3f2fd', textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#1565c0' }}>{totalProducts}</div>
            <div style={{ fontSize: 13, color: '#555' }}>Total Products</div>
          </div>
          <div className="card" style={{ backgroundColor: '#e8f5e9', textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2e7d32' }}>₹{totalStockValue.toFixed(0)}</div>
            <div style={{ fontSize: 13, color: '#555' }}>Stock Value (Cost)</div>
          </div>
          <div className="card" style={{ backgroundColor: '#f3e5f5', textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#7b1fa2' }}>₹{totalSellValue.toFixed(0)}</div>
            <div style={{ fontSize: 13, color: '#555' }}>Retail Value</div>
          </div>
          <div className="card" style={{ backgroundColor: '#fff3e0', textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#e65100' }}>{lowStockCount}</div>
            <div style={{ fontSize: 13, color: '#555' }}>Low Stock (&lt;{LOW_STOCK_THRESHOLD})</div>
          </div>
          <div className="card" style={{ backgroundColor: '#ffebee', textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#c62828' }}>{outOfStockCount}</div>
            <div style={{ fontSize: 13, color: '#555' }}>Out of Stock</div>
          </div>
        </div>

        {/* Quick Stock Entry */}
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginTop: 0 }}>Quick Stock Entry</h3>
          <form onSubmit={handleBatchSubmit} style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600 }}>Product</label>
              <select value={batchProduct} onChange={e => setBatchProduct(e.target.value)} required
                style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4, minWidth: 200 }}>
                <option value="">Select...</option>
                {products.map(p => <option key={p.id} value={p.id}>{p.name} ({p.stock_quantity})</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600 }}>Type</label>
              <select value={batchType} onChange={e => setBatchType(e.target.value)}
                style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4 }}>
                <option value="inbound">Inbound</option><option value="outbound">Outbound</option><option value="adjustment">Adjustment</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600 }}>Qty</label>
              <input type="number" value={batchQty} onChange={e => setBatchQty(Number(e.target.value))}
                min={1} required style={{ padding: 8, width: 80, border: '1px solid #ddd', borderRadius: 4 }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600 }}>Reference</label>
              <input value={batchRef} onChange={e => setBatchRef(e.target.value)}
                placeholder="PO#, Invoice#" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4 }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600 }}>Notes</label>
              <input value={batchNotes} onChange={e => setBatchNotes(e.target.value)}
                placeholder="Optional" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4 }} />
            </div>
            <button className="btn btn-primary" type="submit" style={{ padding: '8px 20px' }}>Add</button>
          </form>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <input placeholder="Search by name or SKU..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
            style={{ flex: 1, minWidth: 200, padding: 8, border: '1px solid #ddd', borderRadius: 4 }} />
          <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)}
            style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4 }}>
            <option value="">All Categories</option>
            {categories.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
          </select>
          <select value={filterStockStatus} onChange={e => setFilterStockStatus(e.target.value)}
            style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4 }}>
            <option value="">All Stock Levels</option>
            <option value="in">In Stock</option>
            <option value="low">Low Stock</option>
            <option value="out">Out of Stock</option>
          </select>
          <button className="btn btn-secondary" onClick={load} style={{ padding: '8px 16px' }}>Refresh</button>
        </div>

        {/* Low Stock Alerts */}
        {products.filter(p => p.stock_quantity > 0 && p.stock_quantity < LOW_STOCK_THRESHOLD).length > 0 && (
          <div className="card" style={{ marginBottom: 16, backgroundColor: '#fff3e0', borderLeft: '4px solid #e65100' }}>
            <h4 style={{ marginTop: 0, color: '#e65100' }}>⚠ Low Stock Alerts</h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {products.filter(p => p.stock_quantity > 0 && p.stock_quantity < LOW_STOCK_THRESHOLD).map(p => (
                <span key={p.id} style={{ backgroundColor: '#ffe0b2', padding: '4px 12px', borderRadius: 4, fontSize: 13, cursor: 'pointer' }}
                  onClick={() => selectProduct(p)}>
                  {p.name}: <strong>{p.stock_quantity}</strong> left
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Inventory Table */}
        <div className="card" style={{ overflowX: 'auto', marginBottom: 20 }}>
          <h3 style={{ margin: 0, marginBottom: 12 }}>Products ({filtered.length})</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                <th style={{ padding: 8 }}>Name</th>
                <th style={{ padding: 8 }}>SKU</th>
                <th style={{ padding: 8 }}>Category</th>
                <th style={{ padding: 8 }}>Stock Qty</th>
                <th style={{ padding: 8 }}>Cost Price</th>
                <th style={{ padding: 8 }}>Sell Price</th>
                <th style={{ padding: 8 }}>Stock Value</th>
                <th style={{ padding: 8 }}>Status</th>
                <th style={{ padding: 8 }}>Details</th>
              </tr>
            </thead>
            <tbody>{filtered.map(p => {
              const stockStatus = p.stock_quantity <= 0 ? 'Out' : p.stock_quantity < LOW_STOCK_THRESHOLD ? 'Low' : 'OK';
              const statusColor = stockStatus === 'Out' ? '#f44336' : stockStatus === 'Low' ? '#ff9800' : '#4caf50';
              return (
                <tr key={p.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: 8, fontWeight: 500 }}>{p.name}</td>
                  <td style={{ padding: 8, fontSize: 12, color: '#666' }}>{p.sku}</td>
                  <td style={{ padding: 8 }}>{p.category || '-'}</td>
                  <td style={{ padding: 8, fontWeight: 600 }}>{p.stock_quantity}</td>
                  <td style={{ padding: 8 }}>₹{p.stock_price.toFixed(2)}</td>
                  <td style={{ padding: 8 }}>₹{p.sell_price.toFixed(2)}</td>
                  <td style={{ padding: 8 }}>₹{(p.stock_price * p.stock_quantity).toFixed(2)}</td>
                  <td style={{ padding: 8 }}>
                    <span style={{ backgroundColor: statusColor, color: '#fff', padding: '2px 8px', borderRadius: 4, fontSize: 11 }}>{stockStatus}</span>
                  </td>
                  <td style={{ padding: 8 }}>
                    <button className="btn btn-secondary" style={{ padding: '3px 8px', fontSize: 12 }} onClick={() => selectProduct(p)}>View</button>
                  </td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>

        {/* Product Detail Sidebar */}
        {selectedProduct && (
          <div className="card" style={{ marginBottom: 20, borderLeft: '4px solid #1565c0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ marginTop: 0 }}>{selectedProduct.name} — Stock History</h3>
              <button className="btn btn-secondary" style={{ padding: '4px 10px' }} onClick={() => setSelectedProduct(null)}>Close</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 12 }}>
              <div><strong>SKU:</strong> {selectedProduct.sku}</div>
              <div><strong>Barcode:</strong> {selectedProduct.barcode}</div>
              <div><strong>Current Stock:</strong> {selectedProduct.stock_quantity}</div>
              <div><strong>Cost Price:</strong> ₹{selectedProduct.stock_price}</div>
              <div><strong>Sell Price:</strong> ₹{selectedProduct.sell_price}</div>
              <div><strong>GST Rate:</strong> {(selectedProduct.gst_rate * 100).toFixed(0)}%</div>
            </div>
            {productLedger.length === 0 ? (
              <p style={{ color: '#666' }}>No stock movement history found.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                    <th style={{ padding: 6 }}>Type</th><th style={{ padding: 6 }}>Qty</th>
                    <th style={{ padding: 6 }}>Stock After</th><th style={{ padding: 6 }}>Reference</th>
                    <th style={{ padding: 6 }}>Date</th>
                  </tr>
                </thead>
                <tbody>{productLedger.map((e: any) => (
                  <tr key={e.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: 6 }}>
                      <span style={{
                        backgroundColor: e.transaction_type === 'inbound' ? '#4caf50' : e.transaction_type === 'outbound' ? '#f44336' : '#ff9800',
                        color: '#fff', padding: '1px 6px', borderRadius: 4, fontSize: 11,
                      }}>{e.transaction_type}</span>
                    </td>
                    <td style={{ padding: 6 }}>{e.quantity}</td>
                    <td style={{ padding: 6 }}>{e.adjusted_quantity ?? '-'}</td>
                    <td style={{ padding: 6 }}>{e.reference || '-'}</td>
                    <td style={{ padding: 6, fontSize: 11 }}>{new Date(e.created_at).toLocaleString()}</td>
                  </tr>
                ))}</tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
};
