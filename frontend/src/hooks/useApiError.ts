import { useCallback, useState } from "react";
import { ApiError } from "../api/client";

export function useApiError() {
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
      return undefined;
    }
  }, []);

  return { error, setError, run };
}
