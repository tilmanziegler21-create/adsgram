/** Bot username for Telegram Login Widget — без @ и пробелов */
export function normalizeBotUsername(value: string | null | undefined): string {
  return (value ?? "").trim().replace(/^@+/, "").trim();
}
