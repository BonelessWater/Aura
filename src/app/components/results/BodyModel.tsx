import React, { useRef, useState, useMemo, useCallback, useEffect, Suspense } from 'react';
import { Canvas, useFrame, useThree, ThreeEvent } from '@react-three/fiber';
import { OrbitControls, Html, useGLTF, useAnimations } from '@react-three/drei';
import { motion, AnimatePresence } from 'motion/react';
import { X } from 'lucide-react';
import * as THREE from 'three';

// -- Severity levels with 3 distinct color tiers --
const SEVERITY_COLORS = {
  high: '#E07070',
  moderate: '#F4A261',
  low: '#3ECFCF',
} as const;

const SEVERITY_LABELS = {
  high: 'Strong match',
  moderate: 'Moderate',
  low: 'Noted',
} as const;

// -- Affected body regions with patient-friendly info --
// Positions are calibrated to the Ready Player Me GLB skeleton
interface BodyRegion {
  id: string;
  label: string;
  boneName: string;
  offset: [number, number, number];
  radius: number;
  severity: keyof typeof SEVERITY_COLORS;
  status: string;
  explanation: string;
}

const bodyRegions: BodyRegion[] = [
  {
    id: 'head',
    label: 'Face -- Malar Rash',
    boneName: 'Head',
    offset: [0, 0.06, 0.08],
    radius: 0.06,
    severity: 'high',
    status: '95% match',
    explanation:
      'The butterfly-shaped rash across your cheeks and nose is a strong indicator. Photo analysis shows a pattern highly consistent with malar rash seen in autoimmune conditions.',
  },
  {
    id: 'chest',
    label: 'Chest -- Abnormal Blood Markers',
    boneName: 'Spine2',
    offset: [0, 0.05, 0.08],
    radius: 0.07,
    severity: 'high',
    status: '3 markers flagged',
    explanation:
      'Your CRP is 5x normal, white blood cells are below range, and ANA antibodies are significantly elevated. Together these paint a picture of systemic immune overactivity.',
  },
  {
    id: 'right_hand',
    label: 'Right Hand -- Joint Pain',
    boneName: 'RightHand',
    offset: [0, 0, 0],
    radius: 0.03,
    severity: 'moderate',
    status: 'Reported symptom',
    explanation:
      'You reported stiffness and swelling in your finger joints, especially in the morning. This is a commonly reported symptom in autoimmune profiles.',
  },
  {
    id: 'left_hand',
    label: 'Left Hand -- Joint Pain',
    boneName: 'LeftHand',
    offset: [0, 0, 0],
    radius: 0.03,
    severity: 'moderate',
    status: 'Reported symptom',
    explanation:
      'You reported stiffness and swelling in your finger joints, especially in the morning. This is a commonly reported symptom in autoimmune profiles.',
  },
  {
    id: 'right_knee',
    label: 'Right Knee -- Joint Pain',
    boneName: 'RightLeg',
    offset: [0, 0.02, 0.02],
    radius: 0.04,
    severity: 'moderate',
    status: 'Reported symptom',
    explanation:
      'Knee pain and swelling you described can indicate inflammatory joint involvement, which is present in many autoimmune conditions.',
  },
  {
    id: 'left_knee',
    label: 'Left Knee -- Joint Pain',
    boneName: 'LeftLeg',
    offset: [0, 0.02, 0.02],
    radius: 0.04,
    severity: 'moderate',
    status: 'Reported symptom',
    explanation:
      'Knee pain and swelling you described can indicate inflammatory joint involvement, which is present in many autoimmune conditions.',
  },
  {
    id: 'whole_body',
    label: 'Whole Body -- Fatigue',
    boneName: 'Spine1',
    offset: [0, 0, 0],
    radius: 0.09,
    severity: 'low',
    status: 'Reported symptom',
    explanation:
      'Persistent, debilitating fatigue is one of the most common autoimmune symptoms. You described it as feeling exhausted even after a full night of sleep.',
  },
];

