/**
 * In-memory token storage (never persisted to localStorage — XSS-safe).
 * Tokens survive in-page navigation but not a full page reload.
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setTokens(access: string, refresh: string): void {
  accessToken = access;
  refreshToken = refresh;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return refreshToken;
}

export function clearTokens(): void {
  accessToken = null;
  refreshToken = null;
}

export function isLoggedIn(): boolean {
  return accessToken !== null;
}

const apiUrl = (path: string) =>
  `${(API_BASE_URL ?? "").replace(/\/$/, "")}${path}`;

/**
 * Attempt to refresh the access token.
 *
 * Tries the in-memory refresh token first (if available), then falls
 * back to the ``refresh_token`` HttpOnly cookie so that a page reload
 * does not break token renewal.
 *
 * Returns the new access token string on success, or null on failure.
 */
export async function refreshAccessToken(): Promise<string | null> {
  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const body = refreshToken ? JSON.stringify({ refresh_token: refreshToken }) : undefined;

    const response = await fetch(apiUrl("/api/auth/refresh"), {
      method: "POST",
      headers,
      body,
      credentials: "include",
    });

    if (!response.ok) {
      clearTokens();
      return null;
    }

    const data = await response.json();
    accessToken = data.access_token;
    return accessToken;
  } catch {
    clearTokens();
    return null;
  }
}
