import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

// Built into the backend so anyone can try the app without registering
export const DEMO = { email: "demo@example.com", password: "password123" };

export default function SignIn() {
  const { user, loading, signIn, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (loading) return <p className="loading">Checking your session…</p>;
  if (user) return <Navigate to="/products" replace />;

  const registering = mode === "register";
  const goNext = () => navigate(location.state?.from?.pathname || "/products", { replace: true });

  // Runs a server call, showing its error message if it fails
  const attempt = async (action) => {
    setBusy(true);
    setError("");
    try {
      await action();
      goNext();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  const submit = (e) => {
    e.preventDefault();
    if (!/^\S+@\S+\.\S+$/.test(email)) return setError("Enter a valid email address.");
    if (password.length < 6) return setError("Password must be at least 6 characters.");
    if (registering && confirm !== password) return setError("Passwords do not match.");
    attempt(() => (registering ? register(email.trim(), password, confirm) : signIn(email.trim(), password)));
  };

  const useDemo = () => attempt(() => signIn(DEMO.email, DEMO.password));

  const switchMode = () => {
    setMode(registering ? "signin" : "register");
    setConfirm("");
    setError("");
  };

  return (
    <main className="auth">
      <h1>Stockroom</h1>
      <p className="sub">{registering ? "Create an account to manage products." : "Sign in to manage your products."}</p>
      <form onSubmit={submit} noValidate>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                 autoComplete={registering ? "new-password" : "current-password"} />
        </label>
        {registering && (
          <label>
            Confirm password
            <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
          </label>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Please wait…" : registering ? "Create account" : "Sign in"}
        </button>
      </form>
      <p className="hint">
        {registering ? "Already have an account? " : "New here? "}
        <button type="button" className="link" onClick={switchMode}>
          {registering ? "Sign in" : "Create an account"}
        </button>
      </p>
      <div className="demo">
        <button type="button" onClick={useDemo} disabled={busy}>Try the demo account</button>
        <p className="hint">{DEMO.email} / {DEMO.password}</p>
      </div>
    </main>
  );
}
