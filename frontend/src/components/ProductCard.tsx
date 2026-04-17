import React, { useEffect, useState } from 'react';
import { getProductMediaFileUrl } from '../services/productService';
import { encryptRouteParam, fallbackRouteParam } from '../utils/urlCrypto';

interface ProductCardProps {
  product: {
    id: string;
    name: string;
    sell_price: number;
    stock_quantity: number;
    discount?: 'Discount percentage' | 'Discount amount';
    discount_value?: number;
    image_media_ids?: string[];
    description?: string;
  };
  onAddToCart: (productId: string, quantity: number) => void;
  onSaveForLater: (productId: string) => void;
  isAuthenticated?: boolean;
}

export const ProductCard: React.FC<ProductCardProps> = ({ 
  product, 
  onAddToCart, 
  onSaveForLater,
  isAuthenticated 
}) => {
  const [quantity, setQuantity] = useState(1);
  const [shareMsg, setShareMsg] = useState('');
  const [productRouteToken, setProductRouteToken] = useState(fallbackRouteParam(product.id));
  const hasDiscount = !!product.discount && product.discount_value != null;
  const discountValueNum = Number(product.discount_value || 0);
  const rawDiscountAmount = hasDiscount
    ? product.discount === 'Discount percentage'
      ? (product.sell_price * discountValueNum) / 100
      : discountValueNum
    : 0;
  const appliedDiscountAmount = Math.max(0, Math.min(product.sell_price, rawDiscountAmount));
  const displayPrice = Math.max(0, product.sell_price - appliedDiscountAmount);
  const discountInfo = hasDiscount
    ? product.discount === 'Discount percentage'
      ? `${discountValueNum.toFixed(2)}%`
      : `₹${discountValueNum.toFixed(2)}`
    : null;
  const discountLabel = product.discount === 'Discount percentage' ? 'Discount %' : 'Discount';
  const thumbnailUrl = product.image_media_ids && product.image_media_ids.length > 0
    ? getProductMediaFileUrl(product.image_media_ids[0])
    : '';

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const token = await encryptRouteParam(product.id);
        if (active) setProductRouteToken(token);
      } catch {
        if (active) setProductRouteToken(fallbackRouteParam(product.id));
      }
    })();
    return () => {
      active = false;
    };
  }, [product.id]);

  const handleAddToCart = () => {
    onAddToCart(product.id, quantity);
    setQuantity(1);
  };

  const handleShare = async () => {
    const token = productRouteToken || fallbackRouteParam(product.id);
    const productUrl = `${window.location.origin}/products/${token}`;
    const shareData = { title: product.name, text: `Check out ${product.name} on Hatt!`, url: productUrl };
    if (navigator.share) {
      try { await navigator.share(shareData); } catch { /* cancelled */ }
    } else {
      try {
        await navigator.clipboard.writeText(productUrl);
        setShareMsg('Link copied!');
        setTimeout(() => setShareMsg(''), 2000);
      } catch { setShareMsg('Copy failed'); }
    }
  };

  return (
    <div style={cardStyles}>
      <div style={{ marginBottom: '12px' }}>
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={product.name}
            style={{ width: '100%', height: 160, objectFit: 'cover', borderRadius: 8, background: '#f4f4f4' }}
          />
        ) : (
          <div style={{ height: 160, borderRadius: 8, background: '#f0f0f0', color: '#bbb', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 54 }}>
            &#128722;
          </div>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '10px' }}>
        <a href={`/products/${productRouteToken}`} style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#333', textDecoration: 'none' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = '#007bff')}
          onMouseLeave={(e) => (e.currentTarget.style.color = '#333')}>
          {product.name}
        </a>
      </div>
      
      <p style={{ color: '#666', marginTop: '8px', marginBottom: '8px' }}>{product.description}</p>
      
      <div style={{ marginBottom: '15px' }}>
        {hasDiscount && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
            <span>{discountLabel}:</span><strong>{discountInfo}</strong>
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #ddd', paddingTop: '5px', marginTop: '5px' }}>
          <span style={{ fontWeight: 'bold' }}>Price:</span>
          <strong style={{ fontSize: '18px', color: '#d32f2f' }}>₹{displayPrice.toFixed(2)}</strong>
        </div>
      </div>

      <div style={{ marginBottom: '15px' }}>
        <span style={{ 
          backgroundColor: product.stock_quantity > 0 ? '#c8e6c9' : '#ffcdd2',
          color: product.stock_quantity > 0 ? '#2e7d32' : '#c62828',
          padding: '8px 12px',
          borderRadius: '4px',
          fontSize: '14px'
        }}>
          {product.stock_quantity > 0 ? `In Stock (${product.stock_quantity})` : 'Out of Stock'}
        </span>
      </div>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
        <input
          type="number"
          min="1"
          max={Math.min(5, product.stock_quantity)}
          value={quantity}
          onChange={(e) => setQuantity(Math.min(5, Math.max(1, parseInt(e.target.value) || 1)))}
          style={{ width: '60px', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
          title="Max 5 per product"
        />
        <button
          onClick={handleAddToCart}
          disabled={product.stock_quantity === 0}
          className="btn btn-primary"
          style={{ flex: 1, opacity: product.stock_quantity === 0 ? 0.6 : 1, cursor: product.stock_quantity === 0 ? 'not-allowed' : 'pointer' }}
        >
          Add to Cart
        </button>
      </div>

      <button
        onClick={() => onSaveForLater(product.id)}
        className="btn btn-secondary"
        style={{ width: '100%' }}
      >
        Save for Later
      </button>

      {isAuthenticated && (
        <div style={{ marginTop: '10px', textAlign: 'center' }}>
          <button onClick={handleShare} className="btn" style={{ width: '100%', backgroundColor: '#17a2b8', color: '#fff', fontSize: '13px' }}>
            &#128279; Share Product
          </button>
          {shareMsg && <small style={{ color: '#28a745' }}>{shareMsg}</small>}
        </div>
      )}
    </div>
  );
};

const cardStyles: React.CSSProperties = {
  backgroundColor: '#fff', border: '1px solid #ddd', borderRadius: '8px',
  padding: '15px', transition: 'box-shadow 0.3s', cursor: 'pointer',
};
