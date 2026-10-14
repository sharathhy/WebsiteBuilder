"use client";

// Heavy chunk: three.js + React Three Fiber + drei. Loaded only by Hero3D (next/dynamic, ssr:false).
// Every model is procedural (primitives, LatheGeometry, ExtrudeGeometry) — no GLB downloads.

import { Canvas, useFrame } from "@react-three/fiber";
import { ContactShadows, Environment, Float, Lightformer, MeshDistortMaterial } from "@react-three/drei";
import { useEffect, useMemo, useRef, type ReactNode } from "react";
import * as THREE from "three";
import type { HeroModel } from "@/lib/types";
import type { SceneColors } from "./Hero3D";

const V2 = (x: number, y: number) => new THREE.Vector2(x, y);

/* ---------------------------------------------------------------- models */

function Tooth({ c }: { c: SceneColors }) {
  const crown = useMemo(() => {
    const pts = [
      V2(0.0, 1.02),
      V2(0.22, 1.0),
      V2(0.45, 1.06),
      V2(0.64, 1.0),
      V2(0.76, 0.82),
      V2(0.8, 0.55),
      V2(0.74, 0.28),
      V2(0.6, 0.05),
      V2(0.52, -0.1),
    ];
    return new THREE.LatheGeometry(pts, 64);
  }, []);
  const root = useMemo(() => new THREE.CylinderGeometry(0.27, 0.1, 0.95, 32, 1), []);
  const enamel = (
    <meshPhysicalMaterial color="#f7f4ef" roughness={0.22} clearcoat={1} clearcoatRoughness={0.15} sheen={0.4} sheenColor={c.accent} />
  );
  return (
    <group scale={0.95} position={[0, 0.1, 0]}>
      <mesh geometry={crown}>{enamel}</mesh>
      {[
        [0.27, 0.98, 0.27],
        [-0.27, 0.98, 0.27],
        [0.27, 0.98, -0.27],
        [-0.27, 0.98, -0.27],
      ].map((p, i) => (
        <mesh key={i} position={p as [number, number, number]} scale={[0.3, 0.12, 0.3]}>
          <sphereGeometry args={[1, 32, 16]} />
          {enamel}
        </mesh>
      ))}
      <mesh geometry={root} position={[-0.27, -0.5, 0]} rotation={[0, 0, -0.14]}>
        {enamel}
      </mesh>
      <mesh geometry={root} position={[0.27, -0.5, 0]} rotation={[0, 0, 0.14]}>
        {enamel}
      </mesh>
      <mesh rotation={[Math.PI / 2.3, 0, 0]} position={[0, 0.45, 0]}>
        <torusGeometry args={[1.25, 0.02, 16, 128]} />
        <meshStandardMaterial color={c.primary} emissive={c.primary} emissiveIntensity={0.6} />
      </mesh>
    </group>
  );
}

function Plate({ c }: { c: SceneColors }) {
  const plate = useMemo(
    () =>
      new THREE.LatheGeometry(
        [V2(0, 0), V2(0.95, 0), V2(1.05, 0.03), V2(1.5, 0.16), V2(1.62, 0.2), V2(1.6, 0.24), V2(1.46, 0.21), V2(1.0, 0.08), V2(0, 0.06)],
        96,
      ),
    [],
  );
  return (
    <group rotation={[0.55, 0, 0]} position={[0, -0.2, 0]} scale={1.05}>
      <mesh geometry={plate}>
        <meshPhysicalMaterial color="#fbf8f3" roughness={0.18} clearcoat={1} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, 0.05, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.38, 1.44, 96]} />
        <meshStandardMaterial color={c.accent} metalness={0.9} roughness={0.25} />
      </mesh>
      {/* garnish */}
      <mesh position={[-0.25, 0.28, 0.05]} scale={[0.55, 0.32, 0.5]}>
        <sphereGeometry args={[1, 48, 32]} />
        <meshStandardMaterial color={c.primary} roughness={0.55} />
      </mesh>
      <mesh position={[0.45, 0.2, 0.25]} scale={0.2}>
        <sphereGeometry args={[1, 32, 16]} />
        <meshStandardMaterial color={c.accent} roughness={0.35} />
      </mesh>
      <mesh position={[0.35, 0.16, -0.35]} scale={0.15}>
        <sphereGeometry args={[1, 32, 16]} />
        <meshStandardMaterial color={c.secondary} roughness={0.4} />
      </mesh>
      {[0, 1, 2, 3].map((i) => (
        <mesh key={i} position={[0.1 + i * 0.12, 0.42 + (i % 2) * 0.05, 0.1 - i * 0.08]} rotation={[0.4, i, 0.8]} scale={[0.16, 0.03, 0.08]}>
          <sphereGeometry args={[1, 16, 8]} />
          <meshStandardMaterial color="#4f8a3a" roughness={0.6} />
        </mesh>
      ))}
    </group>
  );
}

