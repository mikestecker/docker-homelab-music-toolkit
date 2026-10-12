import { useState } from "react";
import { api } from "../api/client";
import ErrorBanner from "../components/ErrorBanner";
import { useApiError } from "../hooks/useApiError";

export default function LoginPage({ onSuccess }: { onSuccess: () => void }) {
  const { error, run } = useApiError();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    run(() => api.post<{ ok: boolean }>("/api/auth/login", { username, password }))
      .then((r) => r && onSuccess())
      .finally(() => setBusy(false));
  };

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", width: "100%" }}>
      <form onSubmit={submit} className="panel" style={{ width: 320 }}>
        <h2 style={{ marginTop: 0 }}>Music Toolkit</h2>
        <ErrorBanner message={error} />
        <label>
          Username
          <input type="text" autoFocus value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <div style={{ height: 10 }} />
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <div style={{ height: 14 }} />
        <button className="primary" type="submit" disabled={busy || !username || !password} style={{ width: "100%" }}>
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>
    </div>
  );
}
