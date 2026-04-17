import React from 'react';
import { CartItem } from '../services/cartOrderService';

interface Props {
  items: CartItem[];
  onRemove: (productId: string) => void;
}

export const CartItemTable: React.FC<Props> = ({ items, onRemove }) => (
  <>
    {/* Desktop: table view */}
    <div className="cart-items-desktop">
      <table className="table">
        <thead>
          <tr><th>Product</th><th>Quantity</th><th>Price</th><th>Total</th><th>Action</th></tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.product_id}>
              <td>
                <strong>{item.product_name || 'Unknown Product'}</strong>
                {item.product_spec && <div style={{ fontSize: '12px', color: '#666' }}>{item.product_spec}</div>}
              </td>
              <td>{item.quantity}</td>
              <td>&#x20B9;{item.price.toFixed(2)}</td>
              <td>&#x20B9;{item.total.toFixed(2)}</td>
              <td>
                <button onClick={() => onRemove(item.product_id)} className="btn btn-danger"
                  style={{ padding: '5px 10px', fontSize: '12px' }}>Remove</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    {/* Mobile: card view */}
    <div className="cart-items-mobile">
      {items.map((item) => (
        <div key={item.product_id} className="cart-item-card">
          <div className="cart-item-card-name">{item.product_name || 'Unknown Product'}</div>
          {item.product_spec && <div className="cart-item-card-spec">{item.product_spec}</div>}
          <div className="cart-item-card-row">
            <span>Qty:</span><span><strong>{item.quantity}</strong></span>
          </div>
          <div className="cart-item-card-row">
            <span>Unit Price:</span><span>&#x20B9;{item.price.toFixed(2)}</span>
          </div>
          <div className="cart-item-card-row" style={{ fontWeight: 600, marginBottom: '10px' }}>
            <span>Total:</span><span>&#x20B9;{item.total.toFixed(2)}</span>
          </div>
          <button onClick={() => onRemove(item.product_id)} className="btn btn-danger"
            style={{ width: '100%', fontSize: '13px' }}>Remove</button>
        </div>
      ))}
    </div>
  </>
);
