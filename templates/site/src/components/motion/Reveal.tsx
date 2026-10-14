"use client";

import { m, useReducedMotion, type Variants } from "motion/react";
import type { ReactNode } from "react";
import { useMotionPersonality } from "./MotionProvider";

type Tag = "div" | "li" | "article" | "figure" | "header";

/** Entrance transition when the element scrolls into view (Framer Motion). */
export function Reveal({
  children,
  className,
  delay = 0,
  as = "div",
  y,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  as?: Tag;
  y?: number;
}) {
  const mp = useMotionPersonality();
  const reduce = useReducedMotion();
  if (reduce) {
    const Plain = as;
    return <Plain className={className}>{children}</Plain>;
  }
  const Cmp = m[as];
  return (
    <Cmp
      className={className}
      initial={{ opacity: 0, y: y ?? mp.distance }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "0px 0px -10% 0px" }}
      transition={{ duration: mp.duration, ease: mp.ease, delay }}
    >
      {children}
    </Cmp>
  );
}

/** Staggered group: children should be <RevealItem>. */
export function RevealGroup({
  children,
  className,
  as = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "ul" | "ol";
}) {
  const mp = useMotionPersonality();
  const reduce = useReducedMotion();
  if (reduce) {
    const Plain = as;
    return <Plain className={className}>{children}</Plain>;
  }
  const Cmp = m[as];
  const variants: Variants = { hidden: {}, show: { transition: { staggerChildren: mp.stagger } } };
  return (
    <Cmp
      className={className}
      variants={variants}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "0px 0px -8% 0px" }}
    >
      {children}
    </Cmp>
  );
}

export function RevealItem({
  children,
  className,
  as = "div",
  hover = false,
}: {
  children: ReactNode;
  className?: string;
  as?: Tag;
  hover?: boolean;
}) {
  const mp = useMotionPersonality();
  const reduce = useReducedMotion();
  if (reduce) {
    const Plain = as;
    return <Plain className={className}>{children}</Plain>;
  }
  const Cmp = m[as];
  const variants: Variants = {
    hidden: { opacity: 0, y: mp.distance, scale: 0.98 },
    show: { opacity: 1, y: 0, scale: 1, transition: { duration: mp.duration, ease: mp.ease } },
  };
  return (
    <Cmp
      className={className}
      variants={variants}
      whileHover={hover ? { y: -mp.lift, transition: { duration: 0.3, ease: mp.ease } } : undefined}
    >
      {children}
    </Cmp>
  );
}
