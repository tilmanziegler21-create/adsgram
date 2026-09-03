"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser, userDisplayName } from "@/lib/user-context";

const nav = [
  { href: "/", label: "Каталог" },
  { href: "/add-channel/", label: "Мой канал" },
  { href: "/orders", label: "Заказы" },
  { href: "/wallet", label: "Баланс" },
];

export function Header() {
  const { user, logout } = useUser();
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-violet-200/50 bg-white/80 backdrop-blur-xl dark:border-violet-900/30 dark:bg-[#0c0a12]/80">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
        <Link href="/" className="group flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 text-sm font-bold text-white shadow-md shadow-violet-500/25">
            Ag
          </span>
          <span className="text-lg font-bold tracking-tight">
            Ads<span className="text-violet-600 dark:text-violet-400">gram</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 sm:flex">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-lg px-3.5 py-2 text-sm transition ${
                pathname === item.href
                  ? "bg-violet-100 font-medium text-violet-900 dark:bg-violet-950 dark:text-violet-200"
                  : "text-zinc-600 hover:bg-violet-50 hover:text-violet-800 dark:text-zinc-400 dark:hover:bg-violet-950/50"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          {user ? (
            <>
              <span className="hidden text-sm text-zinc-500 sm:inline">
                {userDisplayName(user)}
              </span>
              <Link
                href="/wallet"
                className="rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm"
              >
                {user.balance.toLocaleString("ru-RU")} ₽
              </Link>
              <button
                type="button"
                onClick={logout}
                className="text-sm text-zinc-500 hover:text-violet-700 dark:hover:text-violet-300"
              >
                Выйти
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-violet-500/20 hover:opacity-90"
            >
              Войти
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