// -- GLTF human body model with skeleton-anchored hotspots --
const MODEL_PATH = '/models/human_body.glb';

function HumanBody({
  onSelectRegion,
  activeRegion,
}: {
  onSelectRegion: (region: BodyRegion | null) => void;
  activeRegion: string | null;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const { scene, nodes } = useGLTF(MODEL_PATH) as any;

  // Slow idle rotation
  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y =
        Math.sin(state.clock.elapsedTime * 0.15) * 0.15;
    }
  });

  // Map bone names to canonical body_region IDs (matching backend VALID_BODY_REGIONS)
  const boneToRegion = useMemo<Record<string, string>>(() => ({
    Head: 'head', Neck: 'neck', LeftEye: 'head', RightEye: 'head',
    Spine2: 'chest', LeftShoulder: 'left_shoulder', RightShoulder: 'right_shoulder',
    RightArm: 'right_upper_arm', LeftArm: 'left_upper_arm',
    Spine: 'abdomen', Spine1: 'whole_body', Hips: 'abdomen',
    RightHand: 'right_hand', RightForeArm: 'right_forearm',
    RightHandThumb1: 'right_hand', RightHandThumb2: 'right_hand',
    RightHandThumb3: 'right_hand', RightHandThumb4: 'right_hand',
    RightHandIndex1: 'right_hand', RightHandIndex2: 'right_hand',
    RightHandIndex3: 'right_hand', RightHandIndex4: 'right_hand',
    RightHandMiddle1: 'right_hand', RightHandMiddle2: 'right_hand',
    RightHandMiddle3: 'right_hand', RightHandMiddle4: 'right_hand',
    RightHandRing1: 'right_hand', RightHandRing2: 'right_hand',
    RightHandRing3: 'right_hand', RightHandRing4: 'right_hand',
    RightHandPinky1: 'right_hand', RightHandPinky2: 'right_hand',
    RightHandPinky3: 'right_hand', RightHandPinky4: 'right_hand',
    LeftHand: 'left_hand', LeftForeArm: 'left_forearm',
    LeftHandThumb1: 'left_hand', LeftHandThumb2: 'left_hand',
    LeftHandThumb3: 'left_hand', LeftHandThumb4: 'left_hand',
    LeftHandIndex1: 'left_hand', LeftHandIndex2: 'left_hand',
    LeftHandIndex3: 'left_hand', LeftHandIndex4: 'left_hand',
    LeftHandMiddle1: 'left_hand', LeftHandMiddle2: 'left_hand',
    LeftHandMiddle3: 'left_hand', LeftHandMiddle4: 'left_hand',
    LeftHandRing1: 'left_hand', LeftHandRing2: 'left_hand',
    LeftHandRing3: 'left_hand', LeftHandRing4: 'left_hand',
    LeftHandPinky1: 'left_hand', LeftHandPinky2: 'left_hand',
    LeftHandPinky3: 'left_hand', LeftHandPinky4: 'left_hand',
    RightLeg: 'right_knee', RightUpLeg: 'right_upper_leg',
    LeftLeg: 'left_knee', LeftUpLeg: 'left_upper_leg',
    RightFoot: 'right_foot', RightToeBase: 'right_foot',
    LeftFoot: 'left_foot', LeftToeBase: 'left_foot',
  }), []);

  const regionSeverityMap = useMemo(() => {
    const m: Record<string, keyof typeof SEVERITY_COLORS> = {};
    bodyRegions.forEach((r) => { m[r.id] = r.severity; });
    return m;
  }, []);

  // Paint vertex colors on skinned meshes based on bone weights
  useEffect(() => {
    const base = new THREE.Color('#4a5568');
    const sevColors: Record<string, THREE.Color> = {
      high: new THREE.Color(SEVERITY_COLORS.high),
      moderate: new THREE.Color(SEVERITY_COLORS.moderate),
      low: new THREE.Color(SEVERITY_COLORS.low),
    };

    scene.traverse((child: any) => {
      if (child.isSkinnedMesh) {
        const geom = child.geometry;
        const si = geom.attributes.skinIndex;
        const sw = geom.attributes.skinWeight;
        const skeleton = child.skeleton;
        if (!si || !sw || !skeleton) return;

        const n = geom.attributes.position.count;
        const colors = new Float32Array(n * 3);
        for (let i = 0; i < n; i++) {
          let maxW = 0, domIdx = 0;
          for (let j = 0; j < 4; j++) {
            const w = sw.getComponent(i, j);
            if (w > maxW) { maxW = w; domIdx = si.getComponent(i, j); }
          }
          const bone = skeleton.bones[domIdx];
          const regionId = bone ? boneToRegion[bone.name] : undefined;
          const sev = regionId ? regionSeverityMap[regionId] : undefined;
          const c = sev && sevColors[sev]
            ? base.clone().lerp(sevColors[sev], 0.55)
            : base.clone();
          colors[i * 3] = c.r;
          colors[i * 3 + 1] = c.g;
          colors[i * 3 + 2] = c.b;
        }
        geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const oldMat = child.material;
        child.material = new THREE.MeshPhysicalMaterial({
          vertexColors: true,
          emissive: '#1a1a2e',
          emissiveIntensity: 0.4,
          roughness: 0.4,
          metalness: 0.25,
          clearcoat: 0.6,
          clearcoatRoughness: 0.3,
          transparent: true,
          opacity: 0.9,
          depthWrite: true,
        });
        if (child.isSkinnedMesh) child.material.skinning = true;
        if (oldMat?.dispose) oldMat.dispose();
      } else if (child.isMesh) {
        const oldMat = child.material;
        child.material = new THREE.MeshPhysicalMaterial({
          color: '#4a5568',
          emissive: '#2d3748',
          emissiveIntensity: 0.5,
          roughness: 0.4,
          metalness: 0.3,
          transparent: true,
          opacity: 0.85,
          depthWrite: true,
        });
        if (oldMat?.dispose) oldMat.dispose();
      }
    });
  }, [scene, boneToRegion, regionSeverityMap]);

  // Find bone world positions for hotspot anchoring
  const bonePositions = useMemo(() => {
    const positions: Record<string, THREE.Vector3> = {};
    scene.traverse((child: any) => {
      if (child.isBone) {
        const worldPos = new THREE.Vector3();
        child.getWorldPosition(worldPos);
        positions[child.name] = worldPos;
      }
    });
    return positions;
  }, [scene]);

  return (
    <group ref={groupRef} position={[0, -0.9, 0]} scale={1}>
      <primitive object={scene} />

      {/* Click targets anchored to skeleton bones */}
      {bodyRegions.map((region) => {
        const bonePos = bonePositions[region.boneName];
        if (!bonePos) return null;

        const position: [number, number, number] = [
          bonePos.x + region.offset[0],
          bonePos.y + region.offset[1],
          bonePos.z + region.offset[2],
        ];

        return (
          <ClickTarget
            key={region.id}
            region={region}
            position={position}
            onClick={(r) =>
              onSelectRegion(activeRegion === r.id ? null : r)
            }
            isActive={activeRegion === region.id}
          />
        );
      })}
    </group>
  );
}

