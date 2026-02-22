import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useNavigate } from 'react-router';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { useBackgroundTitle } from '../context/BackgroundContext';

export const Login = () => {
  const [isSignup, setIsSignup] = useState(false);
  const navigate = useNavigate();
  const { setShowTitle } = useBackgroundTitle();

  useEffect(() => {
    setShowTitle(false);
    return () => setShowTitle(true);
  }, [setShowTitle]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSignup) {
      // New users go through the intake questionnaire
      navigate('/', { state: { startIntake: true } });
    } else {
      // Returning users go straight to the dashboard
      navigate('/', { state: { showDashboard: true } });
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="card-glass p-8 space-y-6">
          {/* Logo */}
          <div className="text-center space-y-2">
            <h1
              className="font-display text-4xl font-bold tracking-[0.08em] text-white/90"
              style={{
                textShadow:
                  '0 0 30px rgba(140, 7, 22, 0.6), 0 0 60px rgba(140, 7, 22, 0.3)',
              }}
            >
              A<span className="text-white/70">u</span>RA
            </h1>
            <p className="text-sm text-white/40">
              {isSignup ? 'Create an account to get started' : 'Sign in to continue'}
            </p>
          </div>

          <AnimatePresence mode="wait">
            <motion.form
              key={isSignup ? 'signup' : 'login'}
              initial={{ opacity: 0, x: isSignup ? 20 : -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: isSignup ? -20 : 20 }}
              transition={{ duration: 0.25 }}
              onSubmit={handleSubmit}
              className="space-y-5"
            >
              {isSignup && (
                <div className="space-y-1.5">
                  <Label className="text-white/60 text-xs">Full Name</Label>
                  <Input
                    type="text"
                    placeholder="Jane Doe"
                    required
                    className="bg-white/[0.04] border-white/10 text-white placeholder:text-white/25 focus-visible:border-[#8c0716]/60 focus-visible:ring-[#8c0716]/20 h-11"
                  />
                </div>
              )}

              <div className="space-y-1.5">
                <Label className="text-white/60 text-xs">Email</Label>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  required
                  className="bg-white/[0.04] border-white/10 text-white placeholder:text-white/25 focus-visible:border-[#8c0716]/60 focus-visible:ring-[#8c0716]/20 h-11"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label className="text-white/60 text-xs">Password</Label>
                  {!isSignup && (
                    <button type="button" className="text-xs text-white/30 hover:text-white/50 transition-colors">
                      Forgot password?
                    </button>
                  )}
                </div>
                <Input
                  type="password"
                  placeholder="••••••••"
                  required
                  className="bg-white/[0.04] border-white/10 text-white placeholder:text-white/25 focus-visible:border-[#8c0716]/60 focus-visible:ring-[#8c0716]/20 h-11"
                />
              </div>

              {isSignup && (
                <div className="space-y-1.5">
                  <Label className="text-white/60 text-xs">Confirm Password</Label>
                  <Input
                    type="password"
                    placeholder="••••••••"
                    required
                    className="bg-white/[0.04] border-white/10 text-white placeholder:text-white/25 focus-visible:border-[#8c0716]/60 focus-visible:ring-[#8c0716]/20 h-11"
                  />
                </div>
              )}

              <Button
                type="submit"
                className="w-full h-12 bg-[#8c0716] hover:bg-[#a8091c] text-white font-medium text-base shadow-[0_0_20px_rgba(140,7,22,0.4)] hover:shadow-[0_0_30px_rgba(140,7,22,0.6)] transition-all"
              >
                {isSignup ? 'Create Account' : 'Sign In'}
              </Button>
            </motion.form>
          </AnimatePresence>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/[0.06]" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-3 text-white/25" style={{ backgroundColor: 'rgba(10, 13, 20, 0.6)' }}>or</span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setIsSignup(!isSignup)}
            className="w-full text-center text-sm text-white/40 hover:text-white/70 transition-colors py-1"
          >
            {isSignup ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
          </button>
        </div>
      </motion.div>
    </div>
  );
};
