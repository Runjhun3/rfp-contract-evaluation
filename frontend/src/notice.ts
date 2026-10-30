// One way to say "saved": every successful write shows the server's own message (e.g.
// "Decision recorded") as a short notice at the top of the screen (components/Notice).
export const NOTICE = "bidlens:notice";

export function notify(message: string): void {
  if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(NOTICE, { detail: message }));
}
