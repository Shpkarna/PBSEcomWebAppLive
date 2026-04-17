import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { productService, Product } from '../services/productService';
import { cartService } from '../services/productService';
import { savedProductService } from '../services/productService';
import { authService } from '../services/authService';
import { ProductCard } from '../components/ProductCard';
import { categoryService, CategoryRow } from '../services/categoryService';

type ProductSortOption = 'latest' | 'name_asc' | 'name_desc' | 'price_asc' | 'price_desc';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<CategoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState<string>('');
  const [sortBy, setSortBy] = useState<ProductSortOption>('latest');
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadProducts();
  }, [category, sortBy]);

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const data = await categoryService.list(0, 200);
        setCategories(data);
      } catch {
        // Category list is optional for browsing; products can still load.
      }
    };
    loadCategories();
  }, []);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const data = await productService.getProducts(0, 12, category || undefined, sortBy);
      setProducts(data);
    } catch (err) {
      setMessage('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = async (productId: string, quantity: number) => {
    if (!authService.isAuthenticated()) {
      navigate('/login');
      return;
    }
    try {
      await cartService.addToCart(productId, quantity);
      setMessage('Product added to cart!');
      setTimeout(() => setMessage(''), 3000);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to add to cart');
    }
  };

  const handleSaveForLater = async (productId: string) => {
    if (!authService.isAuthenticated()) {
      navigate('/login');
      return;
    }
    try {
      await savedProductService.saveProduct(productId);
      setMessage('Product saved for later!');
      setTimeout(() => setMessage(''), 3000);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to save product');
    }
  };

  return (
    <div className="container" style={{ marginTop: '30px', marginBottom: '50px' }}>
      {message && <div className="alert alert-success">{message}</div>}

      <div style={{ marginBottom: '30px' }}>
        <h1>Welcome to Hatt</h1>
        <p>Browse our collection of products</p>
      </div>

      <div style={{ marginBottom: '30px', display: 'flex', gap: '10px' }}>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          style={{ flex: 1, padding: '10px', border: '1px solid #ddd', borderRadius: '4px' }}
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat.id} value={cat.name}>{cat.name}</option>
          ))}
        </select>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as ProductSortOption)}
          style={{ width: '220px', padding: '10px', border: '1px solid #ddd', borderRadius: '4px' }}
        >
          <option value="latest">Sort: Latest</option>
          <option value="name_asc">Sort: Name (A-Z)</option>
          <option value="name_desc">Sort: Name (Z-A)</option>
          <option value="price_asc">Sort: Price (Low-High)</option>
          <option value="price_desc">Sort: Price (High-Low)</option>
        </select>
        <button onClick={loadProducts} className="btn btn-primary">Search</button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>Loading products...</div>
      ) : products.length === 0 ? (
        <div className="alert alert-info">No products found</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '20px' }}>
          {products.map(product => (
            <ProductCard
              key={product.id}
              product={product}
              onAddToCart={handleAddToCart}
              onSaveForLater={handleSaveForLater}
              isAuthenticated={authService.isAuthenticated()}
            />
          ))}
        </div>
      )}
    </div>
  );
};
