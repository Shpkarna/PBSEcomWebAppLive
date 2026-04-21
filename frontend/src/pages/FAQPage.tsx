import React from 'react';

const faqs = [
  { q: 'How do I create an account?', a: 'Click the "Register" button in the top-right corner, fill in your details, and submit the form. You will be logged in automatically.' },
  { q: 'How do I place an order?', a: 'Browse products on the Home page, add items to your cart, then proceed to Checkout. Choose a payment method, enter your shipping address, and confirm the order.' },
  { q: 'What payment methods are accepted?', a: 'We accept Cash, Cash on Delivery (COD), Net Banking, UPI, and Card payments.' },
  { q: 'How can I track my order?', a: 'Go to the "Orders" page from the navigation bar. You will see the status of all your orders (pending, confirmed, processing, shipped, delivered).' },
  { q: 'Can I cancel an order?', a: 'Please contact our support team through the Contact Us page for cancellation requests. Orders that have already shipped cannot be cancelled.' },
  { q: 'What is "Save for Later"?', a: 'When you are logged in, you can save products to review later. Saved products appear under your profile and can be moved to the cart at any time.' },
  { q: 'How do I return a product?', a: 'Navigate to your Orders page, find the delivered order, and initiate a return. Returned orders can be viewed on the Returns page.' },
  { q: 'Is GST included in the product price?', a: 'GST is calculated separately and shown on each product card. The final price displayed includes the applicable GST.' },
];

export const FAQPage: React.FC = () => {
  return (
    <div className="container" style={{ marginTop: '30px', marginBottom: '50px', maxWidth: '800px' }}>
      <h1>Frequently Asked Questions</h1>
      <p style={{ color: '#666', marginBottom: '30px' }}>Find answers to common questions about using Hatt.</p>

      {faqs.map((faq, i) => (
        <details key={i} style={{ marginBottom: '12px', border: '1px solid #ddd', borderRadius: '6px', padding: '14px 18px', background: '#fafafa' }}>
          <summary style={{ fontWeight: 600, cursor: 'pointer', fontSize: '15px' }}>{faq.q}</summary>
          <p style={{ marginTop: '10px', color: '#555', lineHeight: 1.6 }}>{faq.a}</p>
        </details>
      ))}

      <div style={{ marginTop: '30px', padding: '20px', background: '#e3f2fd', borderRadius: '8px' }}>
        <p style={{ margin: 0 }}>
          Didn't find what you were looking for? <a href="/contact">Contact our support team</a>.
        </p>
      </div>
    </div>
  );
};
