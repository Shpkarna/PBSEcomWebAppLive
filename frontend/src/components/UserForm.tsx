import React, { useState } from 'react';

export type UserFormData = {
  username: string;
  email: string;
  password: string;
  full_name: string;
  phone: string;
  address: string;
  role: string;
  is_active: boolean;
  phone_verified: boolean;
  email_verified: boolean;
};

type Props = {
  onSubmit: (data: UserFormData) => Promise<void>;
  roles: string[];
  initialData?: Partial<UserFormData>;
  isEditMode?: boolean;
  onCancelEdit?: () => void;
};

export const UserForm: React.FC<Props> = ({ onSubmit, roles, initialData, isEditMode = false, onCancelEdit }) => {
  const defaultRole = roles.includes('user') ? 'user' : (roles[0] || 'user');
  const emptyForm: UserFormData = {
    username: '', email: '', password: '', full_name: '', phone: '', address: '', role: defaultRole, is_active: true,
    phone_verified: false, email_verified: false,
  };
  const [form, setForm] = useState<UserFormData>(emptyForm);

  React.useEffect(() => {
    setForm((prev) => ({ ...prev, role: prev.role || defaultRole }));
  }, [defaultRole]);

  React.useEffect(() => {
    if (!initialData) {
      setForm((prev) => ({ ...emptyForm, role: prev.role || defaultRole }));
      return;
    }
    setForm({
      username: String(initialData.username || ''),
      email: String(initialData.email || ''),
      password: '',
      full_name: String(initialData.full_name || ''),
      phone: String(initialData.phone || ''),
      address: String(initialData.address || ''),
      role: String(initialData.role || defaultRole),
      is_active: Boolean(initialData.is_active),
      phone_verified: Boolean(initialData.phone_verified),
      email_verified: Boolean(initialData.email_verified),
    });
  }, [initialData, defaultRole]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(form);
    if (!isEditMode) {
      setForm({ ...emptyForm, role: defaultRole });
    }
  };

  return (
    <form
      onSubmit={submit}
      className="card"
      style={{
        marginBottom: 20,
        border: '1px solid #d8e3ea',
        borderRadius: 14,
        background: 'linear-gradient(140deg, #f6fbff 0%, #ffffff 45%, #f7f4ef 100%)',
        boxShadow: '0 10px 24px rgba(8, 34, 55, 0.08)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 12, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0 }}>{isEditMode ? 'Edit User' : 'Create User'}</h3>
        <span style={{ fontSize: 12, color: '#5c7282', background: '#eaf4fb', border: '1px solid #c9e1f2', borderRadius: 999, padding: '4px 10px' }}>
          {isEditMode ? 'Editing existing record' : 'New account setup'}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
        <input
          className="form-input"
          placeholder="Username"
          value={form.username}
          onChange={e => setForm({ ...form, username: e.target.value })}
          required
          disabled={isEditMode}
        />
        <input
          className="form-input"
          placeholder="Email"
          value={form.email}
          onChange={e => setForm({ ...form, email: e.target.value })}
          required
        />
        {!isEditMode && (
          <input
            className="form-input"
            placeholder="Password"
            type="password"
            value={form.password}
            onChange={e => setForm({ ...form, password: e.target.value })}
            required
          />
        )}
        <input
          className="form-input"
          placeholder="Full name"
          value={form.full_name}
          onChange={e => setForm({ ...form, full_name: e.target.value })}
        />
        <input
          className="form-input"
          placeholder="Phone"
          value={form.phone}
          onChange={e => setForm({ ...form, phone: e.target.value })}
        />
        <input
          className="form-input"
          placeholder="Address"
          value={form.address}
          onChange={e => setForm({ ...form, address: e.target.value })}
        />
        <select className="form-input" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}>
          {roles.map((role) => (
            <option key={role} value={role}>{role}</option>
          ))}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', border: '1px solid #d8e3ea', borderRadius: 8, background: '#fff' }}>
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={e => setForm({ ...form, is_active: e.target.checked })}
          />
          Active user
        </label>
        {isEditMode && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', border: '1px solid #d8e3ea', borderRadius: 8, background: '#fff' }}>
            <input
              type="checkbox"
              checked={form.email_verified}
              onChange={e => setForm({ ...form, email_verified: e.target.checked })}
            />
            Email verified
          </label>
        )}
        {isEditMode && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', border: '1px solid #d8e3ea', borderRadius: 8, background: '#fff' }}>
            <input
              type="checkbox"
              checked={form.phone_verified}
              onChange={e => setForm({ ...form, phone_verified: e.target.checked })}
            />
            Phone verified
          </label>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
        <button className="btn btn-primary" type="submit">{isEditMode ? 'Save' : 'Create'}</button>
        {isEditMode && (
          <button className="btn" type="button" onClick={onCancelEdit}>Cancel</button>
        )}
      </div>
    </form>
  );
};
