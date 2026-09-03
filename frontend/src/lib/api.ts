import { getApiBase } from "./api-base";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new ApiError(String(detail), res.status);
  }
  return res.json() as Promise<T>;
}

export type PricingOption = {
  duration_hours: number;
  label: string;
  price: number;
};

export type Channel = {
  id: string;
  title: string;
  username: string | null;
  subscribers_count: number;
  rating: number;
  completed_orders: number;
  total_orders: number;
  pricing: PricingOption[];
  stats: Record<string, unknown> | null;
};

export type AdOrder = {
  id: string;
  channel_id: string;
  advertiser_user_id: string;
  post_text: string;
  duration_hours: number;
  price: number;
  status: string;
  published_message_id: number | null;
  published_at: string | null;
  expires_at: string | null;
};

export type UserProfile = {
  id: string;
  telegram_id: string;
  telegram_username: string | null;
  telegram_first_name: string | null;
  balance: number;
};

export type WalletTransaction = {
  id: string;
  amount: number;
  kind: string;
  description: string | null;
  reference_id: string | null;
  created_at: string | null;
};

export const api = {
  getAuthConfig: () =>
    request<{ bot_username: string | null; bot_link: string | null }>("/api/auth/config"),

  telegramWebAppLogin: (initData: string) =>
    request<UserProfile>("/api/auth/telegram-webapp", {
      method: "POST",
      body: JSON.stringify({ init_data: initData }),
    }),

  telegramLogin: (data: {
    id: number;
    first_name: string;
    last_name?: string;
    username?: string;
    photo_url?: string;
    auth_date: number;
    hash: string;
  }) =>
    request<UserProfile>("/api/auth/telegram", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getProfile: (userId: string) =>
    request<UserProfile>(`/api/auth/me?user_id=${userId}`),

  getChannels: () => request<Channel[]>("/api/marketplace/channels"),

  getConnectInfo: () =>
    request<{ bot_username: string | null; add_bot_url: string | null }>(
      "/api/marketplace/channels/connect-info",
    ),

  getMyChannels: (userId: string) =>
    request<Channel[]>(`/api/marketplace/channels/mine?user_id=${userId}`),

  connectChannel: (userId: string, channelUsername: string) =>
    request<Channel>("/api/marketplace/channels/connect", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, channel_username: channelUsername }),
    }),

  getChannel: (id: string) => request<Channel>(`/api/marketplace/channels/${id}`),

  createOrder: (data: {
    advertiser_user_id: string;
    channel_id: string;
    post_text: string;
    duration_hours: number;
  }) =>
    request<AdOrder>("/api/marketplace/orders", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  payOrder: (orderId: string, advertiserUserId: string) =>
    request<AdOrder>(
      `/api/marketplace/orders/${orderId}/pay?advertiser_user_id=${advertiserUserId}`,
      { method: "POST" },
    ),

  getOrders: (userId: string) =>
    request<AdOrder[]>(`/api/marketplace/orders?user_id=${userId}`),

  topupTest: (userId: string, amount: number) =>
    request<{ user_id: string; balance: number }>("/api/wallet/topup-test", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, amount }),
    }),

  getTransactions: (userId: string) =>
    request<WalletTransaction[]>(`/api/wallet/transactions?user_id=${userId}`),
};
