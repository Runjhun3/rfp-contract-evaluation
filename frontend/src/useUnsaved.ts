import { useEffect } from "react";
import { useBlocker } from "react-router-dom";

const LEAVE = "You have changes that are not saved. Leave this page and lose them?";

// While `dirty`, ask before leaving: on a link inside the app (another page, or another
// item of the same page) and on closing or reloading the tab. A move made right after a
// save passes { afterSave: true } as its state and is never asked about. Only one form
// per page uses it (the router allows one blocker at a time).
export function useUnsavedWarning(dirty: boolean): void {
  const blocker = useBlocker(({ currentLocation, nextLocation }) =>
    dirty && !(nextLocation.state as { afterSave?: boolean } | null)?.afterSave
    && currentLocation.pathname + currentLocation.search !== nextLocation.pathname + nextLocation.search);

  useEffect(() => {
    if (blocker.state !== "blocked") return;
    if (window.confirm(LEAVE)) blocker.proceed();
    else blocker.reset();
  }, [blocker]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault(); // the browser asks
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
}