function Droplet({ c }: { c: SceneColors }) {
  const geo = useMemo(() => {
    const pts: THREE.Vector2[] = [];
    for (let i = 0; i <= 64; i++) {
      const t = (i / 64) * Math.PI;
      pts.push(V2(Math.sin(t) * (1 - Math.cos(t)) * 0.52, Math.cos(t) * 1.15));
    }
    return new THREE.LatheGeometry(pts, 96);
  }, []);
  return (
    <group position={[0, 0.1, 0]}>
      <mesh geometry={geo}>
        <meshPhysicalMaterial
          color={c.primary}
          transmission={0.92}
          thickness={1.4}
          roughness={0.04}
          ior={1.33}
          clearcoat={1}
          attenuationColor={c.primary}
          attenuationDistance={2.5}
        />
      </mesh>
      {[
        [1.1, 0.7, 0.2, 0.16],
        [-1.05, -0.4, 0.3, 0.22],
        [0.8, -0.9, -0.2, 0.11],
      ].map(([x, y, z, s], i) => (
        <mesh key={i} position={[x, y, z]} scale={s}>
          <sphereGeometry args={[1, 32, 32]} />
          <meshPhysicalMaterial color={c.accent} transmission={0.85} roughness={0.05} thickness={0.5} />
        </mesh>
      ))}
    </group>
  );
}

function Dumbbell({ c }: { c: SceneColors }) {
  const plates = (side: 1 | -1) => (
    <group position={[side * 1.0, 0, 0]}>
      {[0, 1].map((i) => (
        <mesh key={i} position={[side * (i * 0.26), 0, 0]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.62 - i * 0.12, 0.62 - i * 0.12, 0.22, 6]} />
          <meshStandardMaterial color={c.dark ? "#1d1d20" : "#26262b"} roughness={0.55} metalness={0.2} />
        </mesh>
      ))}
      <mesh position={[side * -0.13, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.66, 0.66, 0.05, 6]} />
        <meshStandardMaterial color={c.primary} roughness={0.35} metalness={0.3} emissive={c.primary} emissiveIntensity={0.15} />
      </mesh>
    </group>
  );
  return (
    <group rotation={[0.35, -0.5, 0.25]} scale={0.8}>
      <mesh rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.11, 0.11, 2.9, 32]} />
        <meshStandardMaterial color="#c9ccd2" metalness={1} roughness={0.28} />
      </mesh>
      {[-0.5, -0.3, -0.1, 0.1, 0.3, 0.5].map((x) => (
        <mesh key={x} position={[x, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
          <torusGeometry args={[0.115, 0.012, 8, 32]} />
          <meshStandardMaterial color="#9aa0a8" metalness={1} roughness={0.4} />
        </mesh>
      ))}
      {plates(1)}
      {plates(-1)}
    </group>
  );
}

function Pillar({ c }: { c: SceneColors }) {
  const shaft = useMemo(() => {
    const g = new THREE.CylinderGeometry(0.42, 0.46, 2.3, 120, 1, true);
    const pos = g.attributes.position as THREE.BufferAttribute;
    const v = new THREE.Vector3();
    for (let i = 0; i < pos.count; i++) {
      v.fromBufferAttribute(pos, i);
      const a = Math.atan2(v.z, v.x);
      const k = 1 - 0.055 * Math.pow(Math.abs(Math.cos(a * 10)), 3);
      pos.setXYZ(i, v.x * k, v.y, v.z * k);
    }
    g.computeVertexNormals();
    return g;
  }, []);
  const marble = <meshPhysicalMaterial color="#f1ede6" roughness={0.35} clearcoat={0.4} />;
  return (
    <group scale={0.95} position={[0, -0.1, 0]}>
      <mesh position={[0, -1.42, 0]}>
        <boxGeometry args={[1.45, 0.22, 1.45]} />
        {marble}
      </mesh>
      <mesh position={[0, -1.24, 0]}>
        <cylinderGeometry args={[0.6, 0.62, 0.16, 64]} />
        {marble}
      </mesh>
      <mesh geometry={shaft}>{marble}</mesh>
      <mesh position={[0, 1.2, 0]}>
        <cylinderGeometry args={[0.62, 0.45, 0.18, 64]} />
        {marble}
      </mesh>
      <mesh position={[0, 1.36, 0]}>
        <boxGeometry args={[1.45, 0.16, 1.45]} />
        {marble}
      </mesh>
      <mesh position={[0, 1.13, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.48, 0.03, 16, 96]} />
        <meshStandardMaterial color={c.accent} metalness={1} roughness={0.25} />
      </mesh>
      <mesh position={[0, -1.12, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.49, 0.03, 16, 96]} />
        <meshStandardMaterial color={c.accent} metalness={1} roughness={0.25} />
      </mesh>
    </group>
  );
}

