import React, { useRef, useMemo, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { motion, useMotionTemplate, useMotionValue } from "motion/react";
import * as THREE from "three";
import { Sparkles } from "@react-three/drei";

// ── Biconcave disc geometry (real RBC silhouette via LatheGeometry) ───────────
// Profile traces the outer cross-section of an RBC from top-center
// around the outer rim to bottom-center, revolved around Y axis.
function makeBiconcaveGeometry(): THREE.BufferGeometry {
  const profile: THREE.Vector2[] = [
    new THREE.Vector2(0.00,  0.055),
    new THREE.Vector2(0.14,  0.045),
    new THREE.Vector2(0.35,  0.095),
    new THREE.Vector2(0.55,  0.130),
    new THREE.Vector2(0.68,  0.082),
    new THREE.Vector2(0.75,  0.000),
    new THREE.Vector2(0.68, -0.082),
    new THREE.Vector2(0.55, -0.130),
    new THREE.Vector2(0.35, -0.095),
    new THREE.Vector2(0.14, -0.045),
    new THREE.Vector2(0.00, -0.055),
  ];
  return new THREE.LatheGeometry(profile, 48);
}

// ── Single cell — shared geometry, individual material color ─────────────────
interface CellProps {
  homePos: [number, number, number];
  initRot: [number, number, number];
  scale: number;
  driftSpeed: number;
  spinSpeed: number;
  ox: number; oy: number; oz: number;
  isWhite?: boolean;
  geo: THREE.BufferGeometry;
}

const Cell: React.FC<CellProps> = ({
  homePos, initRot, scale, driftSpeed, spinSpeed, ox, oy, oz, isWhite = false, geo,
}) => {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.elapsedTime;
    // Continuous upward flow — speed varies per cell, wraps top→bottom
    const wrapH = 16;                                      // slightly taller than visible
    const rawY = homePos[1] + t * driftSpeed * 70;
    const y = ((rawY % wrapH) + wrapH) % wrapH - wrapH / 2;
    // Gentle lateral wobble proportional to speed (fast cells sway more)
    const sway = 0.8 + driftSpeed * 50;
    const x = homePos[0] + Math.sin(t * driftSpeed * 2.5 + ox) * sway;
    const z = homePos[2] + Math.sin(t * driftSpeed * 0.8 + oz) * 0.6;
    ref.current.position.set(x, y, z);
    ref.current.rotation.x = initRot[0] + t * spinSpeed * 0.8;
    ref.current.rotation.y = initRot[1] + t * spinSpeed;
    ref.current.rotation.z = initRot[2] + t * spinSpeed * 0.6;
  });
  return (
    <mesh ref={ref} geometry={geo} scale={[scale, scale, scale]}>
      {isWhite ? (
        <meshPhysicalMaterial
          color="#dde8f4"
          emissive="#080e1e"
          emissiveIntensity={0.2}
          roughness={0.28}
          metalness={0.0}
          clearcoat={1.0}
          clearcoatRoughness={0.05}
          transmission={0.38}
          thickness={1.8}
          opacity={0.88}
          transparent
        />
      ) : (
        <meshPhysicalMaterial
          color="#a01020"
          emissive="#2a0008"
          emissiveIntensity={0.4}
          roughness={0.18}
          metalness={0.0}
          clearcoat={0.85}
          clearcoatRoughness={0.08}
          transmission={0.1}
          thickness={1.0}
        />
      )}
    </mesh>
  );
};

