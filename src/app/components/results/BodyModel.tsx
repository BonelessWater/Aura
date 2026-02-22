import React, { useRef, useState, useMemo, useCallback } from 'react';
import { Canvas, useFrame, useThree, ThreeEvent } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';
import { motion, AnimatePresence } from 'motion/react';
import { X } from 'lucide-react';
import * as THREE from 'three';

// --- Affected body regions with patient-friendly info ---
interface BodyRegion {
  id: string;
  label: string;
  position: [number, number, number];
  radius: number;
  color: string;
  severity: 'high' | 'moderate' | 'low';
  status: string;
  explanation: string;
}

const bodyRegions: BodyRegion[] = [
  {
    id: 'face',
    label: 'Face — Malar Rash',
    position: [0, 1.55, 0.15],
    radius: 0.12,
    color: '#E07070',
    severity: 'high',
    status: '95% match',
    explanation: 'The butterfly-shaped rash across your cheeks and nose is a strong indicator. Photo analysis shows a pattern highly consistent with malar rash seen in autoimmune conditions.',
  },
  {
    id: 'joints-hands',
    label: 'Hands — Joint Pain',
    position: [0.55, 0.45, 0],
    radius: 0.08,
    color: '#F4A261',
    severity: 'moderate',
    status: 'Reported symptom',
    explanation: 'You reported stiffness and swelling in your finger joints, especially in the morning. This is a commonly reported symptom in autoimmune profiles.',
  },
  {
    id: 'joints-hands-l',
    label: 'Hands — Joint Pain',
    position: [-0.55, 0.45, 0],
    radius: 0.08,
    color: '#F4A261',
    severity: 'moderate',
    status: 'Reported symptom',
    explanation: 'You reported stiffness and swelling in your finger joints, especially in the morning. This is a commonly reported symptom in autoimmune profiles.',
  },
  {
    id: 'joints-knees',
    label: 'Knees — Joint Pain',
    position: [0.15, -0.6, 0.05],
    radius: 0.09,
    color: '#F4A261',
    severity: 'moderate',
    status: 'Reported symptom',
    explanation: 'Knee pain and swelling you described can indicate inflammatory joint involvement, which is present in many autoimmune conditions.',
  },
  {
    id: 'blood',
    label: 'Blood — Abnormal Markers',
    position: [0.2, 0.9, 0.1],
    radius: 0.1,
    color: '#E07070',
    severity: 'high',
    status: '3 markers flagged',
    explanation: 'Your CRP is 5x normal, white blood cells are below range, and ANA antibodies are significantly elevated. Together these paint a picture of systemic immune overactivity.',
  },
  {
    id: 'fatigue',
    label: 'Whole Body — Fatigue',
    position: [0, 0.6, 0],
    radius: 0.15,
    color: '#3ECFCF',
    severity: 'moderate',
    status: 'Reported symptom',
    explanation: 'Persistent, debilitating fatigue is one of the most common autoimmune symptoms. You described it as feeling exhausted even after a full night of sleep.',
  },
];

