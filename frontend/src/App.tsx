import React, { Suspense, useEffect, useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AdminLayout } from './components/AdminLayout';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { ProtectedRoute } from './components/ProtectedRoute';
import { GuestComingSoonWrapper } from './components/GuestComingSoonWrapper';
import { authService, User } from './services/authService';
import {
  loadCompanyImage,
  refreshCompanyImage,
  registerCompanyImageExitCleanup,
  markSkipCompanyImageClearOnNextExit,
} from './services/companyImageCache';
import './styles/global.css';

const lazyWithRetry = (
  importer: () => Promise<{ default: React.ComponentType<any> }>
) => React.lazy(async () => {
  const storageKey = 'lazy-chunk-retry';
  const hasRefreshed = sessionStorage.getItem(storageKey) === 'true';

  try {
    const module = await importer();
    sessionStorage.setItem(storageKey, 'false');
    return module;
  } catch (error: any) {
    const message = String(error?.message || error || '');
    const isChunkLoadError = /ChunkLoadError|Loading chunk [^\s]+ failed|Failed to fetch dynamically imported module/i.test(message);

    if (isChunkLoadError && !hasRefreshed) {
      sessionStorage.setItem(storageKey, 'true');
      window.location.reload();
      return new Promise<never>(() => {});
    }

    throw error;
  }
});

const HomePage = lazyWithRetry(() => import('./pages/HomePage').then(module => ({ default: module.HomePage })));
const DashboardPage = lazyWithRetry(() => import('./pages/DashboardPage').then(module => ({ default: module.DashboardPage })));
const LoginPage = lazyWithRetry(() => import('./pages/LoginPage').then(module => ({ default: module.LoginPage })));
const RegisterPage = lazyWithRetry(() => import('./pages/RegisterPage').then(module => ({ default: module.RegisterPage })));
const CartPage = lazyWithRetry(() => import('./pages/CartPage').then(module => ({ default: module.CartPage })));
const CheckoutPage = lazyWithRetry(() => import('./pages/CheckoutPage').then(module => ({ default: module.CheckoutPage })));
const OrdersPage = lazyWithRetry(() => import('./pages/OrdersPage').then(module => ({ default: module.OrdersPage })));
const AdminDashboardPage = lazyWithRetry(() => import('./pages/AdminDashboardPage').then(module => ({ default: module.AdminDashboardPage })));
const AdminProductsPage = lazyWithRetry(() => import('./pages/AdminProductsPage').then(module => ({ default: module.AdminProductsPage })));
const RoleFunctionalityPage = lazyWithRetry(() => import('./pages/RoleFunctionalityPage').then(module => ({ default: module.RoleFunctionalityPage })));
const UserRoleMappingPage = lazyWithRetry(() => import('./pages/UserRoleMappingPage').then(module => ({ default: module.UserRoleMappingPage })));
const DataImportExportPage = lazyWithRetry(() => import('./pages/DataImportExportPage').then(module => ({ default: module.DataImportExportPage })));
const UsersManagementPage = lazyWithRetry(() => import('./pages/UsersManagementPage').then(module => ({ default: module.UsersManagementPage })));
const CategoriesPage = lazyWithRetry(() => import('./pages/CategoriesPage').then(module => ({ default: module.CategoriesPage })));
const VendorsPage = lazyWithRetry(() => import('./pages/VendorsPage').then(module => ({ default: module.VendorsPage })));
const OrderManagementPage = lazyWithRetry(() => import('./pages/OrderManagementPage').then(module => ({ default: module.OrderManagementPage })));
const AllSalesOrdersPage = lazyWithRetry(() => import('./pages/AllSalesOrdersPage').then(module => ({ default: module.AllSalesOrdersPage })));
const StockLedgerPage = lazyWithRetry(() => import('./pages/StockLedgerPage').then(module => ({ default: module.StockLedgerPage })));
const ContactUsPage = lazyWithRetry(() => import('./pages/ContactUsPage').then(module => ({ default: module.ContactUsPage })));
const FAQPage = lazyWithRetry(() => import('./pages/FAQPage').then(module => ({ default: module.FAQPage })));
const AboutUsPage = lazyWithRetry(() => import('./pages/AboutUsPage').then(module => ({ default: module.AboutUsPage })));
const ReturnsPage = lazyWithRetry(() => import('./pages/ReturnsPage').then(module => ({ default: module.ReturnsPage })));
const OrderDetailPage = lazyWithRetry(() => import('./pages/OrderDetailPage').then(module => ({ default: module.OrderDetailPage })));
const InventoryPage = lazyWithRetry(() => import('./pages/InventoryPage').then(module => ({ default: module.InventoryPage })));
const ProfilePage = lazyWithRetry(() => import('./pages/ProfilePage').then(module => ({ default: module.ProfilePage })));
const SavedForLaterPage = lazyWithRetry(() => import('./pages/SavedForLaterPage').then(module => ({ default: module.SavedForLaterPage })));
const ProductDetailPage = lazyWithRetry(() => import('./pages/ProductDetailPage').then(module => ({ default: module.ProductDetailPage })));

