"use client";

import { useEffect, useState } from "react";
import { formatTime, hoursByDay, isOpenAt } from "@/lib/format";
import { DAYS, type Day, type HoursRow } from "@/lib/types";

function nowIn(tz: string): { day: Day; minutes: number } {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    weekday: "long",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date());
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  const day = (DAYS as readonly string[]).includes(get("weekday")) ? (get("weekday") as Day) : "Monday";
  return { day, minutes: Number(get("hour")) * 60 + Number(get("minute")) };
}

/** Opening hours with today highlighted and an "Open now" badge (computed client-side). */
export function HoursTable({ rows, locale, timeZone }: { rows: HoursRow[]; locale: "en-IN" | "en-US"; timeZone: string }) {
  const [now, setNow] = useState<{ day: Day; minutes: number } | null>(null);
  useEffect(() => {
    const update = () => {
      try {
        setNow(nowIn(timeZone));
      } catch {
        setNow(null);
      }
    };
    update();
    const t = window.setInterval(update, 60_000);
    return () => clearInterval(t);
  }, [timeZone]);

  const days = hoursByDay(rows);
  const open = now ? isOpenAt(rows, now.day, now.minutes) : null;

  return (
    <div>
      <p className="mb-4 flex min-h-8 items-center gap-2" aria-live="polite">
        {open === null ? null : open ? (
          <span className="chip !bg-[color-mix(in_srgb,#16a34a_16%,transparent)] text-fg">
            <span className="open-dot text-[#16a34a]" aria-hidden="true" />
            Open now
          </span>
        ) : (
          <span className="chip">
            <span className="size-2 rounded-full bg-current opacity-60" aria-hidden="true" />
            Closed now
          </span>
        )}
      </p>
      <table className="hours-table w-full overflow-hidden rounded-[var(--radius)] border border-line text-left">
        <caption className="sr-only">Opening hours</caption>
        <thead className="sr-only">
          <tr>
            <th scope="col">Day</th>
            <th scope="col">Hours</th>
          </tr>
        </thead>
        <tbody>
          {days.map(({ day, slots }) => {
            const today = now?.day === day;
            return (
              <tr key={day} data-today={today ? "true" : "false"} aria-current={today ? "date" : undefined}>
                <th scope="row" className="font-semibold">
                  {day}
                  {today ? <span className="ml-2 text-xs font-bold uppercase tracking-wider">Today</span> : null}
                </th>
                <td className="text-right tabular-nums">
                  {slots.length === 0 ? (
                    <span className="text-muted">Closed</span>
                  ) : (
                    slots.map((s, i) => (
                      <span key={i} className="block">
                        {formatTime(s.opens, locale)} – {formatTime(s.closes, locale)}
                      </span>
                    ))
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
