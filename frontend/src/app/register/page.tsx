'use client';

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState } from "react";
import Link from "next/link";
import { Eye, EyeOff, Check } from "lucide-react";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    firstName: "",
    lastName: "",
    agreeToTerms: false
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.email) {
      newErrors.email = "Email is required";
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = "Please enter a valid email";
    }

    if (!formData.firstName) {
      newErrors.firstName = "First name is required";
    }

    if (!formData.lastName) {
      newErrors.lastName = "Last name is required";
    }

    if (!formData.password) {
      newErrors.password = "Password is required";
    } else if (formData.password.length < 8) {
      newErrors.password = "Password must be at least 8 characters";
    }

    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    if (!formData.agreeToTerms) {
      newErrors.agreeToTerms = "You must agree to the terms and conditions";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setIsLoading(true);

    try {
      const response = await api.register({
        email: formData.email,
        password: formData.password,
        first_name: formData.firstName,
        last_name: formData.lastName,
      });
      
      if (response.error) {
        setErrors({ general: response.error });
      } else {
        // Successful registration - redirect to dashboard
        window.location.href = "/dashboard";
      }
    } catch {
      setErrors({ general: "Registration failed. Please try again." });
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: "" }));
    }
  };

  const passwordStrength = () => {
    const password = formData.password;
    let strength = 0;
    
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    
    return strength;
  };

  const getStrengthColor = () => {
    const strength = passwordStrength();
    if (strength <= 2) return "bg-red-500";
    if (strength <= 3) return "bg-yellow-500";
    if (strength <= 4) return "bg-blue-500";
    return "bg-green-500";
  };

  const getStrengthText = () => {
    const strength = passwordStrength();
    if (strength <= 2) return "Weak";
    if (strength <= 3) return "Fair";
    if (strength <= 4) return "Good";
    return "Strong";
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
              <Link href="/login">Already have an account?</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h2 className="text-4xl font-bold mb-3">Create account</h2>
            <p className="text-neutral-400 text-lg">Join MedKIT and start converting</p>
          </div>

          <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800">
            <form onSubmit={handleSubmit} className="space-y-6">
              {errors.general && (
                <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400 text-center">
                  {errors.general}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName" className="text-white font-medium">
                    First name
                  </Label>
                  <Input
                    id="firstName"
                    type="text"
                    value={formData.firstName}
                    onChange={(e) => handleInputChange('firstName', e.target.value)}
                    placeholder="Enter first name"
                    className="h-12 bg-neutral-800 border-neutral-700 text-white placeholder-neutral-500 focus:border-white"
                  />
                  {errors.firstName && (
                    <p className="text-sm text-red-400">{errors.firstName}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="lastName" className="text-white font-medium">
                    Last name
                  </Label>
                  <Input
                    id="lastName"
                    type="text"
                    value={formData.lastName}
                    onChange={(e) => handleInputChange('lastName', e.target.value)}
                    placeholder="Enter last name"
                    className="h-12 bg-neutral-800 border-neutral-700 text-white placeholder-neutral-500 focus:border-white"
                  />
                  {errors.lastName && (
                    <p className="text-sm text-red-400">{errors.lastName}</p>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="text-white font-medium">
                  Email address
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  placeholder="Enter your email"
                  className="h-12 bg-neutral-800 border-neutral-700 text-white placeholder-neutral-500 focus:border-white"
                />
                {errors.email && (
                  <p className="text-sm text-red-400">{errors.email}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-white font-medium">
                  Password
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={formData.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
                    placeholder="Create a password"
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
                {formData.password && (
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-neutral-800 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${getStrengthColor()}`}
                          style={{ width: `${(passwordStrength() / 5) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm text-neutral-400">{getStrengthText()}</span>
                    </div>
                  </div>
                )}
                {errors.password && (
                  <p className="text-sm text-red-400">{errors.password}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-white font-medium">
                  Confirm password
                </Label>
                <div className="relative">
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    value={formData.confirmPassword}
                    onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                    placeholder="Confirm your password"
                    className="h-12 bg-neutral-800 border-neutral-700 text-white placeholder-neutral-500 focus:border-white pr-12"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 text-neutral-400 hover:text-white"
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
                {errors.confirmPassword && (
                  <p className="text-sm text-red-400">{errors.confirmPassword}</p>
                )}
              </div>

              <div className="space-y-2">
                <label className="flex items-start space-x-3 text-sm cursor-pointer">
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={formData.agreeToTerms}
                      onChange={(e) => handleInputChange('agreeToTerms', e.target.checked)}
                      className="sr-only"
                    />
                    <div className={`w-5 h-5 border-2 rounded flex items-center justify-center ${
                      formData.agreeToTerms 
                        ? 'bg-white border-white' 
                        : 'border-neutral-600 bg-neutral-800'
                    }`}>
                      {formData.agreeToTerms && <Check className="h-3 w-3 text-black" />}
                    </div>
                  </div>
                  <span className="text-neutral-400 leading-relaxed">
                    I agree to the{" "}
                    <Link href="/terms" className="text-white hover:underline cursor-pointer">
                      Terms of Service
                    </Link>{" "}
                    and{" "}
                    <Link href="/privacy" className="text-white hover:underline cursor-pointer">
                      Privacy Policy
                    </Link>
                  </span>
                </label>
                {errors.agreeToTerms && (
                  <p className="text-sm text-red-400">{errors.agreeToTerms}</p>
                )}
              </div>

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-12 bg-white text-black hover:bg-neutral-200 text-lg font-medium"
              >
                {isLoading ? "Creating account..." : "Create account"}
              </Button>
            </form>

            <div className="mt-8 pt-8 border-t border-neutral-800 text-center">
              <p className="text-neutral-400">
                Already have an account?{" "}
                <Link href="/login" className="text-white hover:underline font-medium">
                  Sign in here
                </Link>
              </p>
            </div>
          </div>

          <div className="mt-8 text-center">
            <p className="text-sm text-neutral-500">
              By creating an account, you agree to our{" "}
              <Link href="/terms" className="text-neutral-400 hover:text-white">
                Terms of Service
              </Link>{" "}
              and{" "}
              <Link href="/privacy" className="text-neutral-400 hover:text-white">
                Privacy Policy
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
