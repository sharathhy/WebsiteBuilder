"use client";

import { useEffect } from "react";
import { onIdle } from "@/lib/idle";

/**
 * Lenis smooth scroll + GSAP ScrollTrigger scroll-storytelling, loaded after hydration
 * (dynamic import → not in first-load JS) and skipped entirely for prefers-reduced-motion.
 *
 * Markup hooks (set by server components):
 *  [data-speed="0.3"]      parallax layer, moves at a different rate than the scroll
 *  [data-story]            pinned storytelling section (desktop): [data-pin] stays put,
 *                          [data-depth] items rise out of z-depth, [data-progress] fills
 *  [data-tilt]             element that flattens from a 3D tilt as it scrolls into place
 */
export function ScrollFX({ parallax = 1 }: { parallax?: number }) {
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) return;
    let cancelled = false;
    let cleanup: (() => void) | undefined;

    const start = async () => {
      const [{ default: Lenis }, { gsap }, { ScrollTrigger }] = await Promise.all([
        import("lenis"),
        import("gsap"),
        import("gsap/ScrollTrigger"),
      ]);
      if (cancelled) return;
      gsap.registerPlugin(ScrollTrigger);

      const lenis = new Lenis({ lerp: 0.11, smoothWheel: true, anchors: { offset: -88 } });
      lenis.on("scroll", ScrollTrigger.update);
      const tick = (time: number) => lenis.raf(time * 1000);
      gsap.ticker.add(tick);
      gsap.ticker.lagSmoothing(0);

      const ctx = gsap.context(() => {
        // Parallax layers
        gsap.utils.toArray<HTMLElement>("[data-speed]").forEach((el) => {
          const speed = parseFloat(el.dataset.speed || "0") * parallax;
          gsap.fromTo(
            el,
            { yPercent: speed * 12 },
            {
              yPercent: -speed * 12,
              ease: "none",
              scrollTrigger: { trigger: el.parentElement ?? el, start: "top bottom", end: "bottom top", scrub: true },
            },
          );
        });

        // Tilted cards flatten into place (z-depth)
        gsap.utils.toArray<HTMLElement>("[data-tilt]").forEach((el) => {
          gsap.fromTo(
            el,
            { rotateX: 18, scale: 0.92, transformPerspective: 1200, transformOrigin: "50% 100%" },
            {
              rotateX: 0,
              scale: 1,
              ease: "none",
              scrollTrigger: { trigger: el, start: "top 95%", end: "top 35%", scrub: 0.6 },
            },
          );
        });

        // Storytelling: pin the intro column while items rise from depth (desktop only)
        const mm = gsap.matchMedia();
        mm.add("(min-width: 1024px)", () => {
          gsap.utils.toArray<HTMLElement>("[data-story]").forEach((section) => {
            const pin = section.querySelector<HTMLElement>("[data-pin]");
            const list = section.querySelector<HTMLElement>("[data-story-list]");
            const bar = section.querySelector<HTMLElement>("[data-progress]");
            if (!pin || !list) return;
            if (list.offsetHeight > pin.offsetHeight + 120) {
              ScrollTrigger.create({
                trigger: list,
                start: "top 18%",
                end: () => `bottom ${Math.round(18 + (pin.offsetHeight / window.innerHeight) * 100)}%`,
                pin,
                pinSpacing: false,
                invalidateOnRefresh: true,
                onUpdate: (st) => bar?.style.setProperty("--p", st.progress.toFixed(3)),
              });
            }
            section.querySelectorAll<HTMLElement>("[data-depth]").forEach((card) => {
              gsap.fromTo(
                card,
                { opacity: 0.45, scale: 0.92, rotateX: 14, z: -120, transformPerspective: 1000, transformOrigin: "50% 100%" },
                {
                  opacity: 1,
                  scale: 1,
                  rotateX: 0,
                  z: 0,
                  ease: "power2.out",
                  scrollTrigger: { trigger: card, start: "top 98%", end: "top 62%", scrub: 0.5 },
                },
              );
            });
          });
        });
      });

      // Images/fonts can change layout after load
      const refresh = () => ScrollTrigger.refresh();
      window.addEventListener("load", refresh);
      document.fonts?.ready.then(refresh).catch(() => {});

      cleanup = () => {
        window.removeEventListener("load", refresh);
        ctx.revert();
        gsap.ticker.remove(tick);
        lenis.destroy();
      };
    };

    // Wait for the browser to be idle so this never competes with LCP/hydration.
    const cancelIdle = onIdle(() => void start(), 1500);

    return () => {
      cancelled = true;
      cancelIdle();
      cleanup?.();
    };
  }, [parallax]);

  return null;
}
