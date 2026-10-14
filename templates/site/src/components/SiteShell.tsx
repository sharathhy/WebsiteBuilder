import type { ReactNode } from "react";
import type { SiteCtx } from "./common";
import { Footer, MobileActionBar } from "./Footer";
import { Header } from "./Header";
import { PreviewBanner } from "./PreviewBanner";
import { renderableSections } from "./sections/Sections";

export function SiteShell({ ctx, home, children }: { ctx: SiteCtx; home: boolean; children: ReactNode }) {
  const sections = renderableSections(ctx);
  const b = ctx.spec.business;
  const hasBar = !!(b.phone_e164 || b.whatsapp_e164 || ctx.spec.contact.booking_url);
  return (
    <div className={hasBar ? "has-action-bar" : undefined}>
      {ctx.spec.placeholders.length ? <PreviewBanner items={ctx.spec.placeholders} /> : null}
      <Header ctx={ctx} sections={sections} home={home} />
      <main id="main" tabIndex={-1} className="outline-none">
        {children}
      </main>
      <Footer ctx={ctx} />
      <MobileActionBar ctx={ctx} />
    </div>
  );
}
