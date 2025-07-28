/**
 * Smart Progress Hook - Handles progress smoothing and anti-backwards protection
 * This moves all the complex progress logic to the frontend where it belongs!
 */
import { useState, useRef, useCallback } from 'react';

export const useSmartProgress = () => {
  const [displayProgress, setDisplayProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState('idle');
  
  // Keep track of the highest progress seen and smoothing state
  const maxProgressRef = useRef(0);
  const lastUpdateTimeRef = useRef(Date.now());
  const smoothingIntervalRef = useRef(null);
  
  const updateProgress = useCallback((rawProgress, rawMessage = '', rawStatus = 'downloading') => {
    const now = Date.now();
    
    // Anti-backwards protection: Only allow progress to go forward
    const actualProgress = Math.max(rawProgress, maxProgressRef.current);
    maxProgressRef.current = actualProgress;
    
    // Update message and status immediately
    setMessage(rawMessage);
    setStatus(rawStatus);
    
    // Smooth progress animation
    const startProgress = displayProgress;
    const targetProgress = actualProgress;
    const progressDiff = targetProgress - startProgress;
    
    if (progressDiff <= 0) {
      // No change needed or backwards movement blocked
      return;
    }
    
    // Clear any existing smoothing
    if (smoothingIntervalRef.current) {
      clearInterval(smoothingIntervalRef.current);
    }
    
    // Animate progress smoothly over 200ms
    const animationDuration = 200;
    const steps = 10;
    const stepSize = progressDiff / steps;
    const stepDuration = animationDuration / steps;
    
    let currentStep = 0;
    
    smoothingIntervalRef.current = setInterval(() => {
      currentStep++;
      
      if (currentStep >= steps) {
        // Final step - ensure we hit exact target
        setDisplayProgress(targetProgress);
        clearInterval(smoothingIntervalRef.current);
        smoothingIntervalRef.current = null;
      } else {
        // Intermediate step - smooth animation
        const newProgress = startProgress + (stepSize * currentStep);
        setDisplayProgress(Math.round(newProgress));
      }
    }, stepDuration);
    
    lastUpdateTimeRef.current = now;
  }, [displayProgress]);
  
  const reset = useCallback(() => {
    setDisplayProgress(0);
    setMessage('');
    setStatus('idle');
    maxProgressRef.current = 0;
    
    if (smoothingIntervalRef.current) {
      clearInterval(smoothingIntervalRef.current);
      smoothingIntervalRef.current = null;
    }
  }, []);
  
  const handleComplete = useCallback(() => {
    // Smooth transition to 100%
    updateProgress(100, 'Complete!', 'completed');
  }, [updateProgress]);
  
  const handleError = useCallback((errorMessage) => {
    setMessage(errorMessage || 'Error occurred');
    setStatus('error');
    
    if (smoothingIntervalRef.current) {
      clearInterval(smoothingIntervalRef.current);
      smoothingIntervalRef.current = null;
    }
  }, []);
  
  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      if (smoothingIntervalRef.current) {
        clearInterval(smoothingIntervalRef.current);
      }
    };
  }, []);
  
  return {
    progress: displayProgress,
    message,
    status,
    updateProgress,
    reset,
    handleComplete,
    handleError
  };
};

export default useSmartProgress;
