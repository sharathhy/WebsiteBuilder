"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState, type RefObject } from "react";
import { onIdle } from "@/lib/idle";
import type { HeroModel } from "@/lib/types";

// three.js / R3F live only in this lazily-loaded chunk — never in first-load JS.
const HeroScene = dynamic(() => import("./HeroScene"), { ssr: false, loading: () => null });

export interface SceneColors {
  primary: string;
  secondary: string;
  accent: string;
  dark: boolean;
}

/**
 * True only for hardware-accelerated WebGL. Software rasterisers (SwiftShader, llvmpipe —
 * typical of headless CI, VMs and blocklisted GPUs) would burn the main thread, so they get
 * the fallback image instead. Data-saver and very low-memory devices are skipped too.
 */
export function canRender3D(allowSoftware = false): boolean {
  try {
    const nav = navigator as Navigator & { connection?: { saveData?: boolean }; deviceMemory?: number };
    if (nav.connection?.saveData) return false;
    if (typeof nav.deviceMemory === "number" && nav.deviceMemory < 2) return false;
    const c = document.createElement("canvas");
    const gl = (c.getContext("webgl2") || c.getContext("webgl")) as WebGLRenderingContext | null;
    if (!gl) return false;
    const info = gl.getExtension("WEBGL_debug_renderer_info");
    const renderer = String(info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    if (!allowSoftware && /swiftshader|llvmpipe|softpipe|software|basic render/i.test(renderer)) return false;
    return true;
  } catch {
    return false;
  }
}

/** Resolves after window load + an idle slot, i.e. after LCP has had its chance. */
export function afterLoadAndIdle(cb: () => void): () => void {
  let cancelIdle: (() => void) | undefined;
  const idle = () => {
    cancelIdle = onIdle(cb, 2500);
  };
  if (document.readyState === "complete") idle();
  else window.addEventListener("load", idle, { once: true });
  return () => {
    window.removeEventListener("load", idle);
    cancelIdle?.();
  };
}

/**
 * Shared gate for every WebGL scene. A scene mounts only when:
 *  - prefers-reduced-motion is not set,
 *  - hardware WebGL is available (see canRender3D),
 *  - the page has loaded and the main thread is idle,
 *  - its container is near the viewport (IntersectionObserver).
 * After mounting, `visible` pauses the render loop while the container is off-screen.
 */
export function useSceneGate(ref: RefObject<HTMLElement | null>, rootMargin = "0px") {
  const [eligible, setEligible] = useState(false);
  const [visible, setVisible] = useState(false);
  const [mounted, setMounted] = useState(false);
  const eligibleRef = useRef(false);
  const visibleRef = useRef(false);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (reduce.matches || !canRender3D(/[?&]force3d\b/.test(location.search))) return;
    const cancel = afterLoadAndIdle(() => {
      eligibleRef.current = true;
      setEligible(true);
      if (visibleRef.current) setMounted(true);
    });
    const onChange = () => {
      if (reduce.matches) {
        eligibleRef.current = false;
        setEligible(false);
      }
    };
    reduce.addEventListener?.("change", onChange);
    return () => {
      cancel();
      reduce.removeEventListener?.("change", onChange);
    };
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el || !("IntersectionObserver" in window)) return;
    const io = new IntersectionObserver(
      ([e]) => {
        visibleRef.current = e.isIntersecting;
        setVisible(e.isIntersecting);
        // Mount once (first time eligible + visible); afterwards just pause when off-screen.
        if (e.isIntersecting && eligibleRef.current) setMounted(true);
      },
      { threshold: 0.01, rootMargin },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ref, rootMargin]);

  return { eligible, visible, mounted: mounted && eligible };
}

/** The 3D hero: the server-rendered fallback image stays as the hero visual until it's ready. */
export function Hero3D({ model, colors, className = "" }: { model: HeroModel; colors: SceneColors; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const { eligible, visible, mounted } = useSceneGate(ref);
  const [ready, setReady] = useState(false);
  return (
    <div ref={ref} className={`hero-canvas ${className}`} data-ready={ready && eligible ? "true" : "false"} aria-hidden="true">
      {mounted ? <HeroScene model={model} colors={colors} active={visible} onReady={() => setReady(true)} /> : null}
    </div>
  );
}
