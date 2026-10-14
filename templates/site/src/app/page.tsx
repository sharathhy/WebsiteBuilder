import { SiteShell } from "@/components/SiteShell";
import { Hero } from "@/components/hero/Hero";
import { Showcase } from "@/components/showcase/Showcase";
import { renderableSections, Sections } from "@/components/sections/Sections";
import { getSiteCtx } from "@/lib/site";

export default function Home() {
  const ctx = getSiteCtx();
  return (
    <SiteShell ctx={ctx} home>
      <Hero ctx={ctx} />
      <Showcase ctx={ctx} />
      <Sections ctx={ctx} sections={renderableSections(ctx)} />
    </SiteShell>
  );
}
