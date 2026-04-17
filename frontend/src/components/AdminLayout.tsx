import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';

const NAV_ITEMS: { to: string; label: string; end?: boolean }[] = [
  { to: '/admin', label: 'Admin Dashboard', end: true },
  { to: '/admin/products', label: 'Manage Inventory' },
  { to: '/admin/users', label: 'Manage Users' },
  { to: '/admin/categories', label: 'Manage Categories' },
  { to: '/admin/vendors', label: 'Manage Vendors' },
  { to: '/admin/sales-orders', label: 'Manage Orders' },
  { to: '/admin/stock', label: 'Stock Ledger' },
  { to: '/admin/data-import-export', label: 'Data Import / Export' },
  { to: '/admin/role-functionalities', label: 'Role to Functionality' },
  { to: '/admin/user-roles', label: 'User to Role Mapping' },
];

export const AdminLayout: React.FC = () => (
  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 24, padding: '20px 15px 50px' }}>
    <nav className="admin-sidebar">
      <h3 className="admin-sidebar-title">Menu</h3>
      {NAV_ITEMS.map(item => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) =>
            isActive ? 'admin-nav-link admin-nav-link-active' : 'admin-nav-link'
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
    <main className="admin-main-content">
      <Outlet />
    </main>
  </div>
);
