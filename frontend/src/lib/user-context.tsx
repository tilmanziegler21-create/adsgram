"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api, type UserProfile } from "@/lib/api";
import type { TelegramAuthUser } from "@/components/TelegramLogin";

const STORAGE_KEY = "adsgram_user_id";

type UserContextValue = {
  user: UserProfile | null;
  loading: boolean;
  loginWithTelegram: (tgUser: TelegramAuthUser) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const UserContext = createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
      setUser(null);
      return;
    }
    try {
      const profile = await api.getProfile(id);
      setUser(profile);
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const loginWithTelegram = useCallback(async (tgUser: TelegramAuthUser) => {
    const profile = await api.telegramLogin(tgUser);
    localStorage.setItem(STORAGE_KEY, profile.id);
    setUser(profile);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, loginWithTelegram, logout, refresh }),
    [user, loading, loginWithTelegram, logout, refresh],
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used within UserProvider");
  return ctx;
}

export function userDisplayName(user: UserProfile): string {
  if (user.telegram_username) return `@${user.telegram_username}`;
  if (user.telegram_first_name) return user.telegram_first_name;
  return `ID ${user.telegram_id}`;
}
