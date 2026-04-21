import React from 'react';

export const AboutUsPage: React.FC = () => {
  return (
    <div className="container" style={{ marginTop: '30px', marginBottom: '50px', maxWidth: '800px' }}>
      <h1>About Hatt</h1>

      <section style={{ marginBottom: '30px' }}>
        <p style={{ fontSize: '16px', lineHeight: 1.7, color: '#444' }}>
          Hatt is your trusted online marketplace bringing quality products to your doorstep.
          We connect customers with a wide range of categories — from electronics and clothing
          to groceries and home essentials — all backed by transparent pricing that includes
          GST breakdowns on every product.
        </p>
      </section>

      <section style={{ marginBottom: '30px', padding: '20px', background: '#f9f9f9', borderRadius: '8px' }}>
        <h2>Our Mission</h2>
        <p style={{ color: '#555', lineHeight: 1.6 }}>
          To provide an honest, straightforward shopping experience where customers can see
          exactly what they pay for — including taxes — with reliable delivery and responsive
          customer support.
        </p>
      </section>

      <section style={{ marginBottom: '30px' }}>
        <h2>Why Shop With Us?</h2>
        <ul style={{ lineHeight: 2, color: '#555' }}>
          <li>Transparent pricing with GST clearly displayed on every product.</li>
          <li>Wide product catalogue spanning multiple categories.</li>
          <li>Multiple payment options: COD, Net Banking, UPI, and Card.</li>
          <li>Easy order tracking from your personal orders dashboard.</li>
          <li>Dedicated customer support available through our Contact page.</li>
        </ul>
      </section>

      <section style={{ padding: '20px', background: '#e8f5e9', borderRadius: '8px' }}>
        <h2>Get in Touch</h2>
        <p style={{ color: '#555' }}>
          Have questions or feedback? Visit our <a href="/contact">Contact Us</a> page or
          check the <a href="/faq">FAQ</a> for quick answers.
        </p>
      </section>
    </div>
  );
};
