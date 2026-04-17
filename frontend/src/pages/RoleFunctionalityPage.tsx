import React, { useEffect, useMemo, useState } from 'react';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { AppRole, Functionality, rbacService, RoleMapping } from '../services/rbacService';

const editableRoles: AppRole[] = ['user', 'customer', 'business', 'vendor'];

export const RoleFunctionalityPage: React.FC = () => {
  const [functionalities, setFunctionalities] = useState<Functionality[]>([]);
  const [mappings, setMappings] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(true);
  const [savingRole, setSavingRole] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    void loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true); setError('');
      const [allFuncs, roleMappings] = await Promise.all([rbacService.getFunctionalities(), rbacService.getRoleMappings()]);
      setFunctionalities(allFuncs);
      const obj: Record<string, string[]> = {};
      roleMappings.forEach((e: RoleMapping) => { obj[e.role] = e.functionalities; });
      setMappings(obj);
    } catch { setError('Failed to load role mappings.'); }
    finally { setLoading(false); }
  };

  const activeRoles = useMemo(() => {
    const rolesFromBackend = Object.keys(mappings).filter((role) => role !== 'admin') as AppRole[];
    return Array.from(new Set([...editableRoles, ...rolesFromBackend]));
  }, [mappings]);

  const toggleFunctionality = (role: AppRole, code: string) => {
    setMappings((prev) => {
      const cur = prev[role] || [];
      return { ...prev, [role]: cur.includes(code) ? cur.filter((v) => v !== code) : [...cur, code] };
    });
  };

  const saveRole = async (role: AppRole) => {
    try { setSavingRole(role); setMessage(''); setError('');
      await rbacService.updateRoleFunctionalities(role, mappings[role] || []);
      setMessage(`Updated role mapping for ${role}.`);
    } catch { setError(`Failed to update mapping for role ${role}.`); }
    finally { setSavingRole(null); }
  };

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="container" style={{ marginTop: '30px', marginBottom: '50px' }}>
        <h1>Role to Functionality Mapping</h1>
        <p>Map application functionalities to each role. Admin always has full access and is not editable.</p>

        {message && <div className="alert alert-success">{message}</div>}
        {error && <div className="alert alert-danger">{error}</div>}

        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>Loading mappings...</div>
        ) : (
          <>
            <div className="card" style={{ marginBottom: '20px' }}>
              <h3 style={{ marginTop: 0 }}>Available Functionalities</h3>
              <ul style={{ marginBottom: 0 }}>
                {functionalities.map((func) => (
                  <li key={func.code}>
                    <strong>{func.name}</strong>: {func.description}
                  </li>
                ))}
              </ul>
            </div>

            {activeRoles.map((role) => (
              <div className="card" key={role} style={{ marginBottom: '16px' }}>
                <h3 style={{ marginTop: 0, textTransform: 'capitalize' }}>{role}</h3>
                <div style={{ display: 'grid', gap: '10px' }}>
                  {functionalities.map((func) => (
                    <label key={`${role}-${func.code}`} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <input
                        type="checkbox"
                        checked={(mappings[role] || []).includes(func.code)}
                        onChange={() => toggleFunctionality(role, func.code)}
                      />
                      <span>{func.name}</span>
                    </label>
                  ))}
                </div>
                <div style={{ marginTop: '12px' }}>
                  <button
                    className="btn btn-primary"
                    onClick={() => void saveRole(role)}
                    disabled={savingRole === role}
                  >
                    {savingRole === role ? 'Saving...' : 'Save Mapping'}
                  </button>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </ProtectedRoute>
  );
};
