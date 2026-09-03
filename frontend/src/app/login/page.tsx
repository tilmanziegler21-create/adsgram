"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { TelegramLogin, type TelegramAuthUser } from "@/components/TelegramLogin";
import { ApiError, api } from "@/lib/api";
import { useUser } from "@/lib/user-context";

export default function LoginPage() {
  const { user, loginWithTelegram } = useUser();
  const router = useRouter();
  const [botUsername, setBotUsername] = useState(
    process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "",
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (botUsername) return;
    api
      .getAuthConfig()
      .then((cfg) => {
        if (cfg.bot_username) setBotUsername(cfg.bot_username);
      })
      .catch(() => {});
  }, [botUsername]);

  const handleAuth = useCallback(
    async (tgUser: TelegramAuthUser) => {
      setError("");
      setLoading(true);
      try {
        await loginWithTelegram(tgUser);
        router.push("/");
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Ошибка входа");
      } finally {
        setLoading(false);
      }
    },
    [loginWithTelegram, router],
  );

  if (user) {
    router.replace("/");
    return null;
  }

  return (
    <div className="mx-auto flex max-w-md flex-col px-4 py-16">
      <div className="rounded-2xl border border-violet-200/60 bg-white p-8 shadow-lg shadow-violet-500/5 dark:border-violet-900/40 dark:bg-zinc-900">
        <h1 className="text-center text-2xl font-bold">Вход в Adsgram</h1>
        <p className="mt-2 text-center text-sm text-zinc-500">
          Войдите через Telegram — мы сохраним ваш ID и username для заказов и баланса.
        </p>

        <div className="mt-8">
          {botUsername ? (
            <div className={loading ? "pointer-events-none opacity-60" : ""}>
              <TelegramLogin botUsername={botUsername} onAuth={handleAuth} />
            </div>
          ) : (
            <p className="rounded-xl bg-amber-50 px-4 py-3 text-center text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              Укажите <code className="text-xs">TELEGRAM_BOT_USERNAME</code> в .env бэкенда
              или <code className="text-xs">NEXT_PUBLIC_TELEGRAM_BOT_USERNAME</code> во фронтенде.
            </p>
          )}
        </div>

        {loading && (
          <p className="mt-4 text-center text-sm text-zinc-500">Авторизуем…</p>
        )}

        {error && (
          <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-center text-sm text-red-700 dark:bg-red-950 dark:text-red-400">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
