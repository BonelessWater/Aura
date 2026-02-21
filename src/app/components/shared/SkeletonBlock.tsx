import React from 'react';
import { cn } from '../ui/utils';

interface SkeletonBlockProps {
  className?: string;
  count?: number;
  gap?: string;
}

/** Shimmer skeleton that mirrors the final layout shape */
export const SkeletonBlock = ({ className, count = 1, gap = 'gap-4' }: SkeletonBlockProps) => {
  if (count > 1) {
    return (
      <div className={cn('flex flex-col', gap)}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={cn('skeleton-shimmer rounded-xl', className)} />
        ))}
      </div>
    );
  }
  return <div className={cn('skeleton-shimmer rounded-xl', className)} />;
};

/** A full card skeleton that matches the card-glass layout */
export const SkeletonCard = ({ className }: { className?: string }) => (
  <div className={cn('bg-[#13161F] border border-[#2A2E3B] rounded-2xl p-6 space-y-4', className)}>
    <div className="skeleton-shimmer rounded h-4 w-1/3" />
    <div className="skeleton-shimmer rounded h-3 w-full" />
    <div className="skeleton-shimmer rounded h-3 w-2/3" />
    <div className="skeleton-shimmer rounded h-3 w-4/5" />
  </div>
);

/** A list-row skeleton for document archive or feed items */
export const SkeletonRow = ({ className }: { className?: string }) => (
  <div className={cn('flex items-center gap-4 p-4 bg-[#13161F] border border-[#2A2E3B] rounded-lg', className)}>
    <div className="skeleton-shimmer rounded-lg w-10 h-10 flex-shrink-0" />
    <div className="flex-1 space-y-2">
      <div className="skeleton-shimmer rounded h-3 w-2/3" />
      <div className="skeleton-shimmer rounded h-2 w-1/3" />
    </div>
    <div className="skeleton-shimmer rounded h-8 w-20" />
  </div>
);
