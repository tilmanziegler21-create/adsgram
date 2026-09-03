export type TelegramWebAppUser = {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
};

export type TelegramWebApp = {
  initData: string;
  initDataUnsafe: { user?: TelegramWebAppUser };
  ready: () => void;
  expand: () => void;
  close: () => void;
  platform: string;
};

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp };
  }
}

export function getTelegramWebApp(): TelegramWebApp | null {
  if (typeof window === "undefined") return null;
  return window.Telegram?.WebApp ?? null;
}

export function loadTelegramWebAppScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.Telegram?.WebApp) return Promise.resolve();

  return new Promise((resolve, reject) => {
    const existing = document.querySelector('script[src*="telegram-web-app.js"]');
    if (existing) {
      existing.addEventListener("load", () => resolve());
      return;
    }
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-web-app.js";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Telegram WebApp SDK"));
    document.head.appendChild(script);
  });
}

export function isInsideTelegramWebApp(): boolean {
  const tg = getTelegramWebApp();
  return Boolean(tg?.initData);
}
