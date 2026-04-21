import React from 'react';
 

export const DashboardPage: React.FC = () => {
  const message = '';

  return (
    <div className="container" style={{ marginTop: '30px', marginBottom: '50px' }}>
      <h1>Public Dashboard</h1>
      <p>Latest products, special offers and marketing highlights.</p>

      <div style={{ display: 'grid', gap: '20px', marginBottom: '30px' }}>
        <section style={{ background: '#f9f9f9', border: '1px solid #ddd', borderRadius: '8px', padding: '20px' }}>
          <h2>Marketing Spotlight</h2>
          <ul>
            <li>Seasonal sale: up to 25% off on select categories.</li>
            <li>Free shipping for orders over $100.</li>
            <li>New arrivals added every week.</li>
          </ul>
        </section>

        <section style={{ background: '#f9f9f9', border: '1px solid #ddd', borderRadius: '8px', padding: '20px' }}>
          <h2>Trending Products</h2>
          <p>Our most popular products based on recent visits and orders.</p>
        </section>
      </div>

      {message && <div className="alert alert-danger">{message}</div>}

      <div className="card" style={{ background: '#f9f9f9', border: '1px solid #ddd' }}>
        <h3 style={{ marginTop: 0 }}>Discover Products</h3>
        <p style={{ marginBottom: '14px' }}>Browse our complete catalog from the Products page.</p>
        <a href="/products" className="btn btn-primary" style={{ textDecoration: 'none' }}>Go to Products</a>
      </div>
    </div>
  );
};
