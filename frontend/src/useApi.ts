import { useCallback, useEffect, useRef, useState } from "react";
import { get } from "./api";

// Loads `path`, reloads on demand, and polls again while `poll(data)` returns a delay in ms.
export function useApi<T>(path: string, poll?: (data: T) => number | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const pollRef = useRef(poll);

  useEffect(() => {
    pollRef.current = poll;
  });

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const again = (ms: number | null | undefined) => {
      if (alive && ms) timer = setTimeout(() => setTick((t) => t + 1), ms);
    };
    get<T>(path)
      .then((d) => {
        if (!alive) return;
        setData(d);
        setError(null);
        again(pollRef.current?.(d));
      })
      .catch((err: Error) => {
        if (!alive) return;
        setError(err.message);
        if (pollRef.current) again(5000); // polling pages keep retrying
      });
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [path, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, reload };
}