const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [companyImageSrc, setCompanyImageSrc] = useState<string | null>(null);

  const checkAuth = async () => {
    if (authService.isAuthenticated()) {
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
    }
  };

  useEffect(() => {
    const loadAuth = async () => {
      await checkAuth();
      setLoading(false);
    };
    loadAuth();
  }, []);

  useEffect(() => {
    registerCompanyImageExitCleanup();

    const applyCompanyImage = async () => {
      const imageSrc = await loadCompanyImage();
      setCompanyImageSrc(imageSrc);
    };

    const handleCompanyImageUpdated = async () => {
      const imageSrc = await refreshCompanyImage();
      setCompanyImageSrc(imageSrc);
    };

    void applyCompanyImage();
    window.addEventListener('company-image-updated', handleCompanyImageUpdated);

    return () => {
      window.removeEventListener('company-image-updated', handleCompanyImageUpdated);
    };
  }, []);

  useEffect(() => {
    if (companyImageSrc) {
      document.documentElement.style.setProperty('--company-image-url', `url("${companyImageSrc}")`);
    } else {
      document.documentElement.style.removeProperty('--company-image-url');
    }
  }, [companyImageSrc]);

  const handleLogout = useCallback(async () => {
    markSkipCompanyImageClearOnNextExit();
    await authService.logout();
    setUser(null);
    window.location.href = '/dashboard';
  }, []);

  const handleLoginSuccess = async () => {
    await checkAuth();
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '50px' }}>Loading...</div>;
  }

  return (
    <BrowserRouter>
      <Header user={user} onLogout={handleLogout} companyImageSrc={companyImageSrc} />
      <main style={{ minHeight: '80vh' }}>
        <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}>Loading page...</div>}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/products" element={
              <GuestComingSoonWrapper>
                <HomePage />
              </GuestComingSoonWrapper>
            } />
            <Route path="/products/:productId" element={<ProductDetailPage />} />
            <Route path="/login" element={<LoginPage onLoginSuccess={handleLoginSuccess} />} />
            <Route path="/register" element={<RegisterPage onRegisterSuccess={handleLoginSuccess} />} />
            <Route path="/dashboard" element={
              <GuestComingSoonWrapper>
                <DashboardPage />
              </GuestComingSoonWrapper>
            } />
            <Route path="/profile" element={
              <ProtectedRoute requiredFunctionality="user_profile">
                <ProfilePage />
              </ProtectedRoute>
            } />
            <Route path="/saved-for-later" element={
              <ProtectedRoute requiredFunctionality="customer_purchase">
                <SavedForLaterPage />
              </ProtectedRoute>
            } />
            <Route path="/cart" element={
              <ProtectedRoute requiredFunctionality="customer_purchase">
                <CartPage onCheckout={() => { window.location.href = '/checkout'; }} />
              </ProtectedRoute>
            } />
            <Route path="/checkout" element={
              <ProtectedRoute requiredFunctionality="customer_purchase">
                <CheckoutPage onOrderComplete={() => { window.location.href = '/orders'; }} />
              </ProtectedRoute>
            } />
            <Route path="/orders" element={
              <ProtectedRoute requiredFunctionality="customer_purchase">
                <OrdersPage />
              </ProtectedRoute>
            } />
            <Route path="/orders/:orderId" element={
              <ProtectedRoute requiredFunctionality="customer_purchase">
                <OrderDetailPage />
              </ProtectedRoute>
            } />
            <Route path="/returns" element={
              <ProtectedRoute requiredFunctionality="customer_purchase">
                <ReturnsPage />
              </ProtectedRoute>
            } />
            <Route path="/contact" element={<ContactUsPage />} />
            <Route path="/faq" element={<FAQPage />} />
            <Route path="/about" element={<AboutUsPage />} />
            <Route path="/inventory" element={
              <ProtectedRoute requiredFunctionality="inventory_manage">
                <InventoryPage />
              </ProtectedRoute>
            } />
            <Route path="/admin" element={
              <ProtectedRoute requiredFunctionality="inventory_manage">
                <AdminLayout />
              </ProtectedRoute>
            }>
              <Route index element={<AdminDashboardPage />} />
              <Route path="products" element={<AdminProductsPage />} />
              <Route path="users" element={<UsersManagementPage />} />
              <Route path="categories" element={<CategoriesPage />} />
              <Route path="vendors" element={<VendorsPage />} />
              <Route path="orders" element={<OrderManagementPage />} />
              <Route path="sales-orders" element={<AllSalesOrdersPage />} />
              <Route path="stock" element={<StockLedgerPage />} />
              <Route path="role-functionalities" element={<RoleFunctionalityPage />} />
              <Route path="user-roles" element={<UserRoleMappingPage />} />
              <Route path="data-import-export" element={<DataImportExportPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
      <Footer />
    </BrowserRouter>
  );
};

export default App;
