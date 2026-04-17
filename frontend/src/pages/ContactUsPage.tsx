import React, { useState } from 'react';
import { contactService } from '../services/contactService';

export const ContactUsPage: React.FC = () => {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await contactService.submit(form);
      setSubmitted(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit inquiry. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ marginTop: '30px', marginBottom: '50px', maxWidth: '700px' }}>
      <h1>Contact Us</h1>
      <p style={{ color: '#666', marginBottom: '30px' }}>
        Have a question or need help? Fill out the form below and our team will get back to you.
      </p>

      {submitted ? (
        <div className="alert alert-success">
          Thank you for reaching out! We will respond within 24–48 hours.
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          {error && <div className="alert alert-danger">{error}</div>}
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: '5px' }}>Name</label>
            <input name="name" value={form.name} onChange={handleChange} required
              style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px' }} />
          </div>
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: '5px' }}>Email</label>
            <input name="email" type="email" value={form.email} onChange={handleChange} required
              style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px' }} />
          </div>
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: '5px' }}>Subject</label>
            <input name="subject" value={form.subject} onChange={handleChange} required
              style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px' }} />
          </div>
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: '5px' }}>Message</label>
            <textarea name="message" value={form.message} onChange={handleChange} required rows={5}
              style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px', resize: 'vertical' }} />
          </div>
          <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Sending...' : 'Send Message'}
          </button>
        </form>
      )}

      <div style={{ marginTop: '40px', padding: '20px', background: '#f9f9f9', borderRadius: '8px' }}>
        <h3>Other Ways to Reach Us</h3>
        <p>Email: <a href="mailto:support@hatt.com">support@hatt.com</a></p>
        <p>Business hours: Mon – Fri, 9 AM – 6 PM IST</p>
      </div>
    </div>
  );
};
