"use client";

import { useEffect, useState } from "react";
import { ChannelCard } from "@/components/ChannelCard";
import { api, type Channel } from "@/lib/api";

export function ChannelCatalog() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getChannels()
      .then(setChannels)
      .catch(() => setError("Не удалось загрузить каталог. Запустите API (порт 8000)."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="gradient-hero">
      <div className="mx-auto max-w-6xl px-4 py-12">
        <section className="mb-12 text-center sm:text-left">
          <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-violet-600 dark:text-violet-400">
            Маркетплейс Telegram
          </p>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            Реклама в каналах
            <span className="block bg-gradient-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent">
              за пару кликов
            </span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg text-zinc-600 sm:mx-0 dark:text-zinc-400">
            Выберите площадку, оплатите с баланса — владелец подтвердит, бот опубликует пост.
          </p>
        </section>

        {loading && (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-64 animate-pulse rounded-2xl bg-violet-100/60 dark:bg-violet-950/40"
              />
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center dark:border-red-900 dark:bg-red-950/50">
            <p className="font-medium text-red-800 dark:text-red-300">{error}</p>
          </div>
        )}

        {!loading && !error && channels.length === 0 && (
          <div className="rounded-2xl border border-dashed border-violet-300 bg-white/60 p-12 text-center dark:border-violet-800 dark:bg-[#15121f]/60">
            <p className="text-xl font-semibold">Пабликов пока нет</p>
            <p className="mt-2 text-zinc-500">
              Добавьте бота Adsgram админом в канал — он появится здесь автоматически.
            </p>
          </div>
        )}

        {channels.length > 0 && (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {channels.map((channel) => (
              <ChannelCard key={channel.id} channel={channel} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
