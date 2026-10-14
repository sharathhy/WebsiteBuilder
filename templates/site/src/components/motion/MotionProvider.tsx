"use client";

import { LazyMotion, MotionConfig } from "motion/react";
import { createContext, useContext, type ReactNode } from "react";
import type { MotionPersonality } from "@/lib/presets";

const loadFeatures = () => import("./features").then((m) => m.default);

const Ctx = createContext<MotionPersonality>({
  duration: 0.8,
  distance: 24,
  stagger: 0.08,
  ease: [0.22, 1, 0.36, 1],
  lift: 4,
  parallax: 1,
});

export const useMotionPersonality = () => useContext(Ctx);

export function MotionProvider({ motion, children }: { motion: MotionPersonality; children: ReactNode }) {
  return (
    <Ctx.Provider value={motion}>
      {/* reducedMotion="user": transforms are skipped when prefers-reduced-motion is set */}
      <MotionConfig reducedMotion="user">
        <LazyMotion features={loadFeatures} strict>
          {children}
        </LazyMotion>
      </MotionConfig>
    </Ctx.Provider>
  );
}
