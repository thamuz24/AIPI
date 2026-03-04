import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { fetchMeApi, loginApi, loginByFaceApi, registerApi } from '../../../shared/api';
import { clearStoredAuth, getStoredAuth, setStoredAuth } from '../../../shared/services';

const AuthContext = createContext(null);

function normalizeAuthResponse(response) {
  return {
    accessToken: response?.accessToken || '',
    tokenType: response?.tokenType || 'Bearer',
    role: response?.role || '',
    refreshToken: response?.refreshToken || '',
    message: response?.message || '',
  };
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => getStoredAuth() || null);
  const [currentUser, setCurrentUser] = useState(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  const setAuthSession = useCallback((session) => {
    setAuth(session);
    setStoredAuth(session);
  }, []);

  const logout = useCallback(() => {
    setAuth(null);
    setCurrentUser(null);
    clearStoredAuth();
  }, []);

  const fetchMe = useCallback(async () => {
    const me = await fetchMeApi();
    setCurrentUser(me);
    return me;
  }, []);

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      if (!auth?.accessToken) {
        if (active) setIsBootstrapping(false);
        return;
      }

      try {
        await fetchMe();
      } catch (_error) {
        logout();
      } finally {
        if (active) setIsBootstrapping(false);
      }
    }

    bootstrap();

    return () => {
      active = false;
    };
  }, [auth?.accessToken, fetchMe, logout]);

  const login = useCallback(
    async (payload) => {
      const data = await loginApi(payload);
      const session = normalizeAuthResponse(data);
      setAuthSession(session);
      await fetchMe();
      return session;
    },
    [fetchMe, setAuthSession]
  );

  const loginByFace = useCallback(
    async (payload) => {
      const data = await loginByFaceApi(payload);
      const session = normalizeAuthResponse(data);
      setAuthSession(session);
      await fetchMe();
      return session;
    },
    [fetchMe, setAuthSession]
  );

  const register = useCallback(
    async (payload) => {
      const data = await registerApi(payload);
      const session = normalizeAuthResponse(data);
      setAuthSession(session);
      await fetchMe();
      return session;
    },
    [fetchMe, setAuthSession]
  );

  const value = useMemo(
    () => ({
      auth,
      currentUser,
      isAuthenticated: Boolean(auth?.accessToken),
      isBootstrapping,
      login,
      loginByFace,
      register,
      fetchMe,
      logout,
    }),
    [auth, currentUser, isBootstrapping, login, loginByFace, register, fetchMe, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
