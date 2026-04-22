import React from 'react';
import { authService } from '../services/authService';
import { ComingSoonPage } from '../pages/ComingSoonPage';

interface GuestComingSoonWrapperProps {
  children: React.ReactNode;
}

export const GuestComingSoonWrapper: React.FC<GuestComingSoonWrapperProps> = ({ children }) => {
  const isAuthenticated = authService.isAuthenticated();

  if (!isAuthenticated) {
    return <ComingSoonPage />;
  }

  return <>{children}</>;
};