// --- 3D Human Figure built from primitives ---
const HumanFigure = () => {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.15) * 0.12;
    }
  });

  const material = useMemo(() => new THREE.MeshPhysicalMaterial({
    color: '#1a1d26',
    emissive: '#0d0f14',
    roughness: 0.7,
    metalness: 0.1,
    clearcoat: 0.3,
    clearcoatRoughness: 0.4,
    transparent: true,
    opacity: 0.85,
  }), []);

  const outlineMaterial = useMemo(() => new THREE.MeshBasicMaterial({
    color: '#7B61FF',
    transparent: true,
    opacity: 0.06,
    side: THREE.BackSide,
  }), []);

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* Head */}
      <mesh position={[0, 1.55, 0]} material={material}>
        <sphereGeometry args={[0.18, 24, 24]} />
      </mesh>
      <mesh position={[0, 1.55, 0]} material={outlineMaterial}>
        <sphereGeometry args={[0.2, 24, 24]} />
      </mesh>

      {/* Neck */}
      <mesh position={[0, 1.32, 0]} material={material}>
        <cylinderGeometry args={[0.06, 0.07, 0.12, 12]} />
      </mesh>

      {/* Torso */}
      <mesh position={[0, 0.9, 0]} material={material}>
        <capsuleGeometry args={[0.22, 0.55, 8, 16]} />
      </mesh>
      <mesh position={[0, 0.9, 0]} material={outlineMaterial}>
        <capsuleGeometry args={[0.24, 0.57, 8, 16]} />
      </mesh>

      {/* Hips */}
      <mesh position={[0, 0.45, 0]} material={material}>
        <capsuleGeometry args={[0.2, 0.1, 8, 16]} />
      </mesh>

      {/* Left arm */}
      <group position={[-0.32, 1.1, 0]} rotation={[0, 0, 0.2]}>
        <mesh position={[0, -0.18, 0]} material={material}>
          <capsuleGeometry args={[0.055, 0.22, 6, 12]} />
        </mesh>
        <mesh position={[-0.05, -0.48, 0]} material={material}>
          <capsuleGeometry args={[0.045, 0.2, 6, 12]} />
        </mesh>
      </group>

      {/* Right arm */}
      <group position={[0.32, 1.1, 0]} rotation={[0, 0, -0.2]}>
        <mesh position={[0, -0.18, 0]} material={material}>
          <capsuleGeometry args={[0.055, 0.22, 6, 12]} />
        </mesh>
        <mesh position={[0.05, -0.48, 0]} material={material}>
          <capsuleGeometry args={[0.045, 0.2, 6, 12]} />
        </mesh>
      </group>

      {/* Left leg */}
      <group position={[-0.12, 0.3, 0]}>
        <mesh position={[0, -0.22, 0]} material={material}>
          <capsuleGeometry args={[0.07, 0.28, 6, 12]} />
        </mesh>
        <mesh position={[0, -0.6, 0]} material={material}>
          <capsuleGeometry args={[0.055, 0.28, 6, 12]} />
        </mesh>
      </group>

      {/* Right leg */}
      <group position={[0.12, 0.3, 0]}>
        <mesh position={[0, -0.22, 0]} material={material}>
          <capsuleGeometry args={[0.07, 0.28, 6, 12]} />
        </mesh>
        <mesh position={[0, -0.6, 0]} material={material}>
          <capsuleGeometry args={[0.055, 0.28, 6, 12]} />
        </mesh>
      </group>
    </group>
  );
};

// --- Glowing hotspot for affected areas ---
const Hotspot = ({ region, onClick, isActive }: {
  region: BodyRegion;
  onClick: (region: BodyRegion) => void;
  isActive: boolean;
}) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const { gl } = useThree();

  useFrame((state) => {
    if (meshRef.current) {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 2.5) * 0.15;
      const scale = (isActive ? 1.3 : hovered ? 1.15 : 1) * pulse;
      meshRef.current.scale.setScalar(scale);
    }
  });

  const handlePointerOver = useCallback(() => {
    setHovered(true);
    gl.domElement.style.cursor = 'pointer';
  }, [gl]);

  const handlePointerOut = useCallback(() => {
    setHovered(false);
    gl.domElement.style.cursor = 'auto';
  }, [gl]);

  const handleClick = useCallback((e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onClick(region);
  }, [onClick, region]);

  return (
    <group position={region.position}>
      {/* Glow sphere */}
      <mesh
        ref={meshRef}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
        onClick={handleClick}
      >
        <sphereGeometry args={[region.radius, 16, 16]} />
        <meshBasicMaterial
          color={region.color}
          transparent
          opacity={isActive ? 0.6 : hovered ? 0.45 : 0.3}
        />
      </mesh>

      {/* Outer ring glow */}
      <mesh>
        <ringGeometry args={[region.radius * 1.2, region.radius * 1.5, 32]} />
        <meshBasicMaterial
          color={region.color}
          transparent
          opacity={isActive ? 0.2 : 0.08}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Label */}
      {(hovered || isActive) && (
        <Html distanceFactor={3} position={[region.radius + 0.15, 0.05, 0]} style={{ pointerEvents: 'none' }}>
          <div className="whitespace-nowrap bg-[#13161F]/95 border border-white/[0.1] text-white text-[11px] font-medium px-2.5 py-1 rounded-lg shadow-xl backdrop-blur-sm">
            {region.label}
          </div>
        </Html>
      )}
    </group>
  );
};

// --- Scene ---
const BodyScene = ({ onSelectRegion, activeRegion }: {
  onSelectRegion: (region: BodyRegion | null) => void;
  activeRegion: string | null;
}) => (
  <>
    <ambientLight intensity={0.3} />
    <directionalLight position={[3, 5, 5]} intensity={1.2} color="#e8e0f0" />
    <pointLight position={[-3, -2, 3]} intensity={0.6} color="#7B61FF" />
    <pointLight position={[2, -1, -3]} intensity={0.4} color="#3ECFCF" />

    <HumanFigure />

    {bodyRegions.map((region) => (
      <Hotspot
        key={region.id}
        region={region}
        onClick={(r) => onSelectRegion(activeRegion === r.id ? null : r)}
        isActive={activeRegion === region.id}
      />
    ))}

    <OrbitControls
      enableZoom={false}
      enablePan={false}
      minPolarAngle={Math.PI * 0.3}
      maxPolarAngle={Math.PI * 0.7}
      minAzimuthAngle={-Math.PI * 0.3}
      maxAzimuthAngle={Math.PI * 0.3}
    />
  </>
);

