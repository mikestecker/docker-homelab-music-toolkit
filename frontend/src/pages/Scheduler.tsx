import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { JobInfo, RunRecord } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";
import LogPanel from "../components/LogPanel";
import { useApiError } from "../hooks/useApiError";

function fmtTime(iso: string | null) {
  return iso ? new Date(iso).toLocaleString() : "—";
}

function fmtUnix(secs: number | null) {
  return secs ? new Date(secs * 1000).toLocaleString() : "—";
}

export default function SchedulerPage() {
  const { error, run } = useApiError();
  const [jobs, setJobs] = useState<JobInfo[]>([]);
  const [history, setHistory] = useState<RunRecord[]>([]);
  const [selected, setSelected] = useState<RunRecord | null>(null);

  const loadJobs = () => run(() => api.get<JobInfo[]>("/api/jobs")).then((r) => r && setJobs(r));
  const loadHistory = () => run(() => api.get<RunRecord[]>("/api/jobs/history")).then((r) => r && setHistory(r));

  useEffect(() => {
    loadJobs();
    loadHistory();
    const t = setInterval(() => {
      loadJobs();
      loadHistory();
    }, 10000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const trigger = (id: string) => run(() => api.post(`/api/jobs/${id}/trigger`)).then(() => {
    setTimeout(() => {
      loadJobs();
      loadHistory();
    }, 500);
  });

  const setSchedule = (id: string, patch: Partial<{ enabled: boolean; hour: number; minute: number }>) =>
    run(() => api.put(`/api/jobs/${id}/schedule`, patch)).then(() => loadJobs());

  return (
    <div>
      <h2>Scheduler</h2>
      <p className="muted">
        Replaces the TrueNAS cron jobs for cluster cleanup and Tidarr filing. A scheduled run always applies for
        real - previewing on a timer would just silently do nothing.
      </p>
      <ErrorBanner message={error} />

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Job</th>
              <th>Enabled</th>
              <th>Time (UTC-offset of container TZ)</th>
              <th>Next run</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id}>
                <td>{j.label}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={j.enabled}
                    onChange={(e) => setSchedule(j.id, { enabled: e.target.checked })}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min={0}
                    max={23}
                    style={{ width: 50 }}
                    value={j.hour ?? 0}
                    onChange={(e) => setSchedule(j.id, { hour: Number(e.target.value) })}
                  />
                  :
                  <input
                    type="number"
                    min={0}
                    max={59}
                    style={{ width: 50 }}
                    value={j.minute ?? 0}
                    onChange={(e) => setSchedule(j.id, { minute: Number(e.target.value) })}
                  />
                </td>
                <td>{fmtTime(j.next_run)}</td>
                <td>
                  <button onClick={() => trigger(j.id)}>Run now</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Run history</h3>
        <table>
          <thead>
            <tr>
              <th>Job</th>
              <th>Trigger</th>
              <th>Started</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {history.map((r) => (
              <tr key={r.id}>
                <td>{r.job_id}</td>
                <td>{r.trigger}</td>
                <td>{new Date(r.started * 1000).toLocaleString()}</td>
                <td>
                  <span className={`chip ${r.status === "ok" ? "good" : r.status === "error" ? "bad" : "warn"}`}>
                    {r.status}
                  </span>
                </td>
                <td>
                  <button onClick={() => setSelected(r)}>Details</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>
            {selected.job_id} — {fmtUnix(selected.started)}
          </h3>
          {selected.error && <pre className="log">{selected.error}</pre>}
          <LogPanel lines={selected.result?.log as string[] | undefined} />
          <button onClick={() => setSelected(null)}>Close</button>
        </div>
      )}
    </div>
  );
}
