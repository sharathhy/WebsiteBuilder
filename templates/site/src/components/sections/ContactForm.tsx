"use client";

import { CheckCircle2, Loader2, Send } from "lucide-react";
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { track } from "@/lib/analytics";

declare global {
  interface Window {
    turnstile?: {
      render: (el: HTMLElement, opts: Record<string, unknown>) => string;
      reset: (id?: string) => void;
    };
  }
}

type Status = { kind: "idle" } | { kind: "sending" } | { kind: "ok" } | { kind: "error"; message: string };
type Errors = Partial<Record<"name" | "email" | "phone" | "message", string>>;

const TURNSTILE_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

function loadTurnstile(): Promise<void> {
  if (window.turnstile) return Promise.resolve();
  const existing = document.querySelector<HTMLScriptElement>(`script[src="${TURNSTILE_SRC}"]`);
  return new Promise((resolve, reject) => {
    const s = existing ?? document.createElement("script");
    s.addEventListener("load", () => resolve(), { once: true });
    s.addEventListener("error", () => reject(new Error("turnstile")), { once: true });
    if (!existing) {
      s.src = TURNSTILE_SRC;
      s.async = true;
      s.defer = true;
      document.head.appendChild(s);
    }
  });
}

export function ContactForm({
  endpoint,
  siteId,
  turnstileSiteKey,
  dark,
}: {
  endpoint: string;
  siteId: string;
  turnstileSiteKey: string | null;
  dark: boolean;
}) {
  const uid = useId();
  const formRef = useRef<HTMLFormElement>(null);
  const tsRef = useRef<HTMLDivElement>(null);
  const tsWidget = useRef<string | null>(null);
  const [token, setToken] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [errors, setErrors] = useState<Errors>({});
  const statusRef = useRef<HTMLDivElement>(null);

  // Lazy-load Turnstile when the form approaches the viewport (or on first focus).
  useEffect(() => {
    if (!turnstileSiteKey || !formRef.current) return;
    let done = false;
    const go = () => {
      if (done) return;
      done = true;
      loadTurnstile()
        .then(() => {
          if (!tsRef.current || !window.turnstile || tsWidget.current) return;
          tsWidget.current = window.turnstile.render(tsRef.current, {
            sitekey: turnstileSiteKey,
            theme: dark ? "dark" : "light",
            callback: (t: string) => setToken(t),
            "expired-callback": () => setToken(""),
            "error-callback": () => setToken(""),
          });
        })
        .catch(() => {
          /* the server still validates; show nothing scary */
        });
    };
    const form = formRef.current;
    const io = new IntersectionObserver(([e]) => e.isIntersecting && go(), { rootMargin: "300px 0px" });
    io.observe(form);
    form.addEventListener("focusin", go, { once: true });
    return () => {
      io.disconnect();
      form.removeEventListener("focusin", go);
    };
  }, [turnstileSiteKey, dark]);

  const validate = (fd: FormData): Errors => {
    const e: Errors = {};
    const name = String(fd.get("name") ?? "").trim();
    const email = String(fd.get("email") ?? "").trim();
    const phone = String(fd.get("phone") ?? "").trim();
    const message = String(fd.get("message") ?? "").trim();
    if (!name) e.name = "Please enter your name.";
    if (!email && !phone) e.email = "Please add an email or a phone number so we can reply.";
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = "Please enter a valid email address.";
    if (phone && phone.replace(/\D/g, "").length < 7) e.phone = "Please enter a valid phone number.";
    if (!message) e.message = "Please write a short message.";
    return e;
  };

  async function onSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const form = ev.currentTarget;
    const fd = new FormData(form);
    const errs = validate(fd);
    setErrors(errs);
    if (Object.keys(errs).length) {
      const first = Object.keys(errs)[0];
      form.querySelector<HTMLElement>(`[name="${first}"]`)?.focus();
      return;
    }
    if (turnstileSiteKey && !token) {
      setStatus({ kind: "error", message: "Please complete the verification check and try again." });
      return;
    }
    setStatus({ kind: "sending" });
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          site_id: siteId,
          name: String(fd.get("name") ?? "").trim(),
          email: String(fd.get("email") ?? "").trim(),
          phone: String(fd.get("phone") ?? "").trim(),
          message: String(fd.get("message") ?? "").trim(),
          company_website: String(fd.get("company_website") ?? ""),
          turnstile_token: token,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setStatus({ kind: "ok" });
      form.reset();
      track("lead_form_submit", { site_id: siteId });
    } catch {
      setStatus({
        kind: "error",
        message: "Sorry — your message could not be sent. Please try again, or call us instead.",
      });
      if (tsWidget.current) window.turnstile?.reset(tsWidget.current);
      setToken("");
    }
  }

  useEffect(() => {
    if (status.kind === "ok" || status.kind === "error") statusRef.current?.focus();
  }, [status.kind]);

  if (status.kind === "ok") {
    return (
      <div ref={statusRef} tabIndex={-1} role="status" className="grid min-h-72 place-items-center text-center outline-none">
        <div className="grid justify-items-center gap-3">
          <CheckCircle2 size={44} className="text-primary-text" aria-hidden="true" />
          <h3 className="text-2xl">Thank you — message sent.</h3>
          <p className="text-muted">We&rsquo;ll get back to you as soon as we can.</p>
          <button type="button" className="btn btn-ghost mt-2" onClick={() => setStatus({ kind: "idle" })}>
            Send another message
          </button>
        </div>
      </div>
    );
  }

  const f = (k: keyof Errors) => ({
    id: `${uid}-${k}`,
    name: k,
    "aria-invalid": errors[k] ? true : undefined,
    "aria-describedby": errors[k] ? `${uid}-${k}-err` : undefined,
  });
  const err = (k: keyof Errors) =>
    errors[k] ? (
      <p id={`${uid}-${k}-err`} className="mt-1.5 text-sm font-medium text-[#b42318] dark:text-[#ffb4ab]">
        {errors[k]}
      </p>
    ) : null;

  return (
    <form ref={formRef} onSubmit={onSubmit} noValidate className="grid gap-5" aria-describedby={`${uid}-note`}>
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="field">
          <label htmlFor={`${uid}-name`}>Name</label>
          <input {...f("name")} type="text" autoComplete="name" required />
          {err("name")}
        </div>
        <div className="field">
          <label htmlFor={`${uid}-phone`}>
            Phone <span className="font-normal text-muted">(optional)</span>
          </label>
          <input {...f("phone")} type="tel" autoComplete="tel" inputMode="tel" />
          {err("phone")}
        </div>
      </div>
      <div className="field">
        <label htmlFor={`${uid}-email`}>Email</label>
        <input {...f("email")} type="email" autoComplete="email" inputMode="email" />
        {err("email")}
      </div>
      <div className="field">
        <label htmlFor={`${uid}-message`}>Message</label>
        <textarea {...f("message")} rows={4} required />
        {err("message")}
      </div>
      {/* Honeypot: humans never see or fill this. */}
      <div className="hp-field" aria-hidden="true">
        <label htmlFor={`${uid}-hp`}>Company website</label>
        <input id={`${uid}-hp`} type="text" name="company_website" tabIndex={-1} autoComplete="off" defaultValue="" />
      </div>
      {turnstileSiteKey ? <div ref={tsRef} className="min-h-[65px]" /> : null}
      <div ref={status.kind === "error" ? statusRef : undefined} tabIndex={-1} aria-live="assertive" className="outline-none">
        {status.kind === "error" ? (
          <p role="alert" className="rounded-xl border border-[#b42318]/40 bg-[#b42318]/10 p-3 text-sm font-medium">
            {status.message}
          </p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <button type="submit" className="btn btn-primary" disabled={status.kind === "sending"} aria-busy={status.kind === "sending"}>
          {status.kind === "sending" ? (
            <Loader2 size={18} className="animate-spin" aria-hidden="true" />
          ) : (
            <Send size={18} aria-hidden="true" />
          )}
          {status.kind === "sending" ? "Sending…" : "Send message"}
        </button>
        <p id={`${uid}-note`} className="text-sm text-muted">
          We only use your details to reply to you.
        </p>
      </div>
    </form>
  );
}
