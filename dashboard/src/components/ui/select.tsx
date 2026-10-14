import type { SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "min-h-11 w-full rounded-lg bg-white px-3 text-base ring-1 ring-slate-300 sm:text-sm",
        "focus:ring-2 focus:ring-brand-600 focus:outline-none",
        className,
      )}
      {...props}
    />
  );
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full rounded-lg bg-white p-3 font-mono text-sm leading-relaxed ring-1 ring-slate-300",
        "focus:ring-2 focus:ring-brand-600 focus:outline-none",
        className,
      )}
      {...props}
    />
  );
}
