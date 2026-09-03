"use client";

import { useEffect, useRef } from "react";
import { normalizeBotUsername } from "@/lib/telegram";

export type TelegramAuthUser = {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
};

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramAuthUser) => void;
  }
}

type Props = {
  botUsername: string;
  onAuth: (user: TelegramAuthUser) => void;
};

export function TelegramLogin({ botUsername, onAuth }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const onAuthRef = useRef(onAuth);
  onAuthRef.current = onAuth;

  useEffect(() => {
    const container = containerRef.current;
    const login = normalizeBotUsername(botUsername);
    if (!container || !login) return;

    window.onTelegramAuth = (user) => onAuthRef.current(user);

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", login);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "12");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    container.appendChild(script);

    return () => {
      delete window.onTelegramAuth;
      container.replaceChildren();
    };
  }, [botUsername]);

  return <div ref={containerRef} className="flex justify-center" />;
}
