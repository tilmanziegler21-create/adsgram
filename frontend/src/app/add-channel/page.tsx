"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, api, type Channel } from "@/lib/api";
import { useUser } from "@/lib/user-context";

type ConnectInfo = {
  bot_username: string | null;
  add_bot_url: string | null;
};

export default function AddChannelPage() {
  const { user, loading: userLoading } = useUser();
  const [info, setInfo] = useState<ConnectInfo | null>(null);
  const [myChannels, setMyChannels] = useState<Channel[]>([]);
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    if (!user) return;
    const [connectInfo, channels] = await Promise.all([
      api.getConnectInfo(),
      api.getMyChannels(user.id),
    ]);
    setInfo(connectInfo);
    setMyChannels(channels);
  }, [user]);

  useEffect(() => {
    loadData().catch(() => {});
  }, [loadData]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!user) return;
    setError("");
    setSuccess("");
    setSubmitting(true);
    try {
      const channel = await api.connectChannel(user.id, username.trim());
      setSuccess(`Канал «${channel.title}» подключён и появился в каталоге.`);
      setUsername("");
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось подключить канал");
    } finally {
      setSubmitting(false);
    }
  }

  if (userLoading) {
    return <p className="px-4 py-16 text-center text-zinc-500">Загрузка…</p>;
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <h1 className="text-2xl font-bold">Добавить канал</h1>
        <p className="mt-3 text-zinc-500">Войдите через Telegram, чтобы подключить свой канал.</p>
        <Link
          href="/login/"
          className="mt-6 inline-block rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-3 text-sm font-semibold text-white"
        >
          Войти
        </Link>
      </div>
    );
  }

  const botLabel = info?.bot_username ? `@${info.bot_username}` : "бота";

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-3xl font-bold">Добавить канал</h1>
      <p className="mt-2 text-zinc-500">
        Подключите Telegram-канал к каталогу Adsgram и начните продавать рекламу.
      </p>

      <div className="mt-8 space-y-4">
        <section className="rounded-2xl border border-violet-200/60 bg-white p-6 dark:border-violet-900/40 dark:bg-zinc-900">
          <h2 className="font-semibold">Шаг 1. Добавьте бота в канал</h2>
          <ol className="mt-3 list-inside list-decimal space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
            <li>Откройте настройки канала → Администраторы</li>
            <li>Добавьте {botLabel} как администратора</li>
            <li>Включите право «Публиковать сообщения»</li>
          </ol>
          {info?.add_bot_url && (
            <a
              href={info.add_bot_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-flex rounded-xl bg-[#2AABEE] px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90"
            >
              Добавить {botLabel} в канал
            </a>
          )}
        </section>

        <section className="rounded-2xl border border-violet-200/60 bg-white p-6 dark:border-violet-900/40 dark:bg-zinc-900">
          <h2 className="font-semibold">Шаг 2. Укажите канал</h2>
          <p className="mt-2 text-sm text-zinc-500">
            Введите @username или ссылку вида t.me/your_channel
          </p>
          <form onSubmit={onSubmit} className="mt-4 space-y-4">
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="@my_channel"
              className="w-full rounded-xl border border-zinc-300 bg-white px-4 py-3 text-sm outline-none ring-violet-500 focus:ring-2 dark:border-zinc-700 dark:bg-zinc-950"
            />
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60"
            >
              {submitting ? "Проверяем…" : "Подключить канал"}
            </button>
          </form>

          {success && (
            <p className="mt-4 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-800 dark:bg-green-950 dark:text-green-300">
              {success}
            </p>
          )}
          {error && (
            <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">
              {error}
            </p>
          )}
        </section>

        {myChannels.length > 0 && (
          <section className="rounded-2xl border border-violet-200/60 bg-white p-6 dark:border-violet-900/40 dark:bg-zinc-900">
            <h2 className="font-semibold">Ваши каналы</h2>
            <ul className="mt-4 space-y-3">
              {myChannels.map((ch) => (
                <li
                  key={ch.id}
                  className="flex items-center justify-between rounded-xl bg-violet-50 px-4 py-3 dark:bg-violet-950/30"
                >
                  <div>
                    <p className="font-medium">{ch.title}</p>
                    <p className="text-sm text-zinc-500">
                      {ch.username ? `@${ch.username}` : "без username"} ·{" "}
                      {ch.subscribers_count.toLocaleString("ru-RU")} подп.
                    </p>
                  </div>
                  <Link
                    href="/"
                    className="text-sm font-medium text-violet-600 hover:underline dark:text-violet-400"
                  >
                    В каталоге
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
