import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "min-h-11 w-full rounded-lg bg-white px-3 text-base ring-1 ring-slate-300 sm:text-sm",
        "focus:ring-2 focus:ring-brand-600 focus:outline-none",
        className,
      )}
      {...props}
    />
  );
}
