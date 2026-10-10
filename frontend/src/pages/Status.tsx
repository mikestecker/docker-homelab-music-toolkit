import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { StatusResponse } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";
import { useApiError } from "../hooks/useApiError";

function fmtTime(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export default function StatusPage() {
  const { error, run } = useApiError();
  const [status, setStatus] = useState<StatusResponse | null>(null);

  const load = () => run(() => api.get<StatusResponse>("/api/status")).then((r) => r && setStatus(r));

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <h2>Status</h2>
      <ErrorBanner message={error} />

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Navidrome</h3>
        {status ? (
          <table>
            <tbody>
              <tr>
                <th>Reachable</th>
                <td>
                  <span className={`chip ${status.navidrome.reachable ? "good" : "bad"}`}>
                    {status.navidrome.reachable ? "yes" : "no"}
                  </span>
                </td>
              </tr>
              <tr>
                <th>Subsonic API version</th>
                <td>{status.navidrome.version ?? "—"}</td>
              </tr>
              <tr>
                <th>Server</th>
                <td>{status.navidrome.server_version ?? "—"}</td>
              </tr>
              <tr>
                <th>Playlist count</th>
                <td>{status.navidrome.playlist_count ?? "—"}</td>
              </tr>
              {status.navidrome.error && (
                <tr>
                  <th>Error</th>
                  <td className="muted">{status.navidrome.error}</td>
                </tr>
              )}
            </tbody>
          </table>
        ) : (
          <p className="muted">Loading…</p>
        )}
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>AudioMuse</h3>
        {status && (
          <span className={`chip ${status.audiomuse.reachable ? "good" : "bad"}`}>
            {status.audiomuse.reachable ? "reachable" : "unreachable"}
          </span>
        )}
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Scheduled jobs</h3>
        <table>
          <thead>
            <tr>
              <th>Job</th>
              <th>Enabled</th>
              <th>Next run</th>
              <th>Last run</th>
            </tr>
          </thead>
          <tbody>
            {status?.jobs.map((j) => (
              <tr key={j.id}>
                <td>{j.label}</td>
                <td>
                  <span className={`chip ${j.enabled ? "good" : "warn"}`}>{j.enabled ? "on" : "off"}</span>
                </td>
                <td>{fmtTime(j.next_run)}</td>
                <td>
                  {j.last_run ? (
                    <span className={`chip ${j.last_run.status === "ok" ? "good" : j.last_run.status === "error" ? "bad" : "warn"}`}>
                      {j.last_run.status}
                    </span>
                  ) : (
                    <span className="muted">never run</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
