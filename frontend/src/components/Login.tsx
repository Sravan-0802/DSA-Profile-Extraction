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
  const [loading, setLoading] = useState(false);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    setTimeout(() => {
      if (username === ADMIN_USER && password === ADMIN_PASS) {
        sessionStorage.setItem(AUTH_KEY, "1");
        onSuccess();
      } else {
        setError("Invalid username or password");
        setLoading(false);
      }
    }, 300);
  }

  return (
    <div style={styles.page}>
      {/* Background grid pattern */}
      <div style={styles.grid} aria-hidden="true" />

      <div style={styles.card}>
        {/* Logo mark */}
        <div style={styles.logoWrap}>
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="#4f8cff" />
            <path d="M7 14h14M14 7l7 7-7 7" stroke="#fff" strokeWidth="2.2"
              strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>

        <h1 style={styles.title}>DSA Profile Extraction</h1>
        <p style={styles.sub}>Admin access only — sign in to continue</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.fieldGroup}>
            <label htmlFor="username" style={styles.label}>Username</label>
            <div style={styles.inputWrap}>
              <svg style={styles.inputIcon} viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="5.5" r="2.5" stroke="currentColor" strokeWidth="1.4" />
                <path d="M2.5 13c0-2.485 2.462-4.5 5.5-4.5s5.5 2.015 5.5 4.5"
                  stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
              </svg>
              <input
                id="username"
                type="text"
                autoComplete="username"
                placeholder="Enter username"
                value={username}
                onChange={(e) => { setUsername(e.target.value); setError(""); }}
                style={styles.input}
                onFocus={e => Object.assign(e.currentTarget.style, styles.inputFocus)}
                onBlur={e => Object.assign(e.currentTarget.style, styles.inputBlur)}
              />
            </div>
          </div>

          <div style={styles.fieldGroup}>
            <label htmlFor="password" style={styles.label}>Password</label>
            <div style={styles.inputWrap}>
              <svg style={styles.inputIcon} viewBox="0 0 16 16" fill="none">
                <rect x="3" y="7" width="10" height="7" rx="2" stroke="currentColor" strokeWidth="1.4" />
                <path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
              </svg>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(""); }}
                style={styles.input}
                onFocus={e => Object.assign(e.currentTarget.style, styles.inputFocus)}
                onBlur={e => Object.assign(e.currentTarget.style, styles.inputBlur)}
              />
            </div>
          </div>

          {error && (
            <div style={styles.errorBox} role="alert">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
                <circle cx="8" cy="8" r="6.5" stroke="#e5534b" strokeWidth="1.4" />
                <path d="M8 5v3.5M8 11v.5" stroke="#e5534b" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !username || !password}
            style={{
              ...styles.btn,
              ...(loading || !username || !password ? styles.btnDisabled : {}),
            }}
          >
            {loading ? (
              <span style={styles.spinner} />
            ) : (
              <>
                Sign in
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ marginLeft: 6 }}>
                  <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.8"
                    strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </>
            )}
          </button>
        </form>

        <p style={styles.footer}>Resume Intelligence Tool · Internal</p>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
      `}</style>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "linear-gradient(135deg, #0a0f1a 0%, #0f1728 60%, #111e35 100%)",
    padding: "24px 16px",
    position: "relative",
    overflow: "hidden",
  },
  grid: {
    position: "absolute",
    inset: 0,
    backgroundImage:
      "linear-gradient(rgba(79,140,255,0.05) 1px, transparent 1px)," +
      "linear-gradient(90deg, rgba(79,140,255,0.05) 1px, transparent 1px)",
    backgroundSize: "40px 40px",
    maskImage: "radial-gradient(ellipse 80% 70% at 50% 50%, black 40%, transparent 100%)",
    pointerEvents: "none",
  },
  card: {
    position: "relative",
    width: "100%",
    maxWidth: "420px",
    background: "rgba(22, 30, 46, 0.85)",
    backdropFilter: "blur(20px)",
    border: "1px solid rgba(79,140,255,0.15)",
    borderRadius: "18px",
    padding: "36px 36px 28px",
    boxShadow: "0 24px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04) inset",
    animation: "fadeIn .35s ease both",
  },
  logoWrap: {
    marginBottom: "20px",
  },
  title: {
    margin: "0 0 6px",
    fontSize: "22px",
    fontWeight: 700,
    color: "#e6edf3",
    letterSpacing: "-0.3px",
  },
  sub: {
    margin: "0 0 26px",
    fontSize: "13px",
    color: "#6e7c91",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "0",
  },
  fieldGroup: {
    marginBottom: "18px",
  },
  label: {
    display: "block",
    fontSize: "12px",
    fontWeight: 600,
    color: "#8b98a9",
    marginBottom: "7px",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  inputWrap: {
    position: "relative",
    display: "flex",
    alignItems: "center",
  },
  inputIcon: {
    position: "absolute",
    left: "12px",
    width: "15px",
    height: "15px",
    color: "#4a5568",
    pointerEvents: "none",
    flexShrink: 0,
  },
  input: {
    width: "100%",
    background: "rgba(15, 20, 35, 0.7)",
    border: "1px solid rgba(46, 58, 77, 0.8)",
    borderRadius: "10px",
    color: "#e6edf3",
    padding: "11px 14px 11px 38px",
    fontSize: "14px",
    fontFamily: "inherit",
    outline: "none",
    transition: "border-color 0.2s, box-shadow 0.2s",
    WebkitAppearance: "none",
  },
  inputFocus: {
    borderColor: "rgba(79,140,255,0.6)",
    boxShadow: "0 0 0 3px rgba(79,140,255,0.12)",
    background: "rgba(15, 20, 35, 0.9)",
  },
  inputBlur: {
    borderColor: "rgba(46, 58, 77, 0.8)",
    boxShadow: "none",
    background: "rgba(15, 20, 35, 0.7)",
  },
  errorBox: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    background: "rgba(229,83,75,0.1)",
    border: "1px solid rgba(229,83,75,0.3)",
    color: "#ffb4ae",
    padding: "10px 14px",
    borderRadius: "9px",
    marginBottom: "16px",
    fontSize: "13px",
  },
  btn: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
    marginTop: "4px",
    background: "linear-gradient(135deg, #4f8cff 0%, #3a78ee 100%)",
    color: "#fff",
    border: "none",
    borderRadius: "10px",
    padding: "13px 22px",
    fontSize: "14px",
    fontWeight: 700,
    cursor: "pointer",
    letterSpacing: "0.01em",
    boxShadow: "0 4px 16px rgba(79,140,255,0.3)",
    transition: "opacity 0.15s, transform 0.15s",
  },
  btnDisabled: {
    background: "rgba(46, 58, 77, 0.8)",
    color: "#4a5568",
    boxShadow: "none",
    cursor: "not-allowed",
  },
  spinner: {
    width: "16px",
    height: "16px",
    border: "2px solid rgba(255,255,255,0.3)",
    borderTopColor: "#fff",
    borderRadius: "50%",
    display: "inline-block",
    animation: "spin 0.7s linear infinite",
  },
  footer: {
    marginTop: "24px",
    marginBottom: 0,
    textAlign: "center",
    fontSize: "11px",
    color: "#3a4a5c",
    letterSpacing: "0.03em",
  },
};
