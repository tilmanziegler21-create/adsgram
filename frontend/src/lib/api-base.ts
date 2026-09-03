/** API base URL. Empty string = same-origin /api (Netlify proxy). */
export function getApiBase(): string {
  const pub = process.env.NEXT_PUBLIC_API_URL;

  // Netlify: NEXT_PUBLIC_API_URL="" → запросы на /api/* через redirect
  if (pub === "" || pub === "/") {
    return "";
  }

  if (typeof window === "undefined") {
    return pub ?? process.env.API_URL ?? "http://localhost:8000";
  }

  return pub ?? "http://localhost:8000";
}
