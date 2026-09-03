"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, ApiError, type WalletTransaction } from "@/lib/api";
import { useUser } from "@/lib/user-context";

export default function WalletPage() {
  const { user, refresh, loading: userLoading } = useUser();
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [amount, setAmount] = useState(5000);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (!user) return;
    api.getTransactions(user.id).then(setTransactions);
  }, [user]);

  async function onTopup(e: FormEvent) {
    e.preventDefault();
    if (!user) return;
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await api.topupTest(user.id, amount);
      await refresh();
      const txs = await api.getTransactions(user.id);
      setTransactions(txs);
      setSuccess(`Баланс пополнен на ${amount.toLocaleString("ru-RU")} ₽`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка пополнения");
    } finally {
      setLoading(false);
    }
  }

  if (userLoading) {
    return <div className="mx-auto max-w-lg px-4 py-16 text-center text-zinc-500">Загрузка…</div>;
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <p className="mb-4">Войдите для управления балансом</p>
        <Link href="/login" className="text-blue-600 hover:underline">
          Войти
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      <h1 className="text-2xl font-bold">Баланс</h1>

      <div className="mt-6 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-800 p-6 text-white">
        <p className="text-sm text-blue-100">Доступно</p>
        <p className="mt-1 text-4xl font-bold">{user.balance.toLocaleString("ru-RU")} ₽</p>
        <p className="mt-2 text-xs text-blue-200">Тестовые кредиты (development)</p>
      </div>

      <form onSubmit={onTopup} className="mt-8 space-y-4 rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="font-medium">Тестовое пополнение</h2>
        <div className="flex flex-wrap gap-2">
          {[1000, 5000, 10000].map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setAmount(v)}
              className={`rounded-lg border px-3 py-1.5 text-sm ${
                amount === v
                  ? "border-blue-600 bg-blue-50 dark:bg-blue-950"
                  : "border-zinc-200 dark:border-zinc-700"
              }`}
            >
              +{v.toLocaleString("ru-RU")} ₽
            </button>
          ))}
        </div>
        <input
          type="number"
          min={100}
          step={100}
          value={amount}
          onChange={(e) => setAmount(Number(e.target.value))}
          className="w-full rounded-xl border border-zinc-300 px-4 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        {success && <p className="text-sm text-emerald-600">{success}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-emerald-600 py-2.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
        >
          {loading ? "Пополняем…" : "Пополнить"}
        </button>
      </form>

      {transactions.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-3 font-medium">История</h2>
          <ul className="space-y-2">
            {transactions.map((tx) => (
              <li
                key={tx.id}
                className="flex items-center justify-between rounded-xl border border-zinc-200 px-4 py-3 text-sm dark:border-zinc-800"
              >
                <span className="text-zinc-600 dark:text-zinc-400">
                  {tx.description ?? tx.kind}
                </span>
                <span className={tx.amount >= 0 ? "text-emerald-600" : "text-red-600"}>
                  {tx.amount >= 0 ? "+" : ""}
                  {tx.amount.toLocaleString("ru-RU")} ₽
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
