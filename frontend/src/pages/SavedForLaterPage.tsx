import React, { useEffect, useState } from 'react';
import { cartService, savedProductService } from '../services/productService';

interface SavedItem {
  saved_product: {
    id: string;
    product_id: string;
    saved_price: number;
    created_at: string;
  };
  product: {
    _id?: string;
    id?: string;
    name: string;
    stock_quantity: number;
    sell_price: number;
    discount?: 'Discount percentage' | 'Discount amount';
    discount_value?: number;
    description?: string;
  };
  available: boolean;
}

export const SavedForLaterPage: React.FC = () => {
  const [items, setItems] = useState<SavedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  const loadItems = async () => {
    try {
      setLoading(true);
      const data = await savedProductService.getSavedProducts();
      setItems(data || []);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to load saved items');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadItems();
  }, []);

  const handleRemove = async (productId: string) => {
    try {
      await savedProductService.removeSavedProduct(productId);
      setMessage('Removed from saved for later');
      await loadItems();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to remove item');
    }
  };

  const handleMoveToCart = async (item: SavedItem) => {
    if (!item.available) {
      setMessage('Item is currently out of stock');
      return;
    }

    try {
      await cartService.addToCart(item.saved_product.product_id, 1);
      await savedProductService.removeSavedProduct(item.saved_product.product_id);
      setMessage('Item moved to cart');
      await loadItems();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to move item to cart');
    }
  };

  return (
    <div className="container" style={{ marginTop: '30px', marginBottom: '50px' }}>
      <h1>Saved for Later</h1>
      <p style={{ color: '#666' }}>Keep items here and move them to your cart when you are ready.</p>
      {message && <div className="alert alert-info">{message}</div>}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>Loading saved items...</div>
      ) : items.length === 0 ? (
        <div className="card">
          <p>You do not have any saved items yet.</p>
          <a href="/products" className="btn btn-primary" style={{ textDecoration: 'none' }}>Browse Products</a>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '16px' }}>
          {items.map((item) => (
            <div key={item.saved_product.id} className="card" style={{ marginBottom: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'center' }}>
                <div>
                  {(() => {
                    const hasDiscount = !!item.product.discount && item.product.discount_value != null;
                    const discountLabel = item.product.discount === 'Discount percentage' ? 'Discount %' : 'Discount';
                    const discountInfo = item.product.discount === 'Discount percentage'
                      ? `${Number(item.product.discount_value).toFixed(2)}%`
                      : `₹${Number(item.product.discount_value).toFixed(2)}`;
                    return (
                      <>
                  <h3 style={{ margin: '0 0 8px 0' }}>{item.product.name}</h3>
                  <p style={{ margin: '0 0 6px 0', color: '#666' }}>{item.product.description || 'No description available'}</p>
                  <p style={{ margin: 0 }}>
                    Price: <strong>₹{item.product.sell_price.toFixed(2)}</strong> | Stock: {item.product.stock_quantity}
                  </p>
                  {hasDiscount && (
                    <p style={{ margin: '6px 0 0 0' }}>
                      {discountLabel}: <strong>{discountInfo}</strong>
                    </p>
                  )}
                  <p style={{ margin: '6px 0 0 0', color: item.available ? '#1e7e34' : '#c82333', fontWeight: 600 }}>
                    {item.available ? 'Available' : 'Out of stock'}
                  </p>
                      </>
                    );
                  })()}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', minWidth: '180px' }}>
                  <button
                    className="btn btn-success"
                    disabled={!item.available}
                    onClick={() => handleMoveToCart(item)}
                    style={{ opacity: item.available ? 1 : 0.6 }}
                  >
                    Move to Cart
                  </button>
                  <button className="btn btn-secondary" onClick={() => handleRemove(item.saved_product.product_id)}>
                    Remove
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
