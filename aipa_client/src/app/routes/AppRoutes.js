import React from 'react';
import { Route, Routes } from 'react-router-dom';
import { LoginPage, RegisterPage } from '../../features/auth/pages';
import { AdminDashboardPage } from '../../features/admin/pages';
import { HomePage } from '../../features/home/pages';
import { UserManagerInfoPage } from '../../features/user/pages';
import { AdminRoute, ProtectedRoute, PublicOnlyRoute } from './guards';

const AppRoutes = () => (
  <Routes>
    <Route element={<PublicOnlyRoute />}>
      <Route path="/" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
    </Route>

    <Route element={<ProtectedRoute />}>
      <Route path="/home" element={<HomePage />} />
      <Route path="/userInfo" element={<UserManagerInfoPage />} />
    </Route>

    <Route element={<AdminRoute />}>
      <Route path="/admin" element={<AdminDashboardPage />} />
      <Route path="/admin/history" element={<AdminDashboardPage initialTab="history" />} />
    </Route>
  </Routes>
);

export default AppRoutes;