// ── Scene: 12 RBCs + 4 WBCs always inside camera frustum ─────────────────────
// Camera z=15, fov=45 → visible at z=0 is ±6.2 Y, ±11 X (16:9)
const Scene: React.FC = () => {
  const geo = useMemo(() => makeBiconcaveGeometry(), []);

  const rbcs = useMemo<Omit<CellProps,'geo'>[]>(() => [
    { homePos: [-8.5,  3.5, -2.0], initRot: [0.3, 0.8, 0.2], scale: 1.05, driftSpeed: 0.012, spinSpeed: 0.018, ox: 0,   oy: 1,   oz: 2   },
    { homePos: [-6.0,  0.5,  1.5], initRot: [1.1, 0.2, 0.9], scale: 0.75, driftSpeed: 0.022, spinSpeed: 0.031, ox: 10,  oy: 20,  oz: 30  },
    { homePos: [-3.5,  4.2, -1.0], initRot: [0.5, 1.4, 0.7], scale: 0.90, driftSpeed: 0.009, spinSpeed: 0.014, ox: 5,   oy: 15,  oz: 25  },
    { homePos: [-1.0,  2.0,  2.5], initRot: [1.8, 0.6, 1.2], scale: 1.20, driftSpeed: 0.017, spinSpeed: 0.024, ox: 40,  oy: 50,  oz: 60  },
    { homePos: [ 1.5,  4.8, -2.5], initRot: [0.9, 1.1, 0.3], scale: 0.65, driftSpeed: 0.028, spinSpeed: 0.042, ox: 7,   oy: 17,  oz: 27  },
    { homePos: [ 4.0,  1.5,  1.0], initRot: [0.2, 0.5, 1.6], scale: 1.35, driftSpeed: 0.007, spinSpeed: 0.011, ox: 80,  oy: 90,  oz: 100 },
    { homePos: [ 7.0,  3.0, -1.5], initRot: [1.3, 0.9, 0.5], scale: 0.80, driftSpeed: 0.019, spinSpeed: 0.027, ox: 33,  oy: 44,  oz: 55  },
    { homePos: [-7.5, -2.0,  0.5], initRot: [0.7, 1.5, 1.0], scale: 1.15, driftSpeed: 0.013, spinSpeed: 0.020, ox: 22,  oy: 33,  oz: 44  },
    { homePos: [-4.0, -4.0, -2.0], initRot: [1.6, 0.3, 0.8], scale: 0.70, driftSpeed: 0.025, spinSpeed: 0.038, ox: 66,  oy: 77,  oz: 88  },
    { homePos: [-0.5, -3.5,  1.5], initRot: [0.4, 1.2, 1.4], scale: 1.00, driftSpeed: 0.015, spinSpeed: 0.022, ox: 11,  oy: 22,  oz: 33  },
    { homePos: [ 3.5, -2.5, -1.0], initRot: [1.0, 0.7, 0.6], scale: 0.85, driftSpeed: 0.021, spinSpeed: 0.032, ox: 55,  oy: 66,  oz: 77  },
    { homePos: [ 7.5, -4.5,  0.0], initRot: [0.6, 1.3, 1.1], scale: 0.95, driftSpeed: 0.010, spinSpeed: 0.016, ox: 99,  oy: 88,  oz: 77  },
  ], []);

  const wbcs = useMemo<Omit<CellProps,'geo'>[]>(() => [
    { homePos: [-6.5, -1.0, -2.5], initRot: [0.8, 0.4, 1.3], scale: 1.60, driftSpeed: 0.004, spinSpeed: 0.006, ox: 200, oy: 210, oz: 220, isWhite: true },
    { homePos: [ 0.0,  0.0,  0.5], initRot: [1.4, 1.0, 0.5], scale: 1.85, driftSpeed: 0.003, spinSpeed: 0.005, ox: 300, oy: 310, oz: 320, isWhite: true },
    { homePos: [ 5.5, -0.5, -3.0], initRot: [0.3, 1.7, 0.9], scale: 1.65, driftSpeed: 0.005, spinSpeed: 0.007, ox: 400, oy: 410, oz: 420, isWhite: true },
    { homePos: [-2.5,  1.5,  2.0], initRot: [1.2, 0.6, 1.6], scale: 1.45, driftSpeed: 0.006, spinSpeed: 0.008, ox: 500, oy: 510, oz: 520, isWhite: true },
  ], []);

  return (
    <>
      <ambientLight intensity={0.15} color="#ffffff" />
      <directionalLight position={[-8, 10, 8]} intensity={3.5} color="#ffece6" />
      <pointLight position={[10, -8, -4]} intensity={3.0} color="#550010" />
      <pointLight position={[0,   0,  6]} intensity={1.8} color="#0a0516" />
      <pointLight position={[0,   6, 10]} intensity={0.8} color="#d8e8f8" />
      <fog attach="fog" args={["#020005", 14, 30]} />
      {rbcs.map((c, i) => <Cell key={`rbc-${i}`} {...c} geo={geo} />)}
      {wbcs.map((c, i) => <Cell key={`wbc-${i}`} {...c} geo={geo} />)}
      <Sparkles count={200} scale={20} size={1.2} speed={0.3} opacity={0.12} color="#ffb3b3" />
    </>
  );
};

export const Background = () => {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [mouseX, mouseY]);

  const bgGradient = useMotionTemplate`radial-gradient(900px circle at ${mouseX}px ${mouseY}px, rgba(220, 40, 40, 0.07), transparent 40%)`;

  return (
    <div className="fixed inset-0 z-0 overflow-hidden bg-[#020005]">
      <div className="absolute inset-0" style={{ filter: "contrast(1.1) saturate(1.15)" }}>
        <Canvas camera={{ position: [0, 0, 15], fov: 45 }} gl={{ antialias: true }} dpr={[1, 1.5]}>
          <Scene />
        </Canvas>
      </div>
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-[150px] bg-gradient-to-b from-[#020005] to-transparent opacity-90" />
        <div className="absolute bottom-0 left-0 w-full h-[200px] bg-gradient-to-t from-[#0A0D14] to-transparent" />
      </div>
      <motion.div
        className="absolute inset-0 pointer-events-none mix-blend-screen"
        style={{ background: bgGradient }}
      />
    </div>
  );
};
