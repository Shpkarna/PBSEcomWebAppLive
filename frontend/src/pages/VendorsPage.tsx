import React, { useEffect, useState } from 'react';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { VendorForm } from '../components/VendorForm';
import { vendorService } from '../services/vendorService';

export const VendorsPage: React.FC = () => {
  const [rows, setRows] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [message, setMessage] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<Record<string, string>>({ name: '', email: '', phone: '', address: '', gst_number: '', bank_details: '' });

  const load = async () => {
    try { setRows(await vendorService.list()); } catch { setMessage('Failed to load vendors'); }
  };

  useEffect(() => { load(); }, []);

  const createRow = async (payload: Record<string, string>) => {
    await vendorService.create(payload);
    await load();
  };

  const startEdit = (r: any) => {
    setEditingId(r.id);
    setEditData({ name: r.name || '', email: r.email || '', phone: r.phone || '', address: r.address || '', gst_number: r.gst_number || '', bank_details: r.bank_details || '' });
  };

  const cancelEdit = () => { setEditingId(null); };

  const saveEdit = async () => {
    if (!editingId) return;
    try {
      const updates: Record<string, string> = {};
      Object.entries(editData).forEach(([k, v]) => { if (v) updates[k] = v; });
      await vendorService.update(editingId, updates);
      setEditingId(null);
      await load();
    } catch { setMessage('Failed to update vendor'); }
  };

  const remove = async (id: string) => {
    if (!window.confirm('Delete vendor?')) return;
    await vendorService.remove(id);
    await load();
  };

  const normalizedSearch = searchTerm.trim().toLowerCase();
  const filteredRows = rows.filter((r) => {
    if (!normalizedSearch) return true;
    return (
      (r.name || '').toLowerCase().includes(normalizedSearch)
      || (r.email || '').toLowerCase().includes(normalizedSearch)
      || (r.phone || '').toLowerCase().includes(normalizedSearch)
      || (r.gst_number || '').toLowerCase().includes(normalizedSearch)
    );
  });

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="container" style={{ marginTop: 30 }}>
        <h1>Vendors</h1>
        {message && <div className="alert alert-danger">{message}</div>}
        <VendorForm onSubmit={createRow} />
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0 }}>Vendors List ({filteredRows.length})</h3>
            <input
              type="text"
              placeholder="Search vendors by name, email, phone, or GST"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ minWidth: 300, padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
            />
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%' }}>
              <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>GST No</th><th>Actions</th></tr></thead>
              <tbody>{filteredRows.map(r => (
                <tr key={r.id}>
                  <td>{editingId === r.id ? (
                    <input value={editData.name} onChange={e => setEditData({ ...editData, name: e.target.value })}
                      style={{ width: '100%', padding: 4, border: '1px solid #ddd', borderRadius: 4 }} />
                  ) : r.name}</td>
                  <td>{editingId === r.id ? (
                    <input value={editData.email} onChange={e => setEditData({ ...editData, email: e.target.value })}
                      style={{ width: '100%', padding: 4, border: '1px solid #ddd', borderRadius: 4 }} />
                  ) : (r.email || '-')}</td>
                  <td>{editingId === r.id ? (
                    <input value={editData.phone} onChange={e => setEditData({ ...editData, phone: e.target.value })}
                      style={{ width: '100%', padding: 4, border: '1px solid #ddd', borderRadius: 4 }} />
                  ) : (r.phone || '-')}</td>
                  <td>{editingId === r.id ? (
                    <input value={editData.gst_number} onChange={e => setEditData({ ...editData, gst_number: e.target.value })}
                      style={{ width: '100%', padding: 4, border: '1px solid #ddd', borderRadius: 4 }} />
                  ) : (r.gst_number || '-')}</td>
                  <td>
                    {editingId === r.id ? (
                      <><button className="btn btn-primary" style={{ marginRight: 4, padding: '4px 8px' }} onClick={saveEdit}>Save</button>
                        <button className="btn btn-secondary" style={{ padding: '4px 8px' }} onClick={cancelEdit}>Cancel</button></>
                    ) : (
                      <><button className="btn btn-secondary" style={{ marginRight: 4, padding: '4px 8px' }} onClick={() => startEdit(r)}>Edit</button>
                        <button className="btn" style={{ padding: '4px 8px' }} onClick={() => remove(r.id)}>Delete</button></>
                    )}
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
};
