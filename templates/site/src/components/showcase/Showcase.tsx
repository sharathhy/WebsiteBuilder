import { Img, type SiteCtx } from "../common";
import { Icon } from "../Icon";
import { sceneColors } from "../hero/Hero";
import { ShowcaseStage } from "./ShowcaseStage";

/**
 * Scroll showcase: a tall section with a sticky stage. As visitors scroll, the template's 3D
 * model turns and the camera moves while the business's first services step through one at
 * a time. Content is only the spec's own services. Without WebGL the hero art turns in CSS;
 * with prefers-reduced-motion the section collapses to a plain list (see globals.css).
 */
export function Showcase({ ctx }: { ctx: SiteCtx }) {
  const { spec } = ctx;
  const steps = spec.services.slice(0, 3);
  if (!spec.hero.enable_3d || !spec.hero.scroll_scene || steps.length < 2) return null;
  const eyebrow = ctx.preset.eyebrows.services ?? "Services";
  return (
    <section
      className="showcase"
      data-showcase
      aria-labelledby="showcase-title"
      style={{ ["--steps" as string]: steps.length }}
    >
      <div className="showcase-sticky">
        <div className="container-x showcase-grid">
          <div className="showcase-copy">
            <p className="eyebrow">{eyebrow}</p>
            <h2 id="showcase-title" className="sr-only">
              {spec.business.name}: {eyebrow}
            </h2>
            <ol className="showcase-steps">
              {steps.map((s, i) => (
                <li key={i} className="showcase-step" data-step={i} data-on={i === 0 ? "" : undefined}>
                  <span className="showcase-num" aria-hidden="true">
                    {String(i + 1).padStart(2, "0")}
                    <span className="text-muted"> / {String(steps.length).padStart(2, "0")}</span>
                  </span>
                  <h3 className="showcase-title">
                    <span className="icon-chip mr-3 align-middle" aria-hidden="true">
                      <Icon name={s.icon} />
                    </span>
                    {s.title}
                  </h3>
                  <p className="lede mt-4">{s.description}</p>
                </li>
              ))}
            </ol>
            <div className="showcase-rail" aria-hidden="true">
              <span />
            </div>
          </div>
          <div className="showcase-visual" aria-hidden="true">
            <span className="glow showcase-glow" />
            <div className="showcase-art">
              <Img image={{ src: spec.hero.fallback_image.src, alt: "" }} width={800} height={800} />
            </div>
            <ShowcaseStage model={spec.hero.model} colors={sceneColors(ctx)} steps={steps.length} />
          </div>
        </div>
      </div>
    </section>
  );
}
