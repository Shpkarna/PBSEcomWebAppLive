import React, { useEffect, useState } from 'react';
import { cartService, CartResponse } from '../services/productService';
import { CartItemTable } from '../components/CartItemTable';

interface CartPageProps { onCheckout: () => void; }

export const CartPage: React.FC<CartPageProps> = ({ onCheckout }) => {
  const [cart, setCart] = useState<CartResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  useEffect(() => { loadCart(); }, []);

  const loadCart = async () => {
    try { setLoading(true); setCart(await cartService.getCart()); }
    catch (err: any) {
      // If session expired the 401 interceptor redirects to login;
      // show empty cart gracefully instead of an error flash.
      if (err?.response?.status === 401) {
        setCart(null);
      } else {
        setMessage('Failed to load cart');
      }
    }
    finally { setLoading(false); }
  };

  const handleRemoveItem = async (productId: string) => {
    try { await cartService.removeFromCart(productId); setMessage('Item removed from cart'); loadCart(); }
    catch { setMessage('Failed to remove item'); }
  };

  const handleClearCart = async () => {
    if (!window.confirm('Are you sure you want to empty the cart?')) return;
    try { await cartService.clearCart(); setMessage('Cart cleared'); loadCart(); }
    catch { setMessage('Failed to clear cart'); }
  };

  const R = '\u20B9';
  return (
    <div className="container" style={{ marginTop: '30px', marginBottom: '50px' }}>
      {message && <div className="alert alert-success">{message}</div>}
      <h1>Shopping Cart</h1>
      {loading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>Loading cart...</div>
      ) : !cart || cart.items.length === 0 ? (
        <div className="card"><p>Your cart is empty</p>
          <a href="/products" className="btn btn-primary">Continue Shopping</a></div>
      ) : (
        <div className="cart-layout">
          <div>
            <CartItemTable items={cart.items} onRemove={handleRemoveItem} />
            <button onClick={handleClearCart} className="btn btn-secondary" style={{ marginTop: '15px' }}>Clear Cart</button>
          </div>
          <div className="card">
            <div className="card-title">Order Summary</div>
            <div style={{ marginBottom: '15px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span>Subtotal:</span><strong>{R}{cart.subtotal.toFixed(2)}</strong></div>
              {(cart.total_discount || 0) > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <span>Discount:</span><strong style={{ color: '#2e7d32' }}>- {R}{(cart.total_discount || 0).toFixed(2)}</strong>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span>GST:</span><strong>{R}{cart.total_gst.toFixed(2)}</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderTop: '1px solid #ddd', borderBottom: '1px solid #ddd', fontSize: '18px' }}>
                <span>Total:</span><strong style={{ color: '#d32f2f' }}>{R}{cart.total.toFixed(2)}</strong></div>
            </div>
            <button className="btn btn-primary" style={{ width: '100%' }} onClick={onCheckout}>Proceed to Checkout</button>
          </div>
        </div>
      )}
    </div>
  );
};
