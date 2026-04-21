import React, { useState } from 'react';

type Props = { onSubmit: (payload: Record<string, string>) => Promise<void>; };

export const VendorForm: React.FC<Props> = ({ onSubmit }) => {
  const [form, setForm] = useState({ name: '', email: '', phone: '', address: '', gst_number: '', bank_details: '' });
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(form);
    setForm({ name: '', email: '', phone: '', address: '', gst_number: '', bank_details: '' });
  };
  return (
    <form onSubmit={submit} className="card" style={{ marginBottom: 20 }}>
      <h3>Create Vendor</h3>
      <input className="form-input" placeholder="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
      <input className="form-input" placeholder="Email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
      <input className="form-input" placeholder="Phone" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} />
      <input className="form-input" placeholder="Address" value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} />
      <button className="btn btn-primary" type="submit">Create</button>
    </form>
  );
};
