import React, { useEffect, useState } from 'react';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { CategoryForm } from '../components/CategoryForm';
import { categoryService, CategoryDiscountType, CategoryRow } from '../services/categoryService';

const DISCOUNT_OPTIONS: CategoryDiscountType[] = ['Discount percentage', 'Discount amount'];

type CategoryEditData = {
  name: string;
  description: string;
  discount_type: CategoryDiscountType | '';
  discount_value: string;
};

const validateDiscount = (discountType: CategoryDiscountType | '', discountValue: string): string => {
  if (!discountType) {
    return 'Discount type is required';
  }
  if (discountValue === '') {
    return 'Discount value is required';
  }
  const parsedValue = Number(discountValue);
  if (Number.isNaN(parsedValue) || parsedValue < 0) {
    return 'Discount value must be 0 or greater';
  }
  if (discountType === 'Discount percentage' && parsedValue > 100) {
    return 'Discount percentage must be between 0 and 100';
  }
  return '';
};

export const CategoriesPage: React.FC = () => {
  const [rows, setRows] = useState<CategoryRow[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [message, setMessage] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<CategoryEditData>({ name: '', description: '', discount_type: '', discount_value: '' });

  const load = async () => {
    try { setRows(await categoryService.list()); } catch { setMessage('Failed to load categories'); }
  };

  useEffect(() => { load(); }, []);

  const createRow = async (payload: { name: string; description?: string; discount_type?: CategoryDiscountType; discount_value?: number }) => {
    try {
      setMessage('');
      const validationError = validateDiscount(payload.discount_type || '', payload.discount_value == null ? '' : String(payload.discount_value));
      if (validationError) {
        setMessage(validationError);
        return;
      }
      await categoryService.create(payload);
      await load();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to create category');
    }
  };

  const startEdit = (r: CategoryRow) => {
    setEditingId(r.id);
    setEditData({
      name: r.name,
      description: r.description || '',
      discount_type: (r.discount_type as CategoryDiscountType) || '',
      discount_value: r.discount_value == null ? '' : String(r.discount_value),
    });
  };

  const cancelEdit = () => { setEditingId(null); setEditData({ name: '', description: '', discount_type: '', discount_value: '' }); };

  const saveEdit = async () => {
    if (!editingId) return;
    try {
      const validationError = validateDiscount(editData.discount_type, editData.discount_value);
      if (validationError) {
        setMessage(validationError);
        return;
      }
      await categoryService.update(editingId, {
        name: editData.name,
        description: editData.description,
        discount_type: editData.discount_type || undefined,
        discount_value: editData.discount_value === '' ? undefined : Number(editData.discount_value),
      });
      setEditingId(null);
      await load();
    } catch (err: any) { setMessage(err?.response?.data?.detail || 'Failed to update category'); }
  };

  const remove = async (id: string) => {
    if (!window.confirm('Delete category?')) return;
    await categoryService.remove(id);
    await load();
  };

  const normalizedSearch = searchTerm.trim().toLowerCase();
  const filteredRows = rows.filter((r) => {
    if (!normalizedSearch) return true;
    return (
      r.name.toLowerCase().includes(normalizedSearch)
      || (r.description || '').toLowerCase().includes(normalizedSearch)
    );
  });

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="container" style={{ marginTop: 30 }}>
        <h1>Categories</h1>
        {message && <div className="alert alert-danger">{message}</div>}
        <CategoryForm onSubmit={createRow} />
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0 }}>Category List ({filteredRows.length})</h3>
            <input
              type="text"
              placeholder="Search categories by name or description"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ minWidth: 280, padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
            />
          </div>
          <table style={{ width: '100%' }}>
            <thead><tr><th>Name</th><th>Description</th><th>Discount</th><th>Discount Value</th><th>Actions</th></tr></thead>
            <tbody>{filteredRows.map(r => (
              <tr key={r.id}>
                <td>{editingId === r.id ? (
                  <input value={editData.name} onChange={e => setEditData({ ...editData, name: e.target.value })}
                    style={{ width: '100%', padding: 4, border: '1px solid #ddd', borderRadius: 4 }} />
                ) : r.name}</td>
                <td>{editingId === r.id ? (
                  <input value={editData.description} onChange={e => setEditData({ ...editData, description: e.target.value })}
                    style={{ width: '100%', padding: 4, border: '1px solid #ddd', borderRadius: 4 }} />
                ) : (r.description || '-')}</td>
                <td>{editingId === r.id ? (
                  <select
                    value={editData.discount_type}
                    onChange={e => setEditData({ ...editData, discount_type: e.target.value as CategoryDiscountType | '', discount_value: '' })}
                    style={{ width: '100%', padding: 4, border: '1px solid #ddd', borderRadius: 4 }}
                  >
                    <option value="">Select Discount Type</option>
                    {DISCOUNT_OPTIONS.map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                ) : (r.discount_type || '-')}</td>
                <td>{editingId === r.id ? (
                  <input
                    type="number"
                    value={editData.discount_value}
                    onChange={e => setEditData({ ...editData, discount_value: e.target.value })}
                    min="0"
                    max={editData.discount_type === 'Discount percentage' ? '100' : undefined}
                    step="0.01"
                    disabled={!editData.discount_type}
                    placeholder={editData.discount_type === 'Discount percentage' ? '0-100' : 'Amount'}
                    style={{ width: '100%', padding: 4, border: '1px solid #ddd', borderRadius: 4 }}
                  />
                ) : (r.discount_value == null ? '-' : `${r.discount_value}${r.discount_type === 'Discount percentage' ? '%' : ''}`)}</td>
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
    </ProtectedRoute>
  );
};
