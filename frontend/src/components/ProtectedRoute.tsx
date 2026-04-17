import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService, User } from '../services/authService';
import { rbacService } from '../services/rbacService';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: 'admin' | 'business' | 'user' | 'customer' | 'vendor';
  requiredFunctionality?: 'user_profile' | 'customer_purchase' | 'inventory_manage';
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  requiredFunctionality,
}) => {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const currentUser = await authService.getCurrentUser();
        if (!currentUser) {
          navigate('/login', { replace: true });
          return;
        }
        
        const isAdmin = currentUser.role === 'admin';

        if (requiredRole && !isAdmin && currentUser.role !== requiredRole) {
          navigate('/', { replace: true });
          return;
        }

        if (requiredFunctionality && !isAdmin) {
          const access = await rbacService.getMyAccess();
          if (!access.functionalities.includes(requiredFunctionality)) {
            navigate('/', { replace: true });
            return;
          }
        }
        
        setUser(currentUser);
      } catch {
        // Prevent unhandled promise rejections when API is temporarily unreachable.
        navigate('/login', { replace: true });
      } finally {
        setLoading(false);
      }
    };

    if (authService.isAuthenticated()) {
      checkAuth();
    } else {
      navigate('/login', { replace: true });
    }
  }, [navigate, requiredRole, requiredFunctionality]);

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '50px' }}>Loading...</div>;
  }

  return <>{children}</>;
};
