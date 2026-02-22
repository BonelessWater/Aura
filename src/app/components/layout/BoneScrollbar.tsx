import React, { useEffect, useState, useCallback, useRef } from 'react';

/**
 * BoneScrollbar — a custom page scrollbar where the thumb is a bone 🦴
 * Renders as a fixed overlay on the right edge of the viewport.
 */
export const BoneScrollbar = () => {
    const [scrollPercent, setScrollPercent] = useState(0);
    const [thumbHeight, setThumbHeight] = useState(80);
    const [isScrollable, setIsScrollable] = useState(false);
    const [isHovered, setIsHovered] = useState(false);
    const [isDragging, setIsDragging] = useState(false);
    const trackRef = useRef<HTMLDivElement>(null);
    const dragStartY = useRef(0);
    const dragStartScroll = useRef(0);

    const TRACK_PADDING = 8;

    const updateScroll = useCallback(() => {
        const scrollTop = window.scrollY;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;

        setIsScrollable(docHeight > 10);

        if (docHeight <= 0) {
            setScrollPercent(0);
            return;
        }
        setScrollPercent(scrollTop / docHeight);

        const viewRatio = window.innerHeight / document.documentElement.scrollHeight;
        setThumbHeight(Math.max(60, viewRatio * (window.innerHeight - TRACK_PADDING * 2)));
    }, []);

    useEffect(() => {
        // Initial check + delayed check (content might load async)
        updateScroll();
        const timer = setTimeout(updateScroll, 500);
        const timer2 = setTimeout(updateScroll, 1500);

        window.addEventListener('scroll', updateScroll, { passive: true });
        window.addEventListener('resize', updateScroll, { passive: true });

        // Also observe DOM changes (content loading)
        const observer = new MutationObserver(updateScroll);
        observer.observe(document.body, { childList: true, subtree: true });

        return () => {
            clearTimeout(timer);
            clearTimeout(timer2);
            window.removeEventListener('scroll', updateScroll);
            window.removeEventListener('resize', updateScroll);
            observer.disconnect();
        };
    }, [updateScroll]);

    // Drag handling
    const onMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
        dragStartY.current = e.clientY;
        dragStartScroll.current = window.scrollY;
    }, []);

    useEffect(() => {
        if (!isDragging) return;
        const onMouseMove = (e: MouseEvent) => {
            const trackHeight = (trackRef.current?.clientHeight ?? window.innerHeight) - TRACK_PADDING * 2 - thumbHeight;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            if (trackHeight <= 0 || docHeight <= 0) return;
            const dy = e.clientY - dragStartY.current;
            const scrollDelta = (dy / trackHeight) * docHeight;
            window.scrollTo(0, dragStartScroll.current + scrollDelta);
        };
        const onMouseUp = () => setIsDragging(false);
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
        return () => {
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        };
    }, [isDragging, thumbHeight]);

    // Click on track to jump
    const onTrackClick = useCallback((e: React.MouseEvent) => {
        if (!trackRef.current) return;
        const rect = trackRef.current.getBoundingClientRect();
        const clickY = e.clientY - rect.top - TRACK_PADDING;
        const trackUsable = rect.height - TRACK_PADDING * 2 - thumbHeight;
        if (trackUsable <= 0) return;
        const percent = Math.max(0, Math.min(1, clickY / trackUsable));
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        window.scrollTo({ top: percent * docHeight, behavior: 'smooth' });
    }, [thumbHeight]);

    if (!isScrollable) return null;

    const viewHeight = window.innerHeight;
    const trackUsable = viewHeight - TRACK_PADDING * 2 - thumbHeight;
    const thumbTop = TRACK_PADDING + scrollPercent * trackUsable;
    const glow = isHovered || isDragging;

    return (
        <div
            ref={trackRef}
            onClick={onTrackClick}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            className="fixed top-0 right-0 z-[9999] h-screen"
            style={{ width: 28, cursor: 'pointer' }}
        >
            {/* Track groove */}
            <div
                className="absolute top-2 bottom-2 right-[10px] rounded-full"
                style={{ width: 4, background: 'rgba(255,255,255,0.04)' }}
            />

            {/* Bone thumb */}
            <div
                onMouseDown={onMouseDown}
                style={{
                    position: 'absolute',
                    top: thumbTop,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    width: 22,
                    height: thumbHeight,
                    cursor: isDragging ? 'grabbing' : 'grab',
                    filter: glow
                        ? 'drop-shadow(0 0 8px rgba(245, 235, 220, 0.6))'
                        : 'drop-shadow(0 0 3px rgba(245, 235, 220, 0.25))',
                    transition: 'filter 0.2s ease',
                }}
            >
                <svg
                    viewBox="0 0 22 80"
                    width="22"
                    height={thumbHeight}
                    preserveAspectRatio="none"
                    xmlns="http://www.w3.org/2000/svg"
                >
                    <defs>
                        <linearGradient id="boneGrad" x1="0" y1="0" x2="1" y2="0">
                            <stop offset="0%" stopColor="#d4c8aa" />
                            <stop offset="25%" stopColor="#e8dcc8" />
                            <stop offset="50%" stopColor="#f5efe4" />
                            <stop offset="75%" stopColor="#e8dcc8" />
                            <stop offset="100%" stopColor="#cfc2a8" />
                        </linearGradient>
                        <linearGradient id="boneHighlight" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="rgba(255,255,255,0.6)" />
                            <stop offset="30%" stopColor="rgba(255,255,255,0)" />
                            <stop offset="70%" stopColor="rgba(255,255,255,0)" />
                            <stop offset="100%" stopColor="rgba(255,255,255,0.3)" />
                        </linearGradient>
                    </defs>

                    {/* Bone shape: wide knobs top & bottom, narrow shaft center */}
                    <path
                        d={`
              M 5,8
              C 1,6  0,3  3,1
              C 5,-0.5  8,0  9,2
              L 11,2
              C 12.5,-0.5  15.5,-0.5  17.5,1
              C 20.5,3.5  19,7  15,8
              L 14,12
              C 13,14  13,16  13,20
              L 13,60
              C 13,64  13,66  14,68
              L 15,72
              C 19,73  20.5,76.5  17.5,79
              C 15.5,80.5  12.5,80.5  11,78
              L 9,78
              C 8,80  5,80.5  3,79
              C 0,77  1,74  5,72
              L 8,68
              C 9,66  9,64  9,60
              L 9,20
              C 9,16  9,14  8,12
              Z
            `}
                        fill="url(#boneGrad)"
                        stroke="#b8a88a"
                        strokeWidth="0.5"
                    />

                    {/* 3D depth highlight */}
                    <path
                        d={`
              M 5,8
              C 1,6  0,3  3,1
              C 5,-0.5  8,0  9,2
              L 11,2
              C 12.5,-0.5  15.5,-0.5  17.5,1
              C 20.5,3.5  19,7  15,8
              L 14,12
              C 13,14  13,16  13,20
              L 13,60
              C 13,64  13,66  14,68
              L 15,72
              C 19,73  20.5,76.5  17.5,79
              C 15.5,80.5  12.5,80.5  11,78
              L 9,78
              C 8,80  5,80.5  3,79
              C 0,77  1,74  5,72
              L 8,68
              C 9,66  9,64  9,60
              L 9,20
              C 9,16  9,14  8,12
              Z
            `}
                        fill="url(#boneHighlight)"
                    />
                </svg>
            </div>
        </div>
    );
};
