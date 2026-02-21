import React, { useEffect, useRef } from 'react';
import { motion, useMotionTemplate, useMotionValue } from 'motion/react';

export const Background = () => {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = window.innerWidth;
    let height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;
    let time = 0;

    /* ── Blood cells — red & white donut-shaped discs ── */
    interface Cell {
      x: number; y: number; vx: number; vy: number;
      r: number;
      kind: 'red' | 'white';
      alpha: number;
      depth: number;
      seed: number;
      // 3D rotation angles (radians) — tumble in all axes
      rx: number; ry: number; rz: number;
      // 3D angular velocities
      rxV: number; ryV: number; rzV: number;
      // Collision bump velocity
      bumpVx: number; bumpVy: number;
    }

    const cells: Cell[] = [];
    const cellCount = 70;

    for (let i = 0; i < cellCount; i++) {
      const kind: Cell['kind'] = i < cellCount * 0.75 ? 'red' : 'white';
      const depth = 0.4 + Math.random() * 0.6;
      cells.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (0.3 + Math.random() * 0.7) * depth,
        vy: (Math.random() - 0.5) * 0.3,
        r: kind === 'red' ? 24 + Math.random() * 16 : 26 + Math.random() * 14,
        kind,
        alpha: kind === 'red' ? 0.35 + Math.random() * 0.20 : 0.30 + Math.random() * 0.20,
        depth,
        seed: Math.random() * 1000,
        // Start with random 3D orientations
        rx: Math.random() * Math.PI * 2,
        ry: Math.random() * Math.PI * 2,
        rz: Math.random() * Math.PI * 2,
        // Start nearly still — occasional slow spins triggered in the loop
        rxV: 0,
        ryV: 0,
        rzV: 0,
        bumpVx: 0,
        bumpVy: 0,
      });
    }

    cells.sort((a, b) => a.depth - b.depth);

    /* ── Simple collision detection — cells deflect off each other ── */
    const resolveCollisions = () => {
      for (let i = 0; i < cells.length; i++) {
        for (let j = i + 1; j < cells.length; j++) {
          const a = cells[i];
          const b = cells[j];
          // Only collide cells at similar depths
          if (Math.abs(a.depth - b.depth) > 0.25) continue;

          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const minDist = (a.r * a.depth + b.r * b.depth) * 0.85;

          if (dist < minDist && dist > 0) {
            // Normalised collision vector
            const nx = dx / dist;
            const ny = dy / dist;
            const overlap = minDist - dist;

            // Push apart
            const pushForce = overlap * 0.15;
            a.bumpVx -= nx * pushForce;
            a.bumpVy -= ny * pushForce;
            b.bumpVx += nx * pushForce;
            b.bumpVy += ny * pushForce;

            // Gentle spin nudge on collision — slow and subtle
            const spinKick = 0.004 + Math.random() * 0.006;
            a.rxV += (Math.random() - 0.5) * spinKick;
            a.ryV += (Math.random() - 0.5) * spinKick;
            b.rxV += (Math.random() - 0.5) * spinKick;
            b.ryV += (Math.random() - 0.5) * spinKick;
          }
        }
      }
    };

    /* ── Draw a 3D donut-shaped blood cell with lighting ── */
    // Light source direction (top-left, slightly toward viewer)
    const lightDir = { x: -0.5, y: -0.6, z: 0.6 };
    const lightMag = Math.sqrt(lightDir.x ** 2 + lightDir.y ** 2 + lightDir.z ** 2);
    lightDir.x /= lightMag; lightDir.y /= lightMag; lightDir.z /= lightMag;

    const drawCell = (c: Cell) => {
      ctx.save();
      ctx.translate(c.x, c.y);

      const r = c.r * c.depth;
      const a = c.alpha;

      // 3D orientation
      const cosRx = Math.cos(c.rx), sinRx = Math.sin(c.rx);
      const cosRy = Math.cos(c.ry), sinRy = Math.sin(c.ry);

      // Normal vector of disc face (rotated from [0,0,1])
      const nx = sinRy;
      const ny = -sinRx * cosRy;
      const nz = cosRx * cosRy;

      // Diffuse lighting (how much the face catches light)
      const diffuse = Math.max(0, nx * lightDir.x + ny * lightDir.y + nz * lightDir.z);
      // Fresnel-like rim factor (brighter when edge-on)
      const faceDot = Math.abs(nz);
      const rimLight = Math.pow(1 - faceDot, 2.5) * 0.6;

      // Ellipse projection
      const scaleX = Math.max(0.12, Math.abs(cosRy) * 0.88 + 0.12);
      const scaleY = Math.max(0.12, Math.abs(cosRx) * 0.88 + 0.12);

      ctx.rotate(c.rz);
      ctx.scale(scaleX, scaleY);

      const edgeFactor = scaleX * scaleY;
      const effectiveAlpha = a * (0.35 + edgeFactor * 0.65);
      const litAlpha = effectiveAlpha * (0.6 + diffuse * 0.4);

      // Color palette
      const isRed = c.kind === 'red';
      const glowR = isRed ? 220 : 210, glowG = isRed ? 40 : 215, glowB = isRed ? 40 : 230;
      const rimR = isRed ? 240 : 235, rimG = isRed ? 70 : 240, rimB = isRed ? 55 : 250;
      const darkR = isRed ? 100 : 130, darkG = isRed ? 10 : 135, darkB = isRed ? 10 : 150;
      const midR = isRed ? 200 : 210, midG = isRed ? 45 : 215, midB = isRed ? 40 : 230;
      const strokeR = isRed ? 190 : 210, strokeG = isRed ? 35 : 220, strokeB = isRed ? 30 : 240;
      const hlR = isRed ? 255 : 255, hlG = isRed ? 180 : 250, hlB = isRed ? 170 : 255;

      // Drop shadow (offset in light direction)
      const shadowGrad = ctx.createRadialGradient(r * 0.15, r * 0.2, 0, r * 0.15, r * 0.2, r * 1.3);
      shadowGrad.addColorStop(0, `rgba(0, 0, 0, ${litAlpha * 0.25})`);
      shadowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.beginPath();
      ctx.arc(r * 0.15, r * 0.2, r * 1.3, 0, Math.PI * 2);
      ctx.fillStyle = shadowGrad;
      ctx.fill();

      // Ambient glow
      const glow = ctx.createRadialGradient(0, 0, r * 0.3, 0, 0, r * 1.8);
      glow.addColorStop(0, `rgba(${glowR}, ${glowG}, ${glowB}, ${litAlpha * 0.35})`);
      glow.addColorStop(1, `rgba(${glowR}, ${glowG}, ${glowB}, 0)`);
      ctx.beginPath();
      ctx.arc(0, 0, r * 1.8, 0, Math.PI * 2);
      ctx.fillStyle = glow;
      ctx.fill();

      // Main disc — torus gradient enhanced with lighting
      const brightBoost = 0.7 + diffuse * 0.3;
      const outerGrad = ctx.createRadialGradient(0, 0, r * 0.2, 0, 0, r * 1.05);
      outerGrad.addColorStop(0.0, `rgba(${darkR}, ${darkG}, ${darkB}, ${litAlpha * 0.1})`);
      outerGrad.addColorStop(0.25, `rgba(${midR}, ${midG}, ${midB}, ${litAlpha * 0.7 * brightBoost})`);
      outerGrad.addColorStop(0.5, `rgba(${rimR}, ${rimG}, ${rimB}, ${litAlpha * brightBoost})`);
      outerGrad.addColorStop(0.75, `rgba(${midR}, ${midG}, ${midB}, ${litAlpha * 0.8 * brightBoost})`);
      outerGrad.addColorStop(1.0, `rgba(${darkR}, ${darkG}, ${darkB}, ${litAlpha * 0.2})`);
      ctx.beginPath();
      ctx.arc(0, 0, r, 0, Math.PI * 2);
      ctx.fillStyle = outerGrad;
      ctx.fill();

      // Membrane outline — lit side brighter
      ctx.strokeStyle = `rgba(${strokeR}, ${strokeG}, ${strokeB}, ${litAlpha * (0.6 + diffuse * 0.4)})`;
      ctx.lineWidth = 2.5;
      ctx.stroke();

      // Rim lighting (subsurface-scatter-like glow on edges)
      if (rimLight > 0.05) {
        const rimGrad = ctx.createRadialGradient(0, 0, r * 0.85, 0, 0, r * 1.1);
        rimGrad.addColorStop(0, 'rgba(0,0,0,0)');
        rimGrad.addColorStop(0.5, `rgba(${rimR}, ${rimG}, ${rimB}, ${rimLight * litAlpha * 0.6})`);
        rimGrad.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.beginPath();
        ctx.arc(0, 0, r * 1.1, 0, Math.PI * 2);
        ctx.fillStyle = rimGrad;
        ctx.fill();
      }

      // Inner torus ring
      ctx.beginPath();
      ctx.arc(0, 0, r * 0.52, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${midR}, ${midG}, ${midB}, ${litAlpha * 0.4})`;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Central depression
      const centerGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, r * 0.4);
      centerGrad.addColorStop(0, `rgba(5, 8, 15, ${litAlpha * 0.75})`);
      centerGrad.addColorStop(0.5, `rgba(${darkR}, ${darkG}, ${darkB}, ${litAlpha * 0.25})`);
      centerGrad.addColorStop(1, `rgba(${midR}, ${midG}, ${midB}, 0)`);
      ctx.beginPath();
      ctx.arc(0, 0, r * 0.4, 0, Math.PI * 2);
      ctx.fillStyle = centerGrad;
      ctx.fill();

      // Primary specular highlight — shifts with rotation, stronger with diffuse light
      const hlOffX = -r * 0.28 + sinRy * r * 0.15;
      const hlOffY = -r * 0.22 + sinRx * r * 0.12;
      const specIntensity = Math.pow(diffuse, 1.5);
      ctx.beginPath();
      ctx.ellipse(hlOffX, hlOffY, r * 0.24, r * 0.13, -0.5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${hlR}, ${hlG}, ${hlB}, ${litAlpha * (0.25 + specIntensity * 0.45)})`;
      ctx.fill();

      // Hot specular pinpoint
      ctx.beginPath();
      ctx.ellipse(hlOffX + r * 0.06, hlOffY + r * 0.03, r * 0.09, r * 0.05, -0.3, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255, 255, 255, ${litAlpha * (0.15 + specIntensity * 0.35)})`;
      ctx.fill();

      // Subtle secondary reflection on lower-right (environment bounce)
      ctx.beginPath();
      ctx.ellipse(r * 0.2, r * 0.18, r * 0.12, r * 0.06, 0.4, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${hlR}, ${hlG}, ${hlB}, ${litAlpha * 0.08})`;
      ctx.fill();

      ctx.restore();
    };

    /* ── Vessel wall curves ── */
    const drawVesselWalls = () => {
      const waveOffset = time * 0.0003;

      // Top vessel wall
      ctx.beginPath();
      ctx.moveTo(-10, 0);
      for (let x = -10; x <= width + 10; x += 8) {
        const y = 30 + Math.sin(x * 0.003 + waveOffset) * 25 + Math.sin(x * 0.007 + waveOffset * 1.3) * 12;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(width + 10, -10);
      ctx.lineTo(-10, -10);
      ctx.closePath();
      const topGrad = ctx.createLinearGradient(0, 0, 0, 120);
      topGrad.addColorStop(0, 'rgba(140, 25, 25, 0.25)');
      topGrad.addColorStop(0.4, 'rgba(100, 15, 15, 0.10)');
      topGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = topGrad;
      ctx.fill();
      // Vessel membrane line
      ctx.beginPath();
      ctx.moveTo(-10, 0);
      for (let x = -10; x <= width + 10; x += 8) {
        const y = 30 + Math.sin(x * 0.003 + waveOffset) * 25 + Math.sin(x * 0.007 + waveOffset * 1.3) * 12;
        ctx.lineTo(x, y);
      }
      ctx.strokeStyle = 'rgba(180, 40, 40, 0.30)';
      ctx.lineWidth = 2.5;
      ctx.stroke();

      // Bottom vessel wall
      ctx.beginPath();
      ctx.moveTo(-10, height);
      for (let x = -10; x <= width + 10; x += 8) {
        const y = height - 30 - Math.sin(x * 0.0035 + waveOffset * 0.8) * 22 - Math.cos(x * 0.006 + waveOffset * 1.1) * 14;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(width + 10, height + 10);
      ctx.lineTo(-10, height + 10);
      ctx.closePath();
      const botGrad = ctx.createLinearGradient(0, height, 0, height - 120);
      botGrad.addColorStop(0, 'rgba(140, 25, 25, 0.22)');
      botGrad.addColorStop(0.4, 'rgba(100, 15, 15, 0.08)');
      botGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = botGrad;
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(-10, height);
      for (let x = -10; x <= width + 10; x += 8) {
        const y = height - 30 - Math.sin(x * 0.0035 + waveOffset * 0.8) * 22 - Math.cos(x * 0.006 + waveOffset * 1.1) * 14;
        ctx.lineTo(x, y);
      }
      ctx.strokeStyle = 'rgba(180, 40, 40, 0.28)';
      ctx.lineWidth = 2.5;
      ctx.stroke();
    };

    /* ── Flowing plasma streaks ── */
    const drawPlasmaStreaks = () => {
      const streakCount = 5;
      for (let i = 0; i < streakCount; i++) {
        const baseY = (height / (streakCount + 1)) * (i + 1);
        const offset = time * 0.0004 + i * 1.5;
        ctx.beginPath();
        ctx.moveTo(-10, baseY);
        for (let x = -10; x <= width + 10; x += 6) {
          const y = baseY + Math.sin(x * 0.002 + offset) * 40 + Math.cos(x * 0.005 + offset * 0.7) * 15;
          ctx.lineTo(x, y);
        }
        ctx.strokeStyle = `rgba(200, 60, 60, 0.04)`;
        ctx.lineWidth = 40;
        ctx.lineCap = 'round';
        ctx.stroke();
      }
    };

    /* ── Main animation loop ── */
    const animate = () => {
      ctx.clearRect(0, 0, width, height);
      time++;

      // Plasma flow streaks (deepest layer)
      drawPlasmaStreaks();

      // Vessel walls
      drawVesselWalls();

      // Resolve cell-to-cell collisions (bumps & spin transfers)
      resolveCollisions();

      // Blood cells — sporadic drift + occasional slow spins
      cells.forEach((c) => {
        // Sporadic movement — occasional small velocity jitters
        if (Math.random() < 0.008) {
          c.vy += (Math.random() - 0.5) * 0.15;
        }

        // Base rightward flow + gentle wobble
        c.x += c.vx + Math.sin(time * 0.002 + c.seed) * 0.08 + c.bumpVx;
        c.y += c.vy + Math.cos(time * 0.0015 + c.seed * 0.7) * 0.06 + c.bumpVy;

        // Dampen bump & drift velocities
        c.bumpVx *= 0.92;
        c.bumpVy *= 0.92;
        c.vy *= 0.998; // slowly recenter vertical drift

        // Apply rotation
        c.rx += c.rxV;
        c.ry += c.ryV;
        c.rz += c.rzV;

        // Heavy damping — spins die out quickly
        c.rxV *= 0.988;
        c.ryV *= 0.988;
        c.rzV *= 0.990;

        // Rare random spin event — ~1 in 500 frames per cell → slow gentle flip
        if (Math.random() < 0.002) {
          const axis = Math.floor(Math.random() * 3);
          const kick = (Math.random() - 0.5) * 0.012; // very slow spin
          if (axis === 0) c.rxV += kick;
          else if (axis === 1) c.ryV += kick;
          else c.rzV += kick;
        }

        // Wrap around edges
        if (c.x > width + c.r * 2) c.x = -c.r * 2;
        if (c.x < -c.r * 2) c.x = width + c.r * 2;
        if (c.y > height + c.r * 2) c.y = -c.r * 2;
        if (c.y < -c.r * 2) c.y = height + c.r * 2;

        drawCell(c);
      });

      requestAnimationFrame(animate);
    };

    const animId = requestAnimationFrame(animate);

    const handleResize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mouseX, mouseY]);

  const bgGradient = useMotionTemplate`radial-gradient(900px circle at ${mouseX}px ${mouseY}px, rgba(200, 50, 50, 0.04), transparent 40%)`;

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden bg-[#0A0D14]">
      {/* Layer 1: Deep vascular ambient — subtle warm/cool vignette */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_30%,rgba(10,13,20,0.9)_100%)]" />
        <div className="absolute top-0 left-0 w-full h-[200px] bg-gradient-to-b from-[rgba(120,20,20,0.06)] to-transparent" />
        <div className="absolute bottom-0 left-0 w-full h-[200px] bg-gradient-to-t from-[rgba(120,20,20,0.05)] to-transparent" />
      </div>

      {/* Layer 2: Blood vessel canvas — softened so it doesn't compete with text */}
      <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none opacity-60" style={{ filter: 'blur(1.5px)' }} />

      {/* Layer 3: Mouse-tracking warm glow (like a light through plasma) */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{ background: bgGradient }}
      />
    </div>
  );
};
