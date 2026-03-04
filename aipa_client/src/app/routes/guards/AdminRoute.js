import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../../features/auth/context';

function hasAdminAuthority(currentUser) {
  const authorities = currentUser?.authorities;
  if (!Array.isArray(authorities)) return false;

  return authorities.some((item) => {
    if (typeof item === 'string') return item === 'ROLE_ADMIN';
    return item?.authority === 'ROLE_ADMIN';
  });
}

const AdminRoute = () => {
  const { isAuthenticated, isBootstrapping, auth, currentUser } = useAuth();

  if (isBootstrapping) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (auth?.role !== 'ROLE_ADMIN' && !hasAdminAuthority(currentUser)) {
    return <Navigate to="/home" replace />;
  }

  return <Outlet />;
};

export default AdminRoute;
