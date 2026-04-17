import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { productService, Product } from '../services/productService';
import { cartService, savedProductService } from '../services/productService';
import { authService } from '../services/authService';
import { ProductCard } from '../components/ProductCard';
import { decryptRouteParamOrFallback } from '../utils/urlCrypto';

export const ProductDetailPage: React.FC = () => {
  const navigate = useNavigate();
  const { productId } = useParams<{ productId: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [similar, setSimilar] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const isAuth = authService.isAuthenticated();

  useEffect(() => {
    if (!productId) return;
    const load = async () => {
      setLoading(true);
      try {
        const resolvedProductId = await decryptRouteParamOrFallback(productId);
        const p = await productService.getProduct(resolvedProductId);
        setProduct(p);
        // Load similar products by same category
        if (p.category) {
          const all = await productService.getProducts(0, 6, p.category);
          setSimilar(all.filter((x: Product) => x.id !== p.id).slice(0, 4));
        }
      } catch {
        setMessage('Product not found');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [productId]);

  const handleAddToCart = async (pid: string, qty: number) => {
    if (!isAuth) { navigate('/login'); return; }
    try {
      await cartService.addToCart(pid, qty);
      setMessage('Added to cart!');
      setTimeout(() => setMessage(''), 3000);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to add to cart');
    }
  };

  const handleSaveForLater = async (pid: string) => {
    if (!isAuth) { navigate('/login'); return; }
    try {
      await savedProductService.saveProduct(pid);
      setMessage('Saved for later!');
      setTimeout(() => setMessage(''), 3000);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to save');
    }
  };

  if (loading) return <div className="container" style={{ padding: '50px', textAlign: 'center' }}>Loading...</div>;
  if (!product) return <div className="container" style={{ padding: '50px' }}><div className="alert alert-danger">{message || 'Product not found'}</div><Link to="/products" className="btn btn-primary" style={{ textDecoration: 'none' }}>Back to Products</Link></div>;

  const hasDiscount = !!product.discount && product.discount_value != null;
  const discountPercent = product.discount === 'Discount percentage' && product.discount_value != null
    ? Number(product.discount_value)
    : null;
  const discountInfo = hasDiscount
    ? product.discount === 'Discount percentage'
      ? `${Number(product.discount_value).toFixed(2)}%`
      : `₹${Number(product.discount_value).toFixed(2)}`
    : null;
  const discountLabel = product.discount === 'Discount percentage' ? 'Discount %' : 'Discount';
  const discountedPrice = discountPercent != null
    ? Math.max(0, product.sell_price - (product.sell_price * discountPercent) / 100)
    : product.sell_price;

  return (
    <div className="container" style={{ marginTop: '30px', marginBottom: '50px' }}>
      {message && <div className="alert alert-success">{message}</div>}

      <div style={{ marginBottom: '15px' }}>
        <Link to="/products" style={{ color: '#007bff', textDecoration: 'none' }}>&larr; Back to Products</Link>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginBottom: '40px' }}>
        {/* Left: Product image placeholder + basic info */}
        <div>
          <div style={{ backgroundColor: '#f0f0f0', borderRadius: '8px', height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '20px', fontSize: '80px', color: '#ccc' }}>
            &#128722;
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button onClick={() => handleAddToCart(product.id, 1)} className="btn btn-primary" style={{ flex: 1 }} disabled={product.stock_quantity === 0}>Add to Cart</button>
            <button onClick={() => handleSaveForLater(product.id)} className="btn btn-secondary" style={{ flex: 1 }}>Save for Later</button>
          </div>
        </div>

        {/* Right: Details */}
        <div>
          <h1 style={{ marginTop: 0, marginBottom: '10px' }}>{product.name}</h1>
          <span style={{ backgroundColor: '#e3f2fd', color: '#1976d2', padding: '4px 10px', borderRadius: '4px', fontSize: '13px' }}>
            Barcode: {product.barcode}
          </span>
          {product.category && (
            <span style={{ backgroundColor: '#fff3e0', color: '#e65100', padding: '4px 10px', borderRadius: '4px', fontSize: '13px', marginLeft: '8px' }}>
              {product.category}
            </span>
          )}

          <p style={{ marginTop: '15px', color: '#555', lineHeight: 1.6 }}>{product.description || 'No description available.'}</p>

          <div className="card" style={{ marginTop: '20px' }}>
            <h3 style={{ marginTop: 0 }}>Pricing</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <span>Sell Price:</span><strong>₹{product.sell_price.toFixed(2)}</strong>
              {hasDiscount && <span>{discountLabel}:</span>}
              {hasDiscount && <strong>{discountInfo}</strong>}
              <span style={{ fontWeight: 700, borderTop: '1px solid #ddd', paddingTop: '8px' }}>Total:</span>
              <strong style={{ fontSize: '20px', color: '#d32f2f', borderTop: '1px solid #ddd', paddingTop: '8px' }}>₹{discountedPrice.toFixed(2)}</strong>
            </div>
          </div>

          <div style={{ marginTop: '15px' }}>
            <span style={{
              backgroundColor: product.stock_quantity > 0 ? '#c8e6c9' : '#ffcdd2',
              color: product.stock_quantity > 0 ? '#2e7d32' : '#c62828',
              padding: '8px 14px', borderRadius: '4px', fontSize: '14px'
            }}>
              {product.stock_quantity > 0 ? `In Stock (${product.stock_quantity} available)` : 'Out of Stock'}
            </span>
          </div>
        </div>
      </div>

      {/* Specifications */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h2 style={{ marginTop: 0 }}>Specifications</h2>
        <table className="table" style={{ marginTop: '10px' }}>
          <tbody>
            <tr><td style={{ fontWeight: 600, width: '200px' }}>SKU</td><td>{product.sku}</td></tr>
            <tr><td style={{ fontWeight: 600 }}>Barcode</td><td>{product.barcode}</td></tr>
            <tr><td style={{ fontWeight: 600 }}>Category</td><td>{product.category || 'N/A'}</td></tr>
            <tr><td style={{ fontWeight: 600 }}>Manufacturer</td><td>Hatt Official</td></tr>
            <tr><td style={{ fontWeight: 600 }}>Validity</td><td>12 months from date of purchase</td></tr>
            {hasDiscount && (
              <tr><td style={{ fontWeight: 600 }}>{discountLabel}</td><td>{discountInfo}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Customer Reviews */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h2 style={{ marginTop: 0 }}>Customer Reviews</h2>
        <div style={{ color: '#666', padding: '20px', textAlign: 'center', border: '1px dashed #ddd', borderRadius: '8px' }}>
          <p style={{ fontSize: '16px', marginBottom: '5px' }}>No reviews yet</p>
          <p style={{ fontSize: '13px', color: '#999' }}>Be the first to review this product</p>
        </div>
      </div>

      {/* Similar Products */}
      {similar.length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          <h2>Similar Products</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '20px' }}>
            {similar.map(sp => (
              <ProductCard key={sp.id} product={sp} onAddToCart={handleAddToCart} onSaveForLater={handleSaveForLater} isAuthenticated={isAuth} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
