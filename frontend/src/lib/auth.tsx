import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";
import { AuthContext, type CurrentUser } from "./auth-context";

const TOKEN_STORAGE_KEY = "sentinel_access_token";

/**
 * Central auth/session store. Frontend never contains business rules: this
 * only holds the token/user returned by the backend and attaches the
 * Authorization header, nothing more.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_STORAGE_KEY),
  );
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (token) {
      api.defaults.headers.common.Authorization = `Bearer ${token}`;
    } else {
      delete api.defaults.headers.common.Authorization;
    }
  }, [token]);

  const fetchMe = useCallback(async () => {
    const response = await api.get<CurrentUser>("/auth/me");
    setUser(response.data);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      if (token) {
        try {
          await fetchMe();
        } catch {
          setToken(null);
          localStorage.removeItem(TOKEN_STORAGE_KEY);
        }
      }
      if (!cancelled) {
        setIsLoading(false);
      }
    }

    void init();
    return () => {
      cancelled = true;
    };
  }, [token, fetchMe]);

  const persistSession = useCallback((accessToken: string, currentUser: CurrentUser) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    setToken(accessToken);
    setUser(currentUser);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await api.post("/auth/login", {
        email: email.trim(),
        password,
      });
      persistSession(response.data.access_token, response.data.user);
      return response.data.user as CurrentUser;
    },
    [persistSession],
  );

  const signup = useCallback(
    async (fullName: string, email: string, password: string) => {
      const response = await api.post("/auth/signup", {
        full_name: fullName.trim(),
        email: email.trim(),
        password,
      });
      persistSession(response.data.access_token, response.data.user);
      return response.data.user as CurrentUser;
    },
    [persistSession],
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, token, isLoading, login, signup, logout, refreshUser: fetchMe }),
    [user, token, isLoading, login, signup, logout, fetchMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
