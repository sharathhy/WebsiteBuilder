import { cn } from "@/lib/utils";

const gradeTone: Record<string, string> = {
  A: "bg-emerald-600 text-white",
  B: "bg-lime-500 text-white",
  C: "bg-amber-500 text-white",
  D: "bg-red-600 text-white",
};

export function ScorePill({ score, grade }: { score: number | null; grade: string | null }) {
  if (score === null) {
    return <span className="text-xs text-slate-500">not scored</span>;
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={cn(
          "inline-flex size-7 items-center justify-center rounded-md text-xs font-bold",
          gradeTone[grade ?? "D"],
        )}
        aria-label={`Grade ${grade}`}
      >
        {grade}
      </span>
      <span className="text-sm font-semibold tabular-nums">{score}</span>
    </span>
  );
}

export function Bar({ value, max, className }: { value: number; max: number; className?: string }) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  const tone = pct >= 85 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-slate-100", className)}>
      <div className={cn("h-full rounded-full", tone)} style={{ width: `${pct}%` }} />
    </div>
  );
}
