const WS_BASE_URL: string = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

export function adminLiveFeedUrl(token: string): string {
  return `${WS_BASE_URL}/ws/admin/live?token=${encodeURIComponent(token)}`;
}
