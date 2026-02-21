import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';

// Helper for Clinical Translation hover only
export const DoctorHoverHelper = ({ boxRef }: { boxRef: React.RefObject<HTMLDivElement> }) => {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  useEffect(() => {
    const box = boxRef?.current;
    if (!box) return;

    const onEnter = (e: Event) => {
      const target = e.target as HTMLElement;
      if (box.contains(target) && (target.tagName === 'P' || target.tagName === 'SPAN' || target.tagName === 'BUTTON' || target.closest('button'))) {
        // Find the closest card/block ancestor to position against
        const anchor = target.closest('button') || target.closest('[class*="rounded"]') || target;
        const boxRect = box.getBoundingClientRect();
        const anchorRect = anchor.getBoundingClientRect();
        setPos({
          // Offset so her hands (~75% down the 56px image = 42px) sit on the card's top edge
          top: anchorRect.top - boxRect.top - 42,
          // Position her at 5% from the left edge of the card
          left: anchorRect.left - boxRect.left + (anchorRect.width * 0.05) - 28,
        });
      }
    };

    const onLeave = () => {
      setPos(null);
    };

    box.addEventListener('mouseover', onEnter);
    box.addEventListener('mouseout', onLeave);
    return () => {
      box.removeEventListener('mouseover', onEnter);
      box.removeEventListener('mouseout', onLeave);
    };
  }, [boxRef]);

  return (
    <AnimatePresence>
      {pos && (
        <motion.img
          key="doctor-helper"
          src="/assets/doctor-hero-hover.png"
          alt=""
          initial={{ opacity: 0, scale: 0.8, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.8, y: 8 }}
          transition={{ type: 'spring', stiffness: 500, damping: 22, mass: 0.4 }}
          style={{
            position: 'absolute',
            top: pos.top,
            left: pos.left,
            width: 56,
            height: 56,
            zIndex: 99,
            pointerEvents: 'none',
            filter: 'drop-shadow(0 0 8px rgba(123,97,255,0.5)) drop-shadow(0 0 16px rgba(37,99,235,0.3))',
          }}
        />
      )}
    </AnimatePresence>
  );
};
