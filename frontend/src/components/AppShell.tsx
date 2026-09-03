import { Header } from "@/components/Header";
import { UserProvider } from "@/lib/user-context";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <UserProvider>
      <Header />
      <main className="flex-1">{children}</main>
      <footer className="border-t border-violet-100 py-8 text-center text-sm text-zinc-500 dark:border-violet-900/40">
        Adsgram — реклама в Telegram-каналах
      </footer>
    </UserProvider>
  );
}
