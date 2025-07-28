'use client';

import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { 
  Download, 
  RefreshCw, 
  User, 
  Settings, 
  Crown, 
  Calendar,
  FileText,
  Activity,
  LogOut
} from "lucide-react";
import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Link from "next/link";

interface UserStats {
  downloadsToday: number;
  downloadsTotal: number;
  conversionsToday: number;
  conversionsTotal: number;
  storageUsed: number;
  storageLimit: number;
}

interface RecentActivity {
  id: number;
  type: 'download' | 'conversion';
  title: string;
  status: 'completed' | 'processing' | 'failed';
  timestamp: string;
  size?: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user: authUser, isAuthenticated, logout, isLoading: authLoading } = useAuth();
  
  const [stats, setStats] = useState<UserStats>({
    downloadsToday: 0,
    downloadsTotal: 0,
    conversionsToday: 0,
    conversionsTotal: 0,
    storageUsed: 0,
    storageLimit: 0
  });

  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      if (!authUser) return;
      
      try {
        setIsLoading(true);
        
        // Fetch recent downloads and conversions
        const [downloadsResponse, conversionsResponse] = await Promise.all([
          api.getRecentDownloads(3),
          api.getRecentConversions(3)
        ]);

        // Combine and format recent activity
        const activities: RecentActivity[] = [];
        
        if (downloadsResponse.data) {
          downloadsResponse.data.forEach((download, index) => {
            activities.push({
              id: index + 1,
              type: 'download',
              title: download.title || download.url,
              status: download.status as 'completed' | 'processing' | 'failed',
              timestamp: formatTimestamp(download.created_at),
              size: download.file_size ? download.file_size / (1024 * 1024) : undefined
            });
          });
        }

        if (conversionsResponse.data) {
          conversionsResponse.data.forEach((conversion, index) => {
            activities.push({
              id: activities.length + index + 1,
              type: 'conversion',
              title: `${conversion.filename} → ${conversion.output_format}`,
              status: conversion.status as 'completed' | 'processing' | 'failed',
              timestamp: formatTimestamp(conversion.created_at),
              size: conversion.file_size / (1024 * 1024)
            });
          });
        }

        // Sort by timestamp (most recent first)
        activities.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        setRecentActivity(activities.slice(0, 4));

        // Set basic stats (you can enhance this by getting real stats from API)
        setStats({
          downloadsToday: 0, // Will be updated from actual API
          downloadsTotal: downloadsResponse.data?.length || 0,
          conversionsToday: 0, // Will be updated from actual API
          conversionsTotal: conversionsResponse.data?.length || 0,
          storageUsed: 0, // TODO: Calculate from actual usage
          storageLimit: authUser?.is_premium ? 100 : 10 // GB
        });

      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, [authUser]);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) {
      return 'Just now';
    } else if (diffInHours < 24) {
      return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    } else {
      const diffInDays = Math.floor(diffInHours / 24);
      return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      router.push("/");
    } catch (error) {
      console.error('Logout failed:', error);
      // Even if logout fails, redirect
      router.push("/");
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-400';
      case 'processing': return 'text-blue-400';
      case 'failed': return 'text-red-400';
      default: return 'text-neutral-400';
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-900/20';
      case 'processing': return 'bg-blue-900/20';
      case 'failed': return 'bg-red-900/20';
      default: return 'bg-neutral-900/20';
    }
  };

  // Show loading or redirect if not authenticated
  if (authLoading || !authUser) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4" />
          <p className="text-neutral-300">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="text-center">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4" />
            <p className="text-neutral-300">Loading dashboard data...</p>
          </div>
        </div>
      )}
      
      {/* Header */}
      <header className="border-b border-neutral-800 bg-black sticky top-0 z-40">{
        }
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-3">
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
            <div className="flex items-center space-x-4">
              <Button className="bg-white text-black hover:bg-neutral-200" asChild>
                <Link href="/">New Download</Link>
              </Button>
              <Button
                variant="ghost"
                onClick={handleLogout}
                className="text-neutral-400 hover:text-white"
              >
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8 max-w-7xl">
        {/* Welcome Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-4xl font-bold mb-2">
                Welcome back, {authUser?.first_name}!
              </h2>
              <p className="text-neutral-400 text-lg">
                Here&apos;s what&apos;s happening with your account
              </p>
            </div>
            {!authUser?.is_premium && (
              <Button className="bg-gradient-to-r from-yellow-600 to-yellow-500 text-black hover:from-yellow-500 hover:to-yellow-400">
                <Crown className="h-4 w-4 mr-2" />
                Upgrade to Premium
              </Button>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="bg-neutral-900 rounded-2xl p-6 border border-neutral-800">
            <div className="flex items-center justify-between mb-4">
              <Download className="h-8 w-8 text-blue-400" />
              <span className="text-sm text-neutral-400">Today</span>
            </div>
            <div className="space-y-2">
              <p className="text-3xl font-bold">{stats.downloadsToday}</p>
              <p className="text-neutral-400">Downloads</p>
              <p className="text-sm text-neutral-500">
                {stats.downloadsTotal} total
              </p>
            </div>
          </div>

          <div className="bg-neutral-900 rounded-2xl p-6 border border-neutral-800">
            <div className="flex items-center justify-between mb-4">
              <RefreshCw className="h-8 w-8 text-green-400" />
              <span className="text-sm text-neutral-400">Today</span>
            </div>
            <div className="space-y-2">
              <p className="text-3xl font-bold">{stats.conversionsToday}</p>
              <p className="text-neutral-400">Conversions</p>
              <p className="text-sm text-neutral-500">
                {stats.conversionsTotal} total
              </p>
            </div>
          </div>

          <div className="bg-neutral-900 rounded-2xl p-6 border border-neutral-800">
            <div className="flex items-center justify-between mb-4">
              <FileText className="h-8 w-8 text-purple-400" />
              <span className="text-sm text-neutral-400">Storage</span>
            </div>
            <div className="space-y-2">
              <p className="text-3xl font-bold">{stats.storageUsed}GB</p>
              <p className="text-neutral-400">Used</p>
              <div className="space-y-2">
                <Progress 
                  value={(stats.storageUsed / stats.storageLimit) * 100} 
                  className="h-2"
                />
                <p className="text-sm text-neutral-500">
                  {stats.storageLimit}GB limit
                </p>
              </div>
            </div>
          </div>

          <div className="bg-neutral-900 rounded-2xl p-6 border border-neutral-800">
            <div className="flex items-center justify-between mb-4">
              <Calendar className="h-8 w-8 text-orange-400" />
              <span className="text-sm text-neutral-400">Member</span>
            </div>
            <div className="space-y-2">
              <p className="text-xl font-bold">
                {authUser?.is_premium ? 'Premium' : 'Free'}
              </p>
              <p className="text-neutral-400">Account</p>
              <p className="text-sm text-neutral-500">
                Since {new Date(authUser?.date_joined || '').toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="activity" className="w-full">
          <TabsList className="grid w-full grid-cols-3 bg-neutral-900 p-1 rounded-xl border border-neutral-800">
            <TabsTrigger 
              value="activity" 
              className="data-[state=active]:bg-white data-[state=active]:text-black text-neutral-400"
            >
              <Activity className="h-4 w-4 mr-2" />
              Recent Activity
            </TabsTrigger>
            <TabsTrigger 
              value="profile" 
              className="data-[state=active]:bg-white data-[state=active]:text-black text-neutral-400"
            >
              <User className="h-4 w-4 mr-2" />
              Profile
            </TabsTrigger>
            <TabsTrigger 
              value="settings" 
              className="data-[state=active]:bg-white data-[state=active]:text-black text-neutral-400"
            >
              <Settings className="h-4 w-4 mr-2" />
              Settings
            </TabsTrigger>
          </TabsList>

          <TabsContent value="activity" className="mt-6">
            <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800">
              <h3 className="text-2xl font-bold mb-6">Recent Activity</h3>
              <div className="space-y-4">
                {recentActivity.length === 0 ? (
                  <div className="text-center py-12">
                    <Activity className="h-12 w-12 text-neutral-600 mx-auto mb-4" />
                    <p className="text-neutral-400 text-lg">No recent activity</p>
                    <p className="text-neutral-500 text-sm mt-2">
                      Start downloading or converting files to see your activity here
                    </p>
                  </div>
                ) : (
                  recentActivity.map((activity) => (
                    <div key={activity.id} className="bg-neutral-800 rounded-xl p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-4">
                          <div className={`p-3 rounded-lg ${getStatusBg(activity.status)}`}>
                            {activity.type === 'download' ? (
                              <Download className="h-5 w-5 text-blue-400" />
                            ) : (
                              <RefreshCw className="h-5 w-5 text-green-400" />
                            )}
                          </div>
                          <div className="flex-1">
                            <h4 className="font-semibold text-white mb-1">
                              {activity.title}
                            </h4>
                            <div className="flex items-center space-x-4 text-sm text-neutral-400">
                              <span className={getStatusColor(activity.status)}>
                                {activity.status.charAt(0).toUpperCase() + activity.status.slice(1)}
                              </span>
                              <span>{activity.timestamp}</span>
                              {activity.size && (
                                <span>{activity.size.toFixed(1)} MB</span>
                              )}
                            </div>
                          </div>
                        </div>
                        {activity.status === 'completed' && (
                          <Button variant="ghost" size="sm" className="text-neutral-400 hover:text-white">
                            Download
                          </Button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="profile" className="mt-6">
            <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800">
              <h3 className="text-2xl font-bold mb-6">Profile Information</h3>
              <div className="space-y-6">
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-neutral-400 mb-2">
                      First Name
                    </label>
                    <p className="text-white text-lg">{authUser?.first_name}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-400 mb-2">
                      Last Name
                    </label>
                    <p className="text-white text-lg">{authUser?.last_name}</p>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-400 mb-2">
                    Email Address
                  </label>
                  <p className="text-white text-lg">{authUser?.email}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-400 mb-2">
                    Account Type
                  </label>
                  <div className="flex items-center space-x-3">
                    <span className="text-white text-lg">
                      {authUser?.is_premium ? 'Premium' : 'Free'}
                    </span>
                    {authUser?.is_premium && <Crown className="h-5 w-5 text-yellow-500" />}
                  </div>
                </div>
                <div className="pt-4">
                  <Button className="bg-white text-black hover:bg-neutral-200">
                    Edit Profile
                  </Button>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="settings" className="mt-6">
            <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800">
              <h3 className="text-2xl font-bold mb-6">Account Settings</h3>
              <div className="space-y-8">
                <div>
                  <h4 className="text-lg font-semibold text-white mb-4">Preferences</h4>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-white font-medium">Email Notifications</p>
                        <p className="text-sm text-neutral-400">
                          Receive emails about your downloads and conversions
                        </p>
                      </div>
                      <input type="checkbox" defaultChecked className="rounded" />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-white font-medium">Auto-delete Files</p>
                        <p className="text-sm text-neutral-400">
                          Automatically delete files after 7 days
                        </p>
                      </div>
                      <input type="checkbox" defaultChecked className="rounded" />
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-lg font-semibold text-white mb-4">Security</h4>
                  <div className="space-y-4">
                    <Button variant="outline" className="border-neutral-700 text-white hover:bg-neutral-800">
                      Change Password
                    </Button>
                    <Button variant="outline" className="border-neutral-700 text-white hover:bg-neutral-800">
                      Two-Factor Authentication
                    </Button>
                  </div>
                </div>

                <div>
                  <h4 className="text-lg font-semibold text-red-400 mb-4">Danger Zone</h4>
                  <Button variant="outline" className="border-red-800 text-red-400 hover:bg-red-900/20">
                    Delete Account
                  </Button>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
