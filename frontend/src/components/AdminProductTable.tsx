import React, { useMemo, useState } from 'react';
import { Product } from '../services/productService';

interface Props {
  products: Product[];
  loading: boolean;
  isAdmin: boolean;
  page: number;
  pageSize: number;
  canNextPage: boolean;
  onRefresh: () => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onEdit: (product: Product) => void;
  onDelete: (product: Product) => void;
}

export const AdminProductTable: React.FC<Props> = ({
  products,
  loading,
  isAdmin,
  page,
  pageSize,
  canNextPage,
  onRefresh,
  onPageChange,
  onPageSizeChange,
  onEdit,
  onDelete,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredProducts = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) return products;
    return products.filter((product) => (
      product.name.toLowerCase().includes(query)
      || product.sku.toLowerCase().includes(query)
      || (product.category || '').toLowerCase().includes(query)
    ));
  }, [products, searchTerm]);

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', gap: 10, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0 }}>Product Catalog ({filteredProducts.length})</h3>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Search by name, SKU, or category"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ minWidth: 260, padding: '7px 9px', border: '1px solid #ddd', borderRadius: 4 }}
          />
          <button className="btn btn-secondary" onClick={onRefresh} disabled={loading}>Refresh</button>
        </div>
      </div>
      {loading ? (
        <div style={{ textAlign: 'center', padding: '25px' }}>Loading products...</div>
      ) : products.length === 0 ? (
        <div className="alert alert-info" style={{ margin: 0 }}>No products available. Create your first product above.</div>
      ) : (
        <>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th><th>SKU</th><th>Category</th><th>Stock</th>
                  <th>GST</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((product) => (
                  <tr key={product.id}>
                    <td>{product.name}</td>
                    <td>{product.sku}</td>
                    <td>{product.category || '-'}</td>
                    <td>{product.stock_quantity}</td>
                    <td>{(product.gst_rate * 100).toFixed(0)}%</td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <button className="btn btn-primary" style={{ padding: '6px 10px' }} onClick={() => onEdit(product)}>Edit</button>
                        {isAdmin && (
                          <button className="btn btn-danger" style={{ padding: '6px 10px' }} onClick={() => void onDelete(product)}>Delete</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, gap: 12, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <label htmlFor="product-page-size">Rows per page</label>
              <select
                id="product-page-size"
                value={pageSize}
                onChange={(e) => onPageSizeChange(Number(e.target.value))}
                disabled={loading}
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={20}>20</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button className="btn btn-secondary" onClick={() => onPageChange(page - 1)} disabled={loading || page <= 1}>Previous</button>
              <span>Page {page}</span>
              <button className="btn btn-secondary" onClick={() => onPageChange(page + 1)} disabled={loading || !canNextPage}>Next</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
