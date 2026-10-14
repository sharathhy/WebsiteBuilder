"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { useSceneGate, type SceneColors } from "../hero/Hero3D";
import type { HeroModel } from "@/lib/types";

// Same lazily-loaded three.js chunk as the hero: never in first-load JS.
const ShowcaseScene = dynamic(() => import("../hero/HeroScene").then((m) => m.ShowcaseScene), {
  ssr: false,
  loading: () => null,
});

/**
 * Drives the scroll showcase: reads how far the tall section has been scrolled (0..1),
 * exposes it as `--p` on the section, marks the active step, and feeds the same value to
 * the 3D scene. The steps work without WebGL (the static art turns with `--p` in CSS).
 */
export function ShowcaseStage({ model, colors, steps }: { model: HeroModel; colors: SceneColors; steps: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const progress = useRef(0);
  const { visible, mounted } = useSceneGate(ref, "200px 0px");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const section = ref.current?.closest<HTMLElement>("[data-showcase]");
    if (!section) return;
    const items = Array.from(section.querySelectorAll<HTMLElement>("[data-step]"));
    let frame = 0;
    let active = -1;
    const update = () => {
      frame = 0;
      const r = section.getBoundingClientRect();
      const span = Math.max(1, r.height - window.innerHeight);
      const p = Math.min(1, Math.max(0, -r.top / span));
      progress.current = p;
      section.style.setProperty("--p", p.toFixed(4));
      const idx = Math.min(steps - 1, Math.floor(p * steps * 0.999));
      if (idx !== active) {
        active = idx;
        items.forEach((el, i) => el.toggleAttribute("data-on", i === idx));
      }
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [steps]);

  return (
    <div ref={ref} className="showcase-canvas" data-ready={ready ? "true" : "false"} aria-hidden="true">
      {mounted ? (
        <ShowcaseScene model={model} colors={colors} active={visible} progress={progress} onReady={() => setReady(true)} />
      ) : null}
    </div>
  );
}
