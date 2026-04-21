import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer style={footerStyles}>
      <div className="container">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginBottom: '30px' }}>
          <div>
            <h4>Quick Links</h4>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              <li><a href="/dashboard">Dashboard</a></li>
              <li><a href="/products">Products</a></li>
              <li><a href="/contact">Contact Us</a></li>
            </ul>
          </div>
          <div>
            <h4>Customer Service</h4>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              <li><a href="/faq">FAQ</a></li>
              <li><a href="/returns">Returns</a></li>
            </ul>
          </div>
        </div>
        <div style={{ borderTop: '1px solid #ddd', paddingTop: '20px', textAlign: 'center' }}>
          <p>&copy; 2026 Hatt. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

const footerStyles: React.CSSProperties = {
  backgroundColor: '#f8f9fa',
  padding: '40px 0 20px',
  marginTop: '50px',
  borderTop: '1px solid #ddd',
};
