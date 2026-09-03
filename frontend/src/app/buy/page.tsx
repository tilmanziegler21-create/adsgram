"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { api, ApiError, type Channel } from "@/lib/api";
import { useUser } from "@/lib/user-context";

function BuyForm() {
  const searchParams = useSearchParams();
  const id = searchParams.get("channel") ?? "";
  const { user, refresh } = useUser();
  const router = useRouter();

  const [channel, setChannel] = useState<Channel | null>(null);
  const [duration, setDuration] = useState(24);
  const [postText, setPostText] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (!id) {
      setLoading(false);
      return;
    }
    api
      .getChannel(id)
      .then(setChannel)
      .catch(() => setChannel(null))
      .finally(() => setLoading(false));
  }, [id]);

  const selectedPrice = channel?.pricing.find((p) => p.duration_hours === duration)?.price;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!user) {
      router.push("/login");
      return;
    }
    if (!channel || !selectedPrice) return;

    setError("");
    setSuccess("");
    setSubmitting(true);

    try {
      const order = await api.createOrder({
        advertiser_user_id: user.id,
        channel_id: channel.id,
        post_text: postText.trim(),
        duration_hours: duration,
      });
      await api.payOrder(order.id, user.id);
      await refresh();
      setSuccess(
        "Заказ оплачен! Владелец канала получил запрос в Telegram. После подтверждения пост будет опубликован автоматически.",
      );
      setPostText("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось оформить заказ");
    } finally {
      setSubmitting(false);
    }
  }

  if (!id) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="text-lg font-medium">Канал не указан</p>
        <Link href="/" className="mt-4 inline-block text-blue-600 hover:underline">
          ← В каталог
        </Link>
      </div>
    );
  }

  if (loading) {
    return <div className="mx-auto max-w-2xl px-4 py-16 text-center text-zinc-500">Загрузка…</div>;
  }

  if (!channel) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="text-lg font-medium">Канал не найден</p>
        <Link href="/" className="mt-4 inline-block text-blue-600 hover:underline">
          ← В каталог
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300">
        ← Каталог
      </Link>

      <header className="mt-4 mb-8">
        <h1 className="text-3xl font-bold">{channel.title}</h1>
        {channel.username && <p className="mt-1 text-zinc-500">@{channel.username}</p>}
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          <span>⭐ {channel.rating.toFixed(1)}</span>
          <span>{channel.subscribers_count.toLocaleString("ru-RU")} подписчиков</span>
          <span>{channel.completed_orders} успешных сделок</span>
        </div>
      </header>

      <form
        onSubmit={onSubmit}
        className="space-y-6 rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div>
          <label className="mb-2 block text-sm font-medium">Срок размещения</label>
          <div className="grid gap-2 sm:grid-cols-3">
            {channel.pricing.map((option) => (
              <button
                key={option.duration_hours}
                type="button"
                onClick={() => setDuration(option.duration_hours)}
                className={`rounded-xl border px-4 py-3 text-left text-sm transition ${
                  duration === option.duration_hours
                    ? "border-blue-600 bg-blue-50 ring-2 ring-blue-600 dark:bg-blue-950"
                    : "border-zinc-200 hover:border-zinc-300 dark:border-zinc-700"
                }`}
              >
                <div className="font-medium">{option.label}</div>
                <div className="text-zinc-500">{option.price.toLocaleString("ru-RU")} ₽</div>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label htmlFor="post" className="mb-2 block text-sm font-medium">
            Текст рекламного поста
          </label>
          <textarea
            id="post"
            required
            rows={8}
            maxLength={4096}
            value={postText}
            onChange={(e) => setPostText(e.target.value)}
            placeholder="Напишите текст, который увидят подписчики канала…"
            className="w-full resize-y rounded-xl border border-zinc-300 bg-white px-4 py-3 text-sm outline-none ring-blue-500 focus:ring-2 dark:border-zinc-700 dark:bg-zinc-950"
          />
          <p className="mt-1 text-xs text-zinc-500">{postText.length} / 4096</p>
        </div>

        <div className="flex items-center justify-between rounded-xl bg-zinc-50 px-4 py-3 dark:bg-zinc-800">
          <span className="text-sm text-zinc-600 dark:text-zinc-400">К оплате</span>
          <span className="text-xl font-bold">{selectedPrice?.toLocaleString("ru-RU")} ₽</span>
        </div>

        {!user && (
          <p className="text-sm text-amber-700 dark:text-amber-400">
            <Link href="/login" className="underline">
              Войдите
            </Link>
            , чтобы оплатить заказ.
          </p>
        )}

        {user && user.balance < (selectedPrice ?? 0) && (
          <p className="text-sm text-red-600">
            Недостаточно средств.{" "}
            <Link href="/wallet" className="underline">
              Пополните баланс
            </Link>
            .
          </p>
        )}

        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">
            {error}
          </p>
        )}

        {success && (
          <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400">
            {success}
          </p>
        )}

        <button
          type="submit"
          disabled={
            submitting || !user || (selectedPrice !== undefined && user.balance < selectedPrice)
          }
          className="w-full rounded-xl bg-blue-600 py-3.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Оформляем…" : "Оплатить и отправить на модерацию"}
        </button>
      </form>
    </div>
  );
}

export default function BuyPage() {
  return (
    <Suspense fallback={<div className="py-16 text-center text-zinc-500">Загрузка…</div>}>
      <BuyForm />
    </Suspense>
  );
}
