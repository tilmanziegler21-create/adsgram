"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type AdOrder } from "@/lib/api";
import { useUser } from "@/lib/user-context";

const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  pending_payment: "Ожидает оплаты",
  awaiting_owner: "На модерации у владельца",
  approved: "Одобрен",
  published: "Опубликован",
  rejected: "Отклонён",
  cancelled: "Отменён",
  failed: "Ошибка",
};

const STATUS_COLORS: Record<string, string> = {
  awaiting_owner: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  published: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  rejected: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
};

export default function OrdersPage() {
  const { user, loading: userLoading } = useUser();
  const [orders, setOrders] = useState<AdOrder[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    api.getOrders(user.id).then(setOrders).finally(() => setLoading(false));
  }, [user]);

  if (userLoading || loading) {
    return <div className="mx-auto max-w-3xl px-4 py-16 text-center text-zinc-500">Загрузка…</div>;
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p className="mb-4">Войдите, чтобы видеть заказы</p>
        <Link href="/login" className="text-blue-600 hover:underline">
          Войти
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-bold">Мои заказы</h1>

      {orders.length === 0 ? (
        <p className="mt-8 text-zinc-500">Заказов пока нет</p>
      ) : (
        <ul className="mt-6 space-y-4">
          {orders.map((order) => (
            <li
              key={order.id}
              className="rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900"
            >
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm text-zinc-500">
                  {new Date(order.published_at ?? Date.now()).toLocaleDateString("ru-RU")}
                </span>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    STATUS_COLORS[order.status] ?? "bg-zinc-100 text-zinc-700 dark:bg-zinc-800"
                  }`}
                >
                  {STATUS_LABELS[order.status] ?? order.status}
                </span>
              </div>
              <p className="line-clamp-3 text-sm whitespace-pre-wrap">{order.post_text}</p>
              <div className="mt-3 flex gap-4 text-sm text-zinc-500">
                <span>{order.duration_hours} ч</span>
                <span>{order.price.toLocaleString("ru-RU")} ₽</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
