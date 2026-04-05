import { useEffect, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "../api/client";

const DEV_MODE = import.meta.env.VITE_DEV_MODE === "true";

interface AuthState {
  session: Session | null;
  user: User | null;
  loading: boolean;
}

interface UseAuth extends AuthState {
  signUp: (email: string, password: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  isDevMode: boolean;
}

// Fake session/user for dev mode
const DEV_SESSION = {
  access_token: "dev-token",
  token_type: "bearer",
  expires_in: 999999,
  refresh_token: "dev-refresh",
  user: {
    id: "dev-user-00000000",
    email: "dev@growthpilot.local",
    aud: "authenticated",
    role: "authenticated",
    app_metadata: {},
    user_metadata: {},
    created_at: new Date().toISOString(),
  },
} as unknown as Session;

export function useAuth(): UseAuth {
  const [state, setState] = useState<AuthState>({
    session: DEV_MODE ? DEV_SESSION : null,
    user: DEV_MODE ? DEV_SESSION.user : null,
    loading: !DEV_MODE,
  });

  useEffect(() => {
    if (DEV_MODE) return;

    supabase.auth.getSession().then(({ data: { session } }) => {
      setState({ session, user: session?.user ?? null, loading: false });
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setState({ session, user: session?.user ?? null, loading: false });
    });

    return () => subscription.unsubscribe();
  }, []);

  async function signUp(email: string, password: string): Promise<void> {
    if (DEV_MODE) return;
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
  }

  async function signIn(email: string, password: string): Promise<void> {
    if (DEV_MODE) return;
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) throw error;
  }

  async function signOut(): Promise<void> {
    if (DEV_MODE) return;
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  }

  return { ...state, signUp, signIn, signOut, isDevMode: DEV_MODE };
}
