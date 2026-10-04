import { createContext, useContext, useEffect, useState } from "react";
import { request, setUnauthorizedHandler } from "../api/client.js";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // { id, email } from the server session
  const [loading, setLoading] = useState(true);

  // Ask the server who is logged in, so a page refresh keeps you signed in
  useEffect(() => {
    request("/auth/me")
      .then((d) => setUser(d.user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
    setUnauthorizedHandler(() => setUser(null));
  }, []);

  const signIn = async (email, password) =>
    setUser((await request("/auth/login", { method: "POST", body: { email, password } })).user);

  const register = async (email, password, confirmPassword) =>
    setUser((await request("/auth/register", {
      method: "POST",
      body: { email, password, confirm_password: confirmPassword },
    })).user);

  const signOut = async () => {
    try { await request("/auth/logout", { method: "POST" }); } catch { /* clear locally anyway */ }
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, signIn, register, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}
