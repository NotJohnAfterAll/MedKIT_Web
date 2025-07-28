'use client';

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState, useEffect } from "react";
import Link from "next/link";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated } = useAuth();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const result = await login(email, password);
      
      if (!result.success) {
        setError(result.error || "Login failed. Please try again.");
      } else {
        // Successful login - redirect to dashboard
        router.push("/dashboard");
      }
    } catch {
      setError("Login failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {/* Header */}
      <header className="border-b border-neutral-800 bg-black">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-3 cursor-pointer">
              <svg width="32" height="32" viewBox="0 0 2048 2048" xmlns="http://www.w3.org/2000/svg" style={{color: 'white'}}>
                <g transform="matrix(2,0,0,2,0,0)">
                  <g transform="matrix(1,0,0,1,-69.5,23.5)">
                    <circle cx="581.5" cy="488.5" r="427.5" fill="none" stroke="#ffffff" strokeWidth="6.64" strokeLinecap="round" strokeLinejoin="round"/>
                  </g>
                  <g transform="matrix(0.95614,0,0,0.821365,-44.4737,59.1986)">
                    <path d="M582,292L810,748L354,748L582,292Z" fill="#ffffff"/>
                  </g>
                </g>
              </svg>
              <h1 className="text-2xl font-bold">MedKIT</h1>
            </Link>
            <Button variant="ghost" className="text-neutral-400 hover:text-white" asChild>
              <Link href="/register">Need an account?</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h2 className="text-4xl font-bold mb-3">Welcome back</h2>
            <p className="text-neutral-400 text-lg">Sign in to your MedKIT account</p>
          </div>

          <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800">
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400 text-center">
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="email" className="text-white font-medium">
                  Email address
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  required
                  className="h-12 bg-neutral-800 border-neutral-700 text-white placeholder-neutral-500 focus:border-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-white font-medium">
                  Password
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    required
                    className="h-12 bg-neutral-800 border-neutral-700 text-white placeholder-neutral-500 focus:border-white pr-12"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 text-neutral-400 hover:text-white"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center space-x-2 text-sm">
                  <input
                    type="checkbox"
                    className="rounded border-neutral-700 bg-neutral-800 text-white focus:ring-white"
                  />
                  <span className="text-neutral-400">Remember me</span>
                </label>
                <Link
                  href="/forgot-password"
                  className="text-sm text-neutral-400 hover:text-white transition-colors"
                >
                  Forgot password?
                </Link>
              </div>

              <Button
                type="submit"
                disabled={isLoading || !email || !password}
                className="w-full h-12 bg-white text-black hover:bg-neutral-200 text-lg font-medium"
              >
                {isLoading ? "Signing in..." : "Sign in"}
              </Button>
            </form>

            <div className="mt-8 pt-8 border-t border-neutral-800 text-center">
              <p className="text-neutral-400">
                Don&apos;t have an account?{" "}
                <Link href="/register" className="text-white hover:underline font-medium cursor-pointer">
                  Sign up for free
                </Link>
              </p>
            </div>
          </div>

          <div className="mt-8 text-center">
            <p className="text-sm text-neutral-500">
              By signing in, you agree to our{" "}
              <Link href="/terms" className="text-neutral-400 hover:text-white cursor-pointer">
                Terms of Service
              </Link>{" "}
              and{" "}
              <Link href="/privacy" className="text-neutral-400 hover:text-white cursor-pointer">
                Privacy Policy
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
