import { useState, type FormEvent } from "react";

const AUTH_KEY = "dsa_admin_authed";
const ADMIN_USER = "Admin";
const ADMIN_PASS = "Nxtwave@2026";

export function isAuthenticated(): boolean {
  try {
    return sessionStorage.getItem(AUTH_KEY) === "1";
  } catch {
    return false;
  }
}

export function clearAuth(): void {
  try {
    sessionStorage.removeItem(AUTH_KEY);
  } catch {
    /* ignore */
  }
}

export default function Login({ onSuccess }: { onSuccess: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (username === ADMIN_USER && password === ADMIN_PASS) {
      sessionStorage.setItem(AUTH_KEY, "1");
      onSuccess();
      return;
    }
    setError("Invalid username or password");
  }

  return (
    <div className="app login-wrap">
      <div className="panel login-panel">
        <h1>DSA Profile Extraction</h1>
        <p className="sub">Admin sign-in required</p>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <div className="error-box">{error}</div>}
          <button className="primary" type="submit">
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}