function House({ c }: { c: SceneColors }) {
  const roof = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(-1.05, 0);
    s.lineTo(0, 0.85);
    s.lineTo(1.05, 0);
    s.closePath();
    const g = new THREE.ExtrudeGeometry(s, { depth: 1.5, bevelEnabled: true, bevelSize: 0.03, bevelThickness: 0.03, bevelSegments: 2 });
    g.translate(0, 0, -0.75);
    return g;
  }, []);
  const wall = <meshStandardMaterial color="#f4f1ea" roughness={0.6} />;
  const glass = <meshPhysicalMaterial color={c.accent} emissive={c.accent} emissiveIntensity={0.55} roughness={0.1} />;
  return (
    <group rotation={[0.18, -0.65, 0]} position={[0, -0.35, 0]}>
      <mesh position={[0, -0.86, 0]}>
        <cylinderGeometry args={[1.85, 1.85, 0.12, 64]} />
        <meshStandardMaterial color={c.secondary} roughness={0.8} />
      </mesh>
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[1.8, 1.6, 1.3]} />
        {wall}
      </mesh>
      <mesh geometry={roof} position={[0, 0.8, 0]}>
        <meshStandardMaterial color={c.primary} roughness={0.45} />
      </mesh>
      <mesh position={[0.55, 1.35, -0.25]}>
        <boxGeometry args={[0.22, 0.5, 0.22]} />
        {wall}
      </mesh>
      <mesh position={[0, -0.38, 0.66]}>
        <boxGeometry args={[0.38, 0.8, 0.04]} />
        <meshStandardMaterial color={c.primary} roughness={0.4} />
      </mesh>
      {[-0.55, 0.55].map((x) => (
        <mesh key={x} position={[x, 0.2, 0.66]}>
          <boxGeometry args={[0.38, 0.38, 0.04]} />
          {glass}
        </mesh>
      ))}
      <mesh position={[0.91, 0.1, 0]} rotation={[0, Math.PI / 2, 0]}>
        <boxGeometry args={[0.6, 0.45, 0.04]} />
        {glass}
      </mesh>
    </group>
  );
}

function Wrench({ c }: { c: SceneColors }) {
  const geos = useMemo(() => {
    const ext = { depth: 0.22, bevelEnabled: true, bevelSize: 0.04, bevelThickness: 0.04, bevelSegments: 3, curveSegments: 48 };
    // open-jaw head
    const R = 0.58;
    const cx = 1.25;
    const jaw = new THREE.Shape();
    const a0 = (32 * Math.PI) / 180;
    jaw.moveTo(cx + R * Math.cos(a0), R * Math.sin(a0));
    jaw.absarc(cx, 0, R, a0, Math.PI * 2 - a0, false);
    jaw.lineTo(cx + 0.02, -0.19);
    jaw.lineTo(cx + 0.02, 0.19);
    jaw.closePath();
    // ring end with hex hole
    const ring = new THREE.Shape();
    ring.absarc(-1.35, 0, 0.45, 0, Math.PI * 2, false);
    const hole = new THREE.Path();
    for (let i = 0; i <= 6; i++) {
      const a = (i / 6) * Math.PI * 2 + Math.PI / 6;
      const x = -1.35 + 0.24 * Math.cos(a);
      const y = 0.24 * Math.sin(a);
      if (i === 0) hole.moveTo(x, y);
      else hole.lineTo(x, y);
    }
    ring.holes.push(hole);
    // handle
    const h = new THREE.Shape();
    h.moveTo(-1.1, -0.17);
    h.lineTo(0.85, -0.2);
    h.lineTo(0.85, 0.2);
    h.lineTo(-1.1, 0.17);
    h.closePath();
    const center = (g: THREE.ExtrudeGeometry) => {
      g.translate(0, 0, -0.11);
      return g;
    };
    return {
      jaw: center(new THREE.ExtrudeGeometry(jaw, ext)),
      ring: center(new THREE.ExtrudeGeometry(ring, ext)),
      handle: center(new THREE.ExtrudeGeometry(h, ext)),
    };
  }, []);
  const steel = <meshStandardMaterial color="#d5d9e0" metalness={1} roughness={0.26} />;
  return (
    <group rotation={[0.5, 0.35, 0.6]} scale={1.0}>
      <mesh geometry={geos.jaw}>{steel}</mesh>
      <mesh geometry={geos.ring}>{steel}</mesh>
      <mesh geometry={geos.handle}>{steel}</mesh>
      <mesh position={[-0.15, 0, 0]} rotation={[0, 0, Math.PI / 2]} scale={[1, 1, 0.5]}>
        <capsuleGeometry args={[0.22, 0.9, 8, 24]} />
        <meshStandardMaterial color={c.primary} roughness={0.5} />
      </mesh>
    </group>
  );
}

