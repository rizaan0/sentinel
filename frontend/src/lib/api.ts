import axios from "axios";

/**
 * Shared API client. All backend calls go through this instance so that
 * base URL, auth headers, and error handling stay centralized in one place
 * (Frontend never contains business rules; it only calls backend services).
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

export const WS_BASE_URL: string =
  import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";
