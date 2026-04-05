import { createClient } from "@supabase/supabase-js";

const DEV_MODE = import.meta.env.VITE_DEV_MODE === "true";

const supabaseUrl =
  (import.meta.env.VITE_SUPABASE_URL as string) || "http://localhost:54321";
const supabaseAnonKey =
  (import.meta.env.VITE_SUPABASE_ANON_KEY as string) || "placeholder";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers ?? {}),
  };

  // In dev mode, skip auth header — backend accepts unauthenticated requests
  if (!DEV_MODE) {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (session?.access_token) {
      (headers as Record<string, string>)["Authorization"] =
        `Bearer ${session.access_token}`;
    }
  }

  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new ApiError(response.status, text);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return response.json() as Promise<T>;
}
