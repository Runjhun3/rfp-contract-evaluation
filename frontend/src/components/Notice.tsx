import { useEffect, useState } from "react";
import { NOTICE } from "../notice";

const SHOWN_MS = 3500;

// The latest "saved" message, at the top right for a few seconds. A live region, so
// screen readers announce it too.
export default function Notice() {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const show = (e: Event) => {
      setMessage((e as CustomEvent<string>).detail);
      clearTimeout(timer);
      timer = setTimeout(() => setMessage(null), SHOWN_MS);
    };
    window.addEventListener(NOTICE, show);
    return () => {
      window.removeEventListener(NOTICE, show);
      clearTimeout(timer);
    };
  }, []);

  return (
    <div className="saved-notice" role="status" aria-live="polite">
      {message && <span><span aria-hidden="true">✓ </span>{message}</span>}
    </div>
  );
}