// -- Invisible click target with ring indicator on hover/active --
function ClickTarget({
  region,
  position,
  onClick,
  isActive,
}: {
  region: BodyRegion;
  position: [number, number, number];
  onClick: (region: BodyRegion) => void;
  isActive: boolean;
}) {
  const ringRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const { gl } = useThree();
  const color = SEVERITY_COLORS[region.severity];

  useFrame((state) => {
    if (ringRef.current) {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 3) * 0.12;
      ringRef.current.scale.setScalar(isActive ? pulse * 1.2 : pulse);
      ringRef.current.rotation.z = state.clock.elapsedTime * 0.4;
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

  const handleClick = useCallback(
    (e: ThreeEvent<MouseEvent>) => {
      e.stopPropagation();
      onClick(region);
    },
    [onClick, region]
  );

  return (
    <group position={position}>
      {/* Invisible click target */}
      <mesh
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
        onClick={handleClick}
      >
        <sphereGeometry args={[region.radius * 1.5, 12, 12]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* Ring indicator on hover/active */}
      {(hovered || isActive) && (
        <mesh ref={ringRef}>
          <ringGeometry args={[region.radius * 0.8, region.radius * 1.1, 32]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={isActive ? 0.7 : 0.4}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}

      {/* Label */}
      {(hovered || isActive) && (
        <Html
          distanceFactor={3}
          position={[region.radius + 0.06, 0.03, 0]}
          style={{ pointerEvents: 'none' }}
        >
          <div className="whitespace-nowrap bg-[#13161F]/95 border border-white/[0.1] text-white text-[11px] font-medium px-2.5 py-1 rounded-lg shadow-xl backdrop-blur-sm">
            {region.label}
          </div>
        </Html>
      )}
    </group>
  );
}

// -- Scene wrapper --
function BodyScene({
  onSelectRegion,
  activeRegion,
}: {
  onSelectRegion: (region: BodyRegion | null) => void;
  activeRegion: string | null;
}) {
  return (
    <>
      <ambientLight intensity={0.8} />
      <directionalLight
        position={[3, 5, 5]}
        intensity={2.0}
        color="#e8e0f0"
      />
      <directionalLight
        position={[-2, 3, -3]}
        intensity={0.8}
        color="#c0b8d8"
      />
      <pointLight position={[-3, -2, 3]} intensity={1.0} color="#7B61FF" />
      <pointLight position={[2, -1, -3]} intensity={0.8} color="#3ECFCF" />
      <pointLight position={[0, 2, -2]} intensity={0.5} color="#9F7AEA" />

      <Suspense fallback={null}>
        <HumanBody
          onSelectRegion={onSelectRegion}
          activeRegion={activeRegion}
        />
      </Suspense>

      <OrbitControls
        enableZoom={false}
        enablePan={false}
        minPolarAngle={Math.PI * 0.3}
        maxPolarAngle={Math.PI * 0.7}
        minAzimuthAngle={-Math.PI * 0.35}
        maxAzimuthAngle={Math.PI * 0.35}
      />
    </>
  );
}

// -- Main BodyModel overlay (same API as original) --
export const BodyModel = ({ onClose }: { onClose: () => void }) => {
  const [activeRegion, setActiveRegion] = useState<string | null>(null);
  const selectedRegion =
    bodyRegions.find((r) => r.id === activeRegion) ?? null;

  return (
    <div className="fixed inset-0 z-[60] flex flex-col bg-[#0A0D14]/95 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
        <div>
          <h2 className="text-lg font-medium text-[#F0F2F8]">
            Your Body Map
          </h2>
          <p className="text-xs text-[#8A93B2] mt-0.5">
            Tap the glowing areas to see what we found
          </p>
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
          <Canvas camera={{ position: [0, 0.1, 2.2], fov: 40 }}>
            <BodyScene
              onSelectRegion={(r) => setActiveRegion(r?.id ?? null)}
              activeRegion={activeRegion}
            />
          </Canvas>

          {/* Legend -- 3 severity levels */}
          <div className="absolute bottom-4 left-4 flex items-center gap-4">
            {(
              Object.entries(SEVERITY_COLORS) as [
                keyof typeof SEVERITY_COLORS,
                string,
              ][]
            ).map(([level, color]) => (
              <div key={level} className="flex items-center gap-1.5">
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{
                    backgroundColor: color,
                    boxShadow: `0 0 8px ${color}60`,
                  }}
                />
                <span className="text-[10px] text-[#8A93B2] capitalize">
                  {SEVERITY_LABELS[level]}
                </span>
              </div>
            ))}
          </div>

          {/* Model attribution */}
          <div className="absolute bottom-4 right-4">
            <span className="text-[9px] text-[#8A93B2]/40">
              3D model: Ready Player Me / hmthanh (MIT)
            </span>
          </div>
        </div>

        {/* Side panel -- region detail */}
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
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{
                      backgroundColor:
                        SEVERITY_COLORS[selectedRegion.severity],
                      boxShadow: `0 0 12px ${SEVERITY_COLORS[selectedRegion.severity]}80`,
                    }}
                  />
                  <h3 className="text-base font-medium text-[#F0F2F8]">
                    {selectedRegion.label}
                  </h3>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className="text-xs font-semibold px-2.5 py-1 rounded-full"
                    style={{
                      backgroundColor: `${SEVERITY_COLORS[selectedRegion.severity]}20`,
                      color: SEVERITY_COLORS[selectedRegion.severity],
                    }}
                  >
                    {SEVERITY_LABELS[selectedRegion.severity]}
                  </span>
                  <span className="text-xs text-[#8A93B2]">
                    {selectedRegion.status}
                  </span>
                </div>

                <p className="text-sm text-[#8A93B2] leading-relaxed">
                  {selectedRegion.explanation}
                </p>

                {/* Severity scale bar */}
                <div className="pt-3">
                  <div className="text-[10px] text-[#8A93B2]/60 mb-2">
                    Severity Scale
                  </div>
                  <div className="flex gap-1 h-2 rounded-full overflow-hidden">
                    {(
                      ['low', 'moderate', 'high'] as (keyof typeof SEVERITY_COLORS)[]
                    ).map((level) => (
                      <div
                        key={level}
                        className="flex-1 rounded-full transition-opacity duration-300"
                        style={{
                          backgroundColor: SEVERITY_COLORS[level],
                          opacity:
                            level === selectedRegion.severity ? 1 : 0.15,
                        }}
                      />
                    ))}
                  </div>
                  <div className="flex justify-between mt-1">
                    <span className="text-[9px] text-[#8A93B2]/40">Low</span>
                    <span className="text-[9px] text-[#8A93B2]/40">
                      Moderate
                    </span>
                    <span className="text-[9px] text-[#8A93B2]/40">High</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-white/[0.06]">
                  <p className="text-[10px] text-[#8A93B2]/60">
                    This is based on your uploaded data and published
                    research. Only a doctor can confirm these findings.
                  </p>
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
                  <svg
                    viewBox="0 0 24 24"
                    className="w-7 h-7 text-[#7B61FF]"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.5}
                  >
                    <circle cx="12" cy="5" r="3" />
                    <path d="M12 8v8M8 12h8M10 20h4" />
                  </svg>
                </div>
                <p className="text-sm text-[#F0F2F8] font-medium mb-1">
                  Tap a highlighted area
                </p>
                <p className="text-xs text-[#8A93B2] max-w-[240px]">
                  Each glowing spot represents something we found in your
                  data. Tap one to learn what it means.
                </p>

                {/* Quick summary list of all regions */}
                <div className="mt-6 space-y-2 w-full text-left">
                  {bodyRegions
                    .filter(
                      (r, i, arr) =>
                        arr.findIndex((a) => a.label === r.label) === i
                    )
                    .map((region) => (
                      <button
                        key={region.id}
                        onClick={() => setActiveRegion(region.id)}
                        className="w-full flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.12] transition-colors text-left"
                      >
                        <div
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{
                            backgroundColor:
                              SEVERITY_COLORS[region.severity],
                            boxShadow: `0 0 6px ${SEVERITY_COLORS[region.severity]}50`,
                          }}
                        />
                        <span className="text-xs text-[#F0F2F8]">
                          {region.label}
                        </span>
                        <span className="ml-auto text-[10px] text-[#8A93B2]">
                          {region.status}
                        </span>
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

// Preload the model
useGLTF.preload(MODEL_PATH);
