import React, { useRef, useMemo, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { motion, useMotionTemplate, useMotionValue } from "motion/react";
import * as THREE from "three";
import { Sparkles } from "@react-three/drei";

const BloodCells = ({ count = 120 }) => {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const cells = useMemo(() => {
    const temp = [];
    for (let i = 0; i < count; i++) {
      const zDepth = (Math.random() - 0.5) * 50 - 5;
      temp.push({
        startPos: [
          (Math.random() - 0.5) * 60,
          (Math.random() - 0.5) * 50,
          zDepth,
        ],
        rotation: [Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI],
        scale: 0.6 + Math.random() * 0.8,
        speed: 0.005 + Math.random() * 0.015,
        offsetX: Math.random() * 100,
        offsetY: Math.random() * 100,
        offsetZ: Math.random() * 100,
      });
    }
    return temp;
  }, [count]);

  useFrame((state) => {
    if (!meshRef.current) return;
    const time = state.clock.elapsedTime;

    cells.forEach((cell, i) => {
      const x = cell.startPos[0] + Math.sin(time * cell.speed * 2 + cell.offsetX) * 4;
      const y = cell.startPos[1] + Math.cos(time * cell.speed * 1.5 + cell.offsetY) * 3 + (time * 0.5);
      const z = cell.startPos[2] + Math.sin(time * cell.speed * 1 + cell.offsetZ) * 2;

      dummy.position.set(x, y % 30 < 15 ? y : y - 60, z);

      dummy.rotation.set(
        cell.rotation[0] + time * cell.speed,
        cell.rotation[1] + time * cell.speed * 1.2,
        cell.rotation[2] + time * cell.speed * 0.8
      );

      dummy.scale.set(cell.scale, cell.scale, cell.scale * 0.35);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, count] as any}>
      <torusGeometry args={[0.5, 0.45, 64, 64]} />
      <meshPhysicalMaterial
        color="#8c0716"
        emissive="#1a0002"
        roughness={0.25}
        metalness={0.0}
        clearcoat={0.6}
        clearcoatRoughness={0.1}
        transmission={0.3}
        thickness={1.5}
      />
    </instancedMesh>
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
    <div className="fixed inset-0 -z-10 overflow-hidden bg-[#020005]">
      <div className="absolute inset-0 opacity-80" style={{ filter: "contrast(1.1) saturate(1.2)" }}>
        <Canvas camera={{ position: [0, 0, 15], fov: 45 }}>
          <fog attach="fog" args={["#020005", 10, 35]} />
          <ambientLight intensity={0.1} color="#ffffff" />
          <directionalLight position={[-10, 10, 10]} intensity={3} color="#ffebe6" />
          <pointLight position={[10, -10, -5]} intensity={2.5} color="#450012" />
          <pointLight position={[0, 0, 5]} intensity={1.5} color="#10051a" />
          <BloodCells count={150} />
          <Sparkles count={300} scale={30} size={1.5} speed={0.4} opacity={0.15} color="#ffb3b3" />
        </Canvas>
      </div>
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-[150px] bg-gradient-to-b from-[#020005] to-transparent opacity-90" />
        <div className="absolute bottom-0 left-0 w-full h-[200px] bg-gradient-to-t from-[#0A0D14] to-transparent opacity-100" />
      </div>
      <motion.div
        className="absolute inset-0 pointer-events-none mix-blend-screen"
        style={{ background: bgGradient }}
      />
    </div>
  );
};
