import { createContext } from "react";

export interface CurrentUser {
  id: number;
  full_name: string;
  email: string;
  account_number: string;
  role: "user" | "admin";
  pin_is_set: boolean;
  balance: string;
}

export interface AuthContextValue {
  user: CurrentUser | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<CurrentUser>;
  signup: (fullName: string, email: string, password: string) => Promise<CurrentUser>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
