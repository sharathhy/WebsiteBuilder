/** requestIdleCallback with a setTimeout fallback (Safari). Returns a cancel function. */
export function onIdle(cb: () => void, timeout = 2000): () => void {
  const w = window as Window & typeof globalThis;
  if (typeof w.requestIdleCallback === "function") {
    const id = w.requestIdleCallback(cb, { timeout });
    return () => w.cancelIdleCallback(id);
  }
  const id = w.setTimeout(cb, Math.min(timeout, 600));
  return () => w.clearTimeout(id);
}
