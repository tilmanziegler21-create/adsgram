import Link from "next/link";
import type { Channel } from "@/lib/api";

function formatSubs(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString("ru-RU");
}

export function ChannelCard({ channel }: { channel: Channel }) {
  const minPrice = Math.min(...channel.pricing.map((p) => p.price));
  const tgLink = channel.username ? `https://t.me/${channel.username}` : null;
  const initial = channel.title.charAt(0).toUpperCase();

  return (
    <article className="group relative flex flex-col overflow-hidden rounded-2xl border border-violet-100 bg-white shadow-sm transition hover:-translate-y-0.5 hover:border-violet-300 hover:shadow-lg hover:shadow-violet-500/10 dark:border-violet-900/40 dark:bg-[#15121f] dark:hover:border-violet-700">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-violet-500 to-indigo-500 opacity-0 transition group-hover:opacity-100" />

      <div className="p-5">
        <div className="mb-4 flex items-start gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 text-lg font-bold text-white">
            {initial}
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="truncate font-semibold leading-tight">{channel.title}</h2>
            {channel.username && (
              <p className="mt-0.5 text-sm text-violet-600 dark:text-violet-400">
                @{channel.username}
              </p>
            )}
          </div>
          <div className="rounded-lg bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-950 dark:text-amber-400">
            ★ {channel.rating.toFixed(1)}
          </div>
        </div>

        <div className="mb-4 grid grid-cols-2 gap-2">
          <div className="rounded-xl bg-violet-50 px-3 py-2 dark:bg-violet-950/50">
            <p className="text-xs text-zinc-500">Подписчики</p>
            <p className="font-semibold">{formatSubs(channel.subscribers_count)}</p>
          </div>
          <div className="rounded-xl bg-violet-50 px-3 py-2 dark:bg-violet-950/50">
            <p className="text-xs text-zinc-500">Сделок</p>
            <p className="font-semibold">{channel.completed_orders}</p>
          </div>
        </div>

        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          от{" "}
          <span className="text-lg font-bold text-violet-700 dark:text-violet-300">
            {minPrice.toLocaleString("ru-RU")} ₽
          </span>
        </p>
      </div>

      <div className="mt-auto flex gap-2 border-t border-violet-100 p-4 dark:border-violet-900/40">
        <Link
          href={`/buy?channel=${channel.id}`}
          className="flex-1 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-2.5 text-center text-sm font-semibold text-white transition hover:opacity-90"
        >
          Купить рекламу
        </Link>
        {tgLink && (
          <a
            href={tgLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center rounded-xl border border-violet-200 px-3 text-violet-600 hover:bg-violet-50 dark:border-violet-800 dark:hover:bg-violet-950"
            aria-label="Открыть в Telegram"
          >
            ↗
          </a>
        )}
      </div>
    </article>
  );
}
