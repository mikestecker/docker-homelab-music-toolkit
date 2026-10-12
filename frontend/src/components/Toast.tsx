import type { ToastState } from "../hooks/useToast";

export default function Toast({ toast, onDismiss }: { toast: ToastState | null; onDismiss: () => void }) {
  if (!toast) return null;
  return (
    <div className={`toast toast-${toast.tone}`} role="status" aria-live="polite">
      <div className="row" style={{ marginBottom: toast.detail?.length ? 6 : 0, flexWrap: "nowrap" }}>
        <span style={{ flex: 1 }}>{toast.message}</span>
        {toast.action && <button onClick={toast.action.onClick}>{toast.action.label}</button>}
        <button onClick={onDismiss}>✕</button>
      </div>
      {toast.detail && toast.detail.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
          {toast.detail.map((d, i) => (
            <li key={i}>{d}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
