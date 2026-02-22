import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';

// Helper for Clinical Translation hover only
export const DoctorHoverHelper = ({ boxRef }: { boxRef: React.RefObject<HTMLDivElement> }) => {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const box = boxRef.current;
    if (!box) return;
    // Only trigger on hover of text inside the box
    const onEnter = (e: Event) => {
      const target = e.target as HTMLElement;
      if (box.contains(target) && (target.tagName === 'P' || target.tagName === 'SPAN')) {
        setShow(true);
      }
    };
    const onLeave = (e: Event) => {
      setShow(false);
    };
    box.addEventListener('mouseover', onEnter);
    box.addEventListener('mouseout', onLeave);
    return () => {
      box.removeEventListener('mouseover', onEnter);
      box.removeEventListener('mouseout', onLeave);
    };
  }, [boxRef]);

  // Position: absolute top left of the box
  return (
    <AnimatePresence>
      {show && (
        <motion.img
          key="doctor-helper"
          src="/assets/doctor-hero-hover.png"
          alt=""
          initial={{ opacity: 0, scale: 0.7, y: -10 }}
          animate={{ opacity: 1, scale: 1.25, y: 0 }}
          exit={{ opacity: 0, scale: 0.7, y: -10 }}
          transition={{ type: 'spring', stiffness: 420, damping: 18, mass: 0.5 }}
          style={{
            position: 'absolute',
            top: '-32px',
            left: '-32px',
            width: 96,
            height: 96,
            zIndex: 99,
            pointerEvents: 'none',
            filter: 'drop-shadow(0 0 16px #7B61FF) drop-shadow(0 0 32px #3ECFCF)',
          }}
        />
      )}
    </AnimatePresence>
  );
};
