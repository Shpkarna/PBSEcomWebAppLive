import { useEffect, useRef, useCallback } from 'react';

const INACTIVITY_MS = 2 * 60 * 1000; // 2 minutes
const EVENTS = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];

export function useInactivityTimer(onTimeout: () => void, isActive: boolean): void {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const resetTimer = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (isActive) {
      timerRef.current = setTimeout(onTimeout, INACTIVITY_MS);
    }
  }, [onTimeout, isActive]);

  useEffect(() => {
    EVENTS.forEach(evt => document.addEventListener(evt, resetTimer, true));
    resetTimer();
    return () => {
      EVENTS.forEach(evt => document.removeEventListener(evt, resetTimer, true));
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [resetTimer]);
}
