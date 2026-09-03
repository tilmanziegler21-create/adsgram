"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { TelegramLogin, type TelegramAuthUser } from "@/components/TelegramLogin";
import { ApiError, api } from "@/lib/api";
import { normalizeBotUsername } from "@/lib/telegram";
import {
  getTelegramWebApp,
  isInsideTelegramWebApp,
  loadTelegramWebAppScript,
} from "@/lib/telegram-webapp";
import { useUser } from "@/lib/user-context";

export default function LoginPage() {
  const { user, loginWithTelegram, loginWithWebApp } = useUser();
  const router = useRouter();
  const [botUsername, setBotUsername] = useState("");
  const [botLink, setBotLink] = useState("");
  const [inTelegram, setInTelegram] = useState(false);
  const [configError, setConfigError] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTelegramWebAppScript()
      .then(() => {
        const tg = getTelegramWebApp();
        tg?.ready();
        tg?.expand();
        setInTelegram(isInsideTelegramWebApp());
      })
      .catch(() => {});

    const fromEnv = normalizeBotUsername(process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME);
    if (fromEnv) {
      setBotUsername(fromEnv);
      setBotLink(`https://t.me/${fromEnv}`);
    }

    api
      .getAuthConfig()
      .then((cfg) => {
        const name = normalizeBotUsername(cfg.bot_username);
        if (name) setBotUsername(name);
        if (cfg.bot_link) setBotLink(cfg.bot_link);
        if (!name) {
          setConfigError("Проверьте TELEGRAM_BOT_TOKEN на сервере.");
        }
      })
      .catch(() => {
        setConfigError("API недоступен. Проверьте деплой.");
      });
  }, []);

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

  useEffect(() => {
    if (user) return;
    const tg = getTelegramWebApp();
    if (!tg?.initData) return;

    setLoading(true);
    loginWithWebApp(tg.initData)
      .then(() => router.push("/"))
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Ошибка входа через Telegram");
      })
      .finally(() => setLoading(false));
  }, [user, loginWithWebApp, router]);

  if (user) {
    router.replace("/");
    return null;
  }

  return (
    <div className="mx-auto flex max-w-md flex-col px-4 py-16">
      <div className="rounded-2xl border border-violet-200/60 bg-white p-8 shadow-lg shadow-violet-500/5 dark:border-violet-900/40 dark:bg-zinc-900">
        <h1 className="text-center text-2xl font-bold">Вход в Adsgram</h1>

        {inTelegram ? (
          <p className="mt-2 text-center text-sm text-zinc-500">
            Вход через Telegram…
          </p>
        ) : (
          <>
            <p className="mt-2 text-center text-sm text-zinc-500">
              На Render без своего домена виджет может не работать. Войдите через бота:
            </p>
            {botLink && (
              <a
                href={botLink}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 flex w-full items-center justify-center rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3 text-sm font-semibold text-white"
              >
                Открыть {botUsername ? `@${botUsername}` : "бота"} → Войти
              </a>
            )}
            <p className="mt-4 text-center text-xs text-zinc-400">
              В боте нажмите кнопку «Войти» — откроется мини-приложение.
            </p>
            <div className="my-6 border-t border-zinc-200 dark:border-zinc-800" />
            <p className="text-center text-xs text-zinc-500">Или через виджет (нужен свой домен):</p>
            <div className="mt-4">
              {botUsername ? (
                <div className={loading ? "pointer-events-none opacity-60" : ""}>
                  <TelegramLogin botUsername={botUsername} onAuth={handleAuth} />
                </div>
              ) : configError ? (
                <p className="rounded-xl bg-amber-50 px-4 py-3 text-center text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                  {configError}
                </p>
              ) : (
                <p className="text-center text-sm text-zinc-500">Загружаем…</p>
              )}
            </div>
          </>
        )}

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
