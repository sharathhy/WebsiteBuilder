"use client";

import { X } from "lucide-react";
import { useState, useSyncExternalStore } from "react";

const KEY = "lf-preview-banner-dismissed";

/** Clearly-labelled notice listing what the owner still has to confirm (spec.placeholders). */
export function PreviewBanner({ items }: { items: string[] }) {
  const stored = useSyncExternalStore(
    () => () => {},
    () => {
      try {
        return sessionStorage.getItem(KEY) === "1";
      } catch {
        return false;
      }
    },
    () => false,
  );
  const [dismissed, setHidden] = useState(false);
  if (stored || dismissed) return null;
  return (
    <aside
      aria-label="Preview notice"
      className="relative z-50 border-b border-dashed border-line bg-surface-2 text-fg"
    >
      <div className="container-x flex items-start gap-3 py-2.5 text-sm">
        <span className="mt-0.5 shrink-0 rounded-full border border-dashed border-current px-2 py-0.5 text-xs font-bold uppercase tracking-wider text-primary-text">
          Preview
        </span>
        <p className="min-w-0 flex-1 leading-relaxed">
          <strong className="font-semibold">Items to confirm with the owner:</strong>{" "}
          <span className="text-muted">{items.join(" · ")}</span>
        </p>
        <button
          type="button"
          className="-my-2 -mr-2 grid size-11 shrink-0 place-items-center rounded-full hover:bg-fg/10"
          aria-label="Dismiss preview notice"
          onClick={() => {
            setHidden(true);
            try {
              sessionStorage.setItem(KEY, "1");
            } catch {
              /* ignore */
            }
          }}
        >
          <X size={18} aria-hidden="true" />
        </button>
      </div>
    </aside>
  );
}
