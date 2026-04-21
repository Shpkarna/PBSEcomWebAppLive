import React, { useEffect, useState } from 'react';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { AppRole, RbacUser, rbacService } from '../services/rbacService';

const assignableRoles: AppRole[] = ['admin', 'business', 'user', 'customer', 'vendor'];

export const UserRoleMappingPage: React.FC = () => {
  const [users, setUsers] = useState<RbacUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchUsername, setSearchUsername] = useState('');
  const [savingUser, setSavingUser] = useState<string | null>(null);
  const [togglingUser, setTogglingUser] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    void loadUsers();
  }, []);

  const loadUsers = async () => {
    try { setLoading(true); setError(''); setUsers(await rbacService.getUsers()); }
    catch { setError('Failed to load users.'); }
    finally { setLoading(false); }
  };

  const onRoleChange = (username: string, role: AppRole) => {
    setUsers((prev) => prev.map((u) => (u.username === username ? { ...u, role } : u)));
  };

  const saveUserRole = async (username: string, role: AppRole) => {
    try {
      setSavingUser(username);
      setMessage('');
      setError('');
      await rbacService.updateUserRole(username, role);
      setMessage(`Updated role for ${username}.`);
    } catch {
      setError(`Failed to update role for ${username}.`);
    } finally {
      setSavingUser(null);
    }
  };

  const toggleUserStatus = async (user: RbacUser) => {
    try {
      setTogglingUser(user.username);
      setMessage('');
      setError('');
      const nextState = !user.is_active;
      await rbacService.updateUserStatus(user.username, nextState);
      setUsers((prev) => prev.map((u) => (u.username === user.username ? { ...u, is_active: nextState } : u)));
      setMessage(`${user.username} has been ${nextState ? 'enabled' : 'disabled'}.`);
    } catch {
      setError(`Failed to update status for ${user.username}.`);
    } finally {
      setTogglingUser(null);
    }
  };

  const normalizedSearchUsername = searchUsername.trim().toLowerCase();
  const filteredUsers = users.filter((user) => {
    if (!normalizedSearchUsername) return true;
    return user.username.toLowerCase().includes(normalizedSearchUsername);
  });

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="container" style={{ marginTop: '30px', marginBottom: '50px' }}>
        <h1>User to Role Mapping</h1>
        <p>Assign roles to users. Admin users are exempt from functionality restrictions.</p>

        {message && <div className="alert alert-success">{message}</div>}
        {error && <div className="alert alert-danger">{error}</div>}

        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>Loading users...</div>
        ) : users.length === 0 ? (
          <div className="alert alert-info">No users found.</div>
        ) : (
          <div className="card" style={{ overflowX: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 10, flexWrap: 'wrap' }}>
              <strong>Mapped Users ({filteredUsers.length})</strong>
              <input
                type="text"
                placeholder="Search by username"
                value={searchUsername}
                onChange={(event) => setSearchUsername(event.target.value)}
                style={{ minWidth: 240, padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
              />
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Active</th>
                  <th>Role</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((user) => (
                  <tr key={user.id}>
                    <td>{user.username}</td>
                    <td>{user.email || '-'}</td>
                    <td>{user.is_active ? 'Yes' : 'No'}</td>
                    <td>
                      {user.username === 'admin' ? (
                        <span>{user.role}</span>
                      ) : (
                      <select
                        value={user.role}
                        onChange={(event) => onRoleChange(user.username, event.target.value as AppRole)}
                      >
                        {assignableRoles.map((role) => (
                          <option key={role} value={role}>
                            {role}
                          </option>
                        ))}
                      </select>
                      )}
                    </td>
                    <td>
                      {user.username === 'admin' ? (
                        <span style={{ color: '#666', fontSize: 13 }}>Protected</span>
                      ) : (
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                          <button
                            className="btn btn-primary"
                            onClick={() => void saveUserRole(user.username, user.role)}
                            disabled={savingUser === user.username || togglingUser === user.username}
                          >
                            {savingUser === user.username ? 'Saving...' : 'Save Role'}
                          </button>
                          <button
                            className="btn"
                            style={{
                              backgroundColor: user.is_active ? '#dc3545' : '#198754',
                              color: '#fff',
                            }}
                            onClick={() => void toggleUserStatus(user)}
                            disabled={togglingUser === user.username || savingUser === user.username}
                          >
                            {togglingUser === user.username
                              ? 'Updating...'
                              : (user.is_active ? 'Disable' : 'Enable')}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
};
