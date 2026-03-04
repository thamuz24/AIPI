import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../../features/auth/context';

const PublicOnlyRoute = () => {
  const { isAuthenticated, isBootstrapping } = useAuth();

  if (isBootstrapping) {
    return null;
  }

  if (isAuthenticated) {
    return <Navigate to="/home" replace />;
  }

  return <Outlet />;
};

export default PublicOnlyRoute;