// --- Main BodyModel overlay ---
export const BodyModel = ({ onClose }: { onClose: () => void }) => {
  const [activeRegion, setActiveRegion] = useState<string | null>(null);
  const selectedRegion = bodyRegions.find(r => r.id === activeRegion) ?? null;

  return (
    <div className="fixed inset-0 z-[60] flex flex-col bg-[#0A0D14]/95 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
        <div>
          <h2 className="text-lg font-medium text-[#F0F2F8]">Your Body Map</h2>
          <p className="text-xs text-[#8A93B2] mt-0.5">Tap the glowing areas to see what we found</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] transition-colors"
        >
          <X className="w-5 h-5 text-[#8A93B2]" />
        </button>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* 3D Canvas */}
        <div className="flex-1 relative min-h-[400px]">
          <Canvas camera={{ position: [0, 0.7, 2.8], fov: 40 }}>
            <BodyScene
              onSelectRegion={(r) => setActiveRegion(r?.id ?? null)}
              activeRegion={activeRegion}
            />
          </Canvas>

          {/* Legend */}
          <div className="absolute bottom-4 left-4 flex items-center gap-4">
            {[
              { label: 'High', color: '#E07070' },
              { label: 'Moderate', color: '#F4A261' },
              { label: 'Reported', color: '#3ECFCF' },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color, boxShadow: `0 0 8px ${item.color}60` }} />
                <span className="text-[10px] text-[#8A93B2]">{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Side panel — region detail */}
        <div className="lg:w-[380px] border-t lg:border-t-0 lg:border-l border-white/[0.06] overflow-y-auto">
          <AnimatePresence mode="wait">
            {selectedRegion ? (
              <motion.div
                key={selectedRegion.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
                className="p-6 space-y-4"
              >
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: selectedRegion.color, boxShadow: `0 0 12px ${selectedRegion.color}80` }} />
                  <h3 className="text-base font-medium text-[#F0F2F8]">{selectedRegion.label}</h3>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full" style={{
                    backgroundColor: `${selectedRegion.color}20`,
                    color: selectedRegion.color,
                  }}>
                    {selectedRegion.severity === 'high' ? 'Strong match' : selectedRegion.severity === 'moderate' ? 'Moderate' : 'Noted'}
                  </span>
                  <span className="text-xs text-[#8A93B2]">{selectedRegion.status}</span>
                </div>

                <p className="text-sm text-[#8A93B2] leading-relaxed">{selectedRegion.explanation}</p>

                <div className="pt-2 border-t border-white/[0.06]">
                  <p className="text-[10px] text-[#8A93B2]/60">This is based on your uploaded data and published research. Only a doctor can confirm these findings.</p>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="p-6 flex flex-col items-center justify-center h-full text-center"
              >
                <div className="w-16 h-16 rounded-full bg-[#7B61FF]/10 flex items-center justify-center mb-4">
                  <svg viewBox="0 0 24 24" className="w-7 h-7 text-[#7B61FF]" fill="none" stroke="currentColor" strokeWidth={1.5}>
                    <circle cx="12" cy="5" r="3" />
                    <path d="M12 8v8M8 12h8M10 20h4" />
                  </svg>
                </div>
                <p className="text-sm text-[#F0F2F8] font-medium mb-1">Tap a highlighted area</p>
                <p className="text-xs text-[#8A93B2] max-w-[240px]">
                  Each glowing spot represents something we found in your data. Tap one to learn what it means.
                </p>

                {/* Quick summary of all regions */}
                <div className="mt-6 space-y-2 w-full text-left">
                  {bodyRegions.filter((r, i, arr) => arr.findIndex(a => a.label === r.label) === i).map((region) => (
                    <button
                      key={region.id}
                      onClick={() => setActiveRegion(region.id)}
                      className="w-full flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.12] transition-colors text-left"
                    >
                      <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: region.color }} />
                      <span className="text-xs text-[#F0F2F8]">{region.label}</span>
                      <span className="ml-auto text-[10px] text-[#8A93B2]">{region.status}</span>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};