function Orb({ c }: { c: SceneColors }) {
  return (
    <group>
      <mesh>
        <sphereGeometry args={[1.05, 128, 128]} />
        <MeshDistortMaterial color={c.primary} distort={0.32} speed={1.6} roughness={0.12} metalness={0.15} />
      </mesh>
      <mesh rotation={[Math.PI / 2.4, 0.3, 0]}>
        <torusGeometry args={[1.65, 0.015, 16, 160]} />
        <meshStandardMaterial color={c.accent} emissive={c.accent} emissiveIntensity={0.9} />
      </mesh>
      <mesh rotation={[Math.PI / 1.8, -0.5, 0.4]}>
        <torusGeometry args={[1.95, 0.01, 16, 160]} />
        <meshStandardMaterial color={c.secondary} emissive={c.secondary} emissiveIntensity={0.9} />
      </mesh>
      <mesh position={[1.55, 0.75, 0.3]} scale={0.14}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshStandardMaterial color={c.secondary} roughness={0.2} metalness={0.4} />
      </mesh>
    </group>
  );
}

const MODELS: Record<HeroModel, (p: { c: SceneColors }) => ReactNode> = {
  tooth: Tooth,
  plate: Plate,
  droplet: Droplet,
  dumbbell: Dumbbell,
  pillar: Pillar,
  house: House,
  wrench: Wrench,
  orb: Orb,
};

/* ---------------------------------------------------------------- rig */

function Rig({ children }: { children: ReactNode }) {
  const g = useRef<THREE.Group>(null);
  useFrame((state, delta) => {
    if (!g.current) return;
    const { x, y } = state.pointer;
    g.current.rotation.y += delta * 0.18;
    g.current.rotation.x = THREE.MathUtils.damp(g.current.rotation.x, -y * 0.25, 3, delta);
    g.current.position.x = THREE.MathUtils.damp(g.current.position.x, x * 0.15, 3, delta);
  });
  return <group ref={g}>{children}</group>;
}

function ReadySignal({ onReady }: { onReady: () => void }) {
  const fired = useRef(false);
  useFrame(() => {
    if (!fired.current) {
      fired.current = true;
      requestAnimationFrame(() => onReady());
    }
  });
  return null;
}

export default function HeroScene({
  model,
  colors,
  active,
  onReady,
}: {
  model: HeroModel;
  colors: SceneColors;
  active: boolean;
  onReady: () => void;
}) {
  const Model = MODELS[model] ?? Orb;
  useEffect(() => () => THREE.Cache.clear(), []);
  return (
    <Canvas
      dpr={[1, 1.75]}
      frameloop={active ? "always" : "never"}
      gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
      camera={{ position: [0, 0.2, 7], fov: 34 }}
      style={{ width: "100%", height: "100%" }}
    >
      <ambientLight intensity={colors.dark ? 0.35 : 0.55} />
      <directionalLight position={[3, 4, 5]} intensity={1.6} />
      <directionalLight position={[-4, -2, -3]} intensity={0.6} color={colors.secondary} />
      <Environment resolution={256} frames={1}>
        <Lightformer form="rect" intensity={2.2} position={[0, 4, 3]} scale={[8, 2, 1]} />
        <Lightformer form="rect" intensity={1.4} position={[-5, 1, 1]} rotation-y={Math.PI / 2} scale={[6, 2, 1]} color={colors.primary} />
        <Lightformer form="rect" intensity={1.1} position={[5, -1, 1]} rotation-y={-Math.PI / 2} scale={[6, 2, 1]} color={colors.accent} />
        <Lightformer form="ring" intensity={1.5} position={[0, 0, -6]} scale={4} />
      </Environment>
      <Float speed={1.6} rotationIntensity={0.35} floatIntensity={0.9}>
        <Rig>
          <Model c={colors} />
        </Rig>
      </Float>
      <ContactShadows position={[0, -1.75, 0]} opacity={colors.dark ? 0.55 : 0.32} scale={7} blur={2.6} far={3} frames={1} />
      <ReadySignal onReady={onReady} />
    </Canvas>
  );
}
