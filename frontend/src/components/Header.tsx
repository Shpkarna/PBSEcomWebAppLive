import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

interface HeaderProps {
  user?: { username: string; role: string } | null;
  onLogout: () => Promise<void> | void;
  companyImageSrc?: string | null;
}

const FALLBACK_BRAND = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 320 96'%3E%3Crect width='320' height='96' fill='%23f5f7fa'/%3E%3Ctext x='50%25' y='52%25' dominant-baseline='middle' text-anchor='middle' font-family='Segoe UI, Arial, sans-serif' font-size='34' fill='%230056b3'%3EHatt%3C/text%3E%3C/svg%3E";

export const Header: React.FC<HeaderProps> = ({ user, onLogout, companyImageSrc }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const canManageInventory = user?.role === 'admin' || user?.role === 'business';
  const canUseCustomerNav = user?.role === 'customer' || user?.role === 'admin';

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    setMenuOpen(false);
    setMobileNavOpen(false);
    await onLogout();
  };

  const closeMobileNav = () => setMobileNavOpen(false);

  const navLinks = (
    <>
      <Link to="/dashboard" style={navLinkStyles} onClick={closeMobileNav}>Dashboard</Link>
      <Link to="/products" style={navLinkStyles} onClick={closeMobileNav}>Products</Link>
      {canUseCustomerNav && <Link to="/cart" style={navLinkStyles} onClick={closeMobileNav}>Cart</Link>}
      {canUseCustomerNav && <Link to="/orders" style={navLinkStyles} onClick={closeMobileNav}>Orders</Link>}
      {canManageInventory && <Link to="/inventory" style={navLinkStyles} onClick={closeMobileNav}>Inventory</Link>}
      {user?.role === 'admin' && <Link to="/admin" style={navLinkStyles} onClick={closeMobileNav}>Admin</Link>}
    </>
  );

  return (
    <header style={headerStyles}>
      <div className="container">
        {/* Top bar — always one row: hamburger · logo · desktop-nav · user */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
            {/* Hamburger — visible only on mobile via CSS */}
            <button
              className="header-hamburger"
              onClick={() => setMobileNavOpen((prev) => !prev)}
              aria-label="Toggle navigation"
            >
              <span className="header-hamburger-bar" />
              <span className="header-hamburger-bar" />
              <span className="header-hamburger-bar" />
            </button>
            <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', position: 'relative' }} onContextMenu={(e) => e.preventDefault()}>
              <img src={companyImageSrc || FALLBACK_BRAND} alt="Hatt"
                style={{ width: '160px', maxWidth: '38vw', height: '55px', objectFit: 'contain', filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.15))', pointerEvents: 'none', userSelect: 'none' } as React.CSSProperties}
                draggable={false}
                onContextMenu={(e) => e.preventDefault()}
              />
              <div style={{ position: 'absolute', inset: 0, backgroundColor: 'transparent', zIndex: 1 }} onContextMenu={(e) => e.preventDefault()} />
            </Link>
            {/* Desktop nav — hidden on mobile via CSS */}
            <nav className="header-nav-desktop">{navLinks}</nav>
          </div>

          {/* User section — always visible top-right */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            {user ? (
              <div ref={menuRef} style={{ position: 'relative' }}>
                <a
                  href="#"
                  style={{ color: '#0056b3', fontWeight: 700, textDecoration: 'underline', whiteSpace: 'nowrap' }}
                  onClick={(e) => {
                    e.preventDefault();
                    setMenuOpen((prev) => !prev);
                  }}
                >
                  {user.username}
                </a>
                {menuOpen && (
                  <div style={menuStyles}>
                    <Link to="/profile" style={menuItemStyles} onClick={() => setMenuOpen(false)}>Profile</Link>
                    <Link to="/saved-for-later" style={menuItemStyles} onClick={() => setMenuOpen(false)}>Saved for Later</Link>
                    <button onClick={handleSignOut} style={menuButtonStyles}>Sign Out</button>
                  </div>
                )}
              </div>
            ) : (
              <>
                <Link to="/login" className="btn btn-primary" style={{ textDecoration: 'none', whiteSpace: 'nowrap' }}>
                  Login
                </Link>
                <Link to="/register" className="btn btn-secondary" style={{ textDecoration: 'none', whiteSpace: 'nowrap' }}>
                  Register
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Mobile nav drawer — toggled by hamburger */}
        <nav className={`header-nav-mobile${mobileNavOpen ? ' open' : ''}`}>{navLinks}</nav>
      </div>
    </header>
  );
};

const headerStyles: React.CSSProperties = {
  backgroundColor: '#ffffff',
  borderBottom: '1px solid #ddd',
  padding: '15px 0',
  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
  position: 'sticky',
  top: 0,
  zIndex: 100,
};

const navLinkStyles: React.CSSProperties = {
  color: '#333',
  textDecoration: 'none',
  fontWeight: 500,
  fontSize: '0.95rem',
  whiteSpace: 'nowrap',
  transition: 'color 0.3s',
  cursor: 'pointer',
};

const menuStyles: React.CSSProperties = {
  position: 'absolute',
  right: 0,
  top: '130%',
  minWidth: '180px',
  maxWidth: '90vw',
  backgroundColor: '#fff',
  border: '1px solid #ddd',
  borderRadius: '8px',
  boxShadow: '0 8px 20px rgba(0, 0, 0, 0.12)',
  zIndex: 999,
  overflow: 'hidden',
};

const menuItemStyles: React.CSSProperties = {
  display: 'block',
  padding: '10px 12px',
  color: '#333',
  textDecoration: 'none',
  borderBottom: '1px solid #f0f0f0',
};

const menuButtonStyles: React.CSSProperties = {
  width: '100%',
  border: 'none',
  background: '#fff',
  padding: '10px 12px',
  textAlign: 'left',
  cursor: 'pointer',
  color: '#c82333',
  fontWeight: 600,
};
