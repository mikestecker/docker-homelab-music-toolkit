import { useCallback, useRef, useState } from "react";

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface ToastState {
  id: number;
  tone: "good" | "warn" | "bad";
  message: string;
  detail?: string[];
  action?: ToastAction;
}

export function useToast() {
  const [toast, setToast] = useState<ToastState | null>(null);
  const counter = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const dismiss = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    setToast(null);
  }, []);

  const show = useCallback((t: Omit<ToastState, "id">) => {
    if (timer.current) clearTimeout(timer.current);
    const id = ++counter.current;
    setToast({ ...t, id });
    // Longer dwell time when there's an action to give (e.g. Undo) time to be clicked.
    timer.current = setTimeout(() => {
      setToast((cur) => (cur?.id === id ? null : cur));
    }, t.action ? 9000 : 5000);
  }, []);

  return { toast, show, dismiss };
}
