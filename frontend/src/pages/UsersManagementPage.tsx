import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { adminService } from '../services/adminService';
import { UserForm, UserFormData } from '../components/UserForm';
import { AppRole, rbacService } from '../services/rbacService';

const SYSTEM_ADMIN_USERNAME = 'admin';

type ManagedUser = {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  phone?: string;
  address?: string;
  role: AppRole;
  is_active: boolean;
  phone_verified: boolean;
  email_verified: boolean;
};

export const UsersManagementPage: React.FC = () => {
  const location = useLocation();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [availableRoles, setAvailableRoles] = useState<AppRole[]>(['admin', 'business', 'user', 'customer', 'vendor']);
  const [searchTerm, setSearchTerm] = useState('');
  const [message, setMessage] = useState('');
  const [savingUser, setSavingUser] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<ManagedUser | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async (search?: string) => {
    try {
      setMessage('');
      const usersResult = await adminService.listAllUsers(search);
      setUsers(usersResult as ManagedUser[]);

      try {
        const roles = await rbacService.getValidRoles();
        if (Array.isArray(roles) && roles.length > 0) {
          setAvailableRoles(roles);
        }
      } catch {
        // Keep fallback roles when backend does not yet expose /rbac/valid-roles.
      }
    } catch {
      setMessage('Failed to load users');
    }
  }, []);

  // Reload fresh user list on every navigation to this page
  useEffect(() => { load(); }, [location.key, load]);

  // Re-fetch from backend when search term changes (debounced)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      load(searchTerm || undefined);
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [searchTerm, load]);

  // Also reload when the browser tab regains focus
  useEffect(() => {
    const onVisible = () => { if (document.visibilityState === 'visible') load(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [load]);

  const submitUserForm = async (data: UserFormData) => {
    try {
      setSavingUser(editingUser?.username || data.username);
      setMessage('');

      if (editingUser) {
        await adminService.updateUser(editingUser.username, {
          email: data.email,
          full_name: data.full_name,
          phone: data.phone,
          address: data.address,
          role: data.role,
          is_active: data.is_active,
          email_verified: data.email_verified,
          phone_verified: data.phone_verified,
        });
        setMessage(`Updated ${editingUser.username}`);
        setEditingUser(null);
      } else {
        await adminService.createUser({
          username: data.username,
          email: data.email,
          password: data.password,
          full_name: data.full_name,
          phone: data.phone,
          address: data.address,
          role: data.role,
          is_active: data.is_active,
        });
        setMessage(`Created ${data.username}`);
      }

      await load();
    } catch (err: any) {
      const failedUser = editingUser?.username || data.username;
      setMessage(err?.response?.data?.detail || `Failed to save ${failedUser}`);
    } finally {
      setSavingUser(null);
    }
  };

  const startEdit = (user: ManagedUser) => {
    if (user.username === SYSTEM_ADMIN_USERNAME) return;
    setEditingUser(user);
    setMessage('');
  };

  const cancelEdit = () => {
    setEditingUser(null);
    setMessage('Edit canceled');
  };

  const deleteUser = async (username: string) => {
    if (!window.confirm(`Delete user ${username}?`)) return;
    try {
      setMessage('');
      await adminService.deleteUser(username);
      setMessage(`Deleted ${username}`);
      await load();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || `Failed to delete ${username}`);
    }
  };

  const filteredUsers = users;

  const tableHeaderCellStyle: React.CSSProperties = {
    textAlign: 'left',
    fontSize: 13,
    letterSpacing: 0.2,
    color: '#2f4858',
    background: '#eef5fa',
    borderBottom: '1px solid #d4e3ee',
    padding: '12px 14px',
  };

  const tableBodyCellStyle: React.CSSProperties = {
    padding: '12px 14px',
    borderBottom: '1px solid #edf1f4',
    verticalAlign: 'middle',
    color: '#1f2f38',
    fontSize: 14,
  };

  return (
    <div className="container" style={{ marginTop: 30 }}>
      <h1>Users Management</h1>
      {message && <div className="alert alert-danger">{message}</div>}
      <UserForm
        onSubmit={submitUserForm}
        roles={availableRoles}
        initialData={editingUser || undefined}
        isEditMode={!!editingUser}
        onCancelEdit={cancelEdit}
      />
      <div className="card" style={{ border: '1px solid #d8e3ea', borderRadius: 14, boxShadow: '0 8px 18px rgba(9, 30, 44, 0.06)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0 }}>All Users ({filteredUsers.length})</h3>
            <span style={{ fontSize: 12, color: '#5c7282', background: '#eaf4fb', border: '1px solid #c9e1f2', borderRadius: 999, padding: '4px 10px' }}>
              SHP fav grid format 1
            </span>
          </div>
          <input
            type="text"
            placeholder="Search users by username or email"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ minWidth: 280, padding: 10, border: '1px solid #d4e3ee', borderRadius: 8, background: '#fbfdff' }}
          />
        </div>
        <div style={{ width: '100%', overflowX: 'auto' }}>
          <table style={{ width: '100%', minWidth: 560, borderCollapse: 'separate', borderSpacing: 0, tableLayout: 'fixed' }}>
            <thead>
              <tr>
                <th style={{ ...tableHeaderCellStyle, borderTopLeftRadius: 10, width: '44%' }}>Username</th>
                <th style={{ ...tableHeaderCellStyle, textAlign: 'center', width: '22%' }}>Active</th>
                <th style={{ ...tableHeaderCellStyle, textAlign: 'center', borderTopRightRadius: 10, width: '34%' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map(u => (
                <tr key={u.id} style={{ background: '#fff' }}>
                  <td style={{ ...tableBodyCellStyle, fontWeight: 600, wordBreak: 'break-word' }}>{u.username}</td>
                  <td style={{ ...tableBodyCellStyle, textAlign: 'center' }}>
                    <span
                      style={{
                        display: 'inline-block',
                        minWidth: 70,
                        padding: '4px 10px',
                        borderRadius: 999,
                        fontSize: 12,
                        fontWeight: 700,
                        color: u.is_active ? '#0f6b2a' : '#8f1d1d',
                        background: u.is_active ? '#e7f8ec' : '#fdecec',
                        border: u.is_active ? '1px solid #bde9ca' : '1px solid #f5c6c6',
                      }}
                    >
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td style={{ ...tableBodyCellStyle, textAlign: 'center' }}>
                    {u.username === SYSTEM_ADMIN_USERNAME ? (
                      <span style={{ color: '#666', fontSize: 13 }}>Protected</span>
                    ) : (
                      <div style={{ display: 'inline-flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
                        <button
                          className="btn btn-primary"
                          disabled={savingUser === u.username}
                          onClick={() => startEdit(u)}
                          style={{ minWidth: 76 }}
                        >
                          Edit
                        </button>
                        <button
                          className="btn"
                          disabled={savingUser === u.username}
                          onClick={() => deleteUser(u.username)}
                          style={{ minWidth: 76 }}
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
