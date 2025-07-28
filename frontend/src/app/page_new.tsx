'use client';

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Download, RefreshCw, Upload, Play, Pause, X } from "lucide-react";
import { useState } from "react";
import Link from "next/link";

interface DownloadItem {
  id: number;
  url: string;
  title: string;
  status: string;
  progress: number;
  format: string;
  quality: string;
}

interface ConversionItem {
  id: number;
  filename: string;
  status: string;
  progress: number;
  inputFormat: string;
  outputFormat: string;
  size: number;
}

export default function HomePage() {
  const [downloadUrl, setDownloadUrl] = useState("");
  const [downloads, setDownloads] = useState<DownloadItem[]>([]);
  const [conversions, setConversions] = useState<ConversionItem[]>([]);

  const handleDownload = () => {
    if (!downloadUrl.trim()) return;
    
    // Mock download for now
    const newDownload: DownloadItem = {
      id: Date.now(),
      url: downloadUrl,
      title: "Sample Video",
      status: "processing",
      progress: 0,
      format: "mp4",
      quality: "720p"
    };
    
    setDownloads([newDownload, ...downloads]);
    setDownloadUrl("");
    
    // Simulate progress
    let progress = 0;
    const interval = setInterval(() => {
      progress += 10;
      if (progress >= 100) {
        clearInterval(interval);
        setDownloads(prev => prev.map(d => 
          d.id === newDownload.id 
            ? { ...d, status: "completed", progress: 100 }
            : d
        ));
      } else {
        setDownloads(prev => prev.map(d => 
          d.id === newDownload.id 
            ? { ...d, progress }
            : d
        ));
      }
    }, 500);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Mock conversion for now
    const newConversion: ConversionItem = {
      id: Date.now(),
      filename: file.name,
      status: "processing",
      progress: 0,
      inputFormat: file.name.split('.').pop() || 'unknown',
      outputFormat: "mp4",
      size: file.size
    };
    
    setConversions([newConversion, ...conversions]);
    
    // Simulate progress
    let progress = 0;
    const interval = setInterval(() => {
      progress += 15;
      if (progress >= 100) {
        clearInterval(interval);
        setConversions(prev => prev.map(c => 
          c.id === newConversion.id 
            ? { ...c, status: "completed", progress: 100 }
            : c
        ));
      } else {
        setConversions(prev => prev.map(c => 
          c.id === newConversion.id 
            ? { ...c, progress }
            : c
        ));
      }
    }, 400);
  };

  const removeItem = (id: number, type: 'download' | 'conversion') => {
    if (type === 'download') {
      setDownloads(prev => prev.filter(d => d.id !== id));
    } else {
      setConversions(prev => prev.filter(c => c.id !== id));
    }
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-black/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="h-8 w-8 bg-white rounded-md flex items-center justify-center">
                <span className="text-black font-bold text-sm">MK</span>
              </div>
              <h1 className="text-2xl font-bold">MedKIT</h1>
            </div>
            <nav className="hidden md:flex items-center space-x-6">
              <Link href="/features" className="text-gray-300 hover:text-white transition-colors">
                Features
              </Link>
              <Link href="/pricing" className="text-gray-300 hover:text-white transition-colors">
                Pricing
              </Link>
              <Link href="/docs" className="text-gray-300 hover:text-white transition-colors">
                Docs
              </Link>
            </nav>
            <div className="flex items-center space-x-3">
              <Button variant="ghost" asChild>
                <Link href="/login">Login</Link>
              </Button>
              <Button asChild>
                <Link href="/register">Sign Up</Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 px-4">
        <div className="container mx-auto text-center">
          <h2 className="text-5xl font-bold mb-6 bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            Download & Convert Media Files with Ease
          </h2>
          <p className="text-xl text-gray-400 mb-8 max-w-2xl mx-auto">
            Professional-grade media processing tool. Download from YouTube, Vimeo, and more. 
            Convert between any format. Fast, reliable, and secure.
          </p>
        </div>
      </section>

      {/* Main Tool */}
      <section className=" px-4">
        <div className="container mx-auto max-w-4xl">
          <Tabs defaultValue="download" className="w-full">
            <TabsList className="flex w-full mb-8">
              <TabsTrigger value="download" className="flex-1 flex items-center justify-center space-x-2">
                <Download className="h-4 w-4" />
                <span>Download</span>
              </TabsTrigger>
              <TabsTrigger value="convert" className="flex-1 flex items-center justify-center space-x-2">
                <RefreshCw className="h-4 w-4" />
                <span>Convert</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="download" className="space-y-6">
              <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
                <h3 className="text-lg font-semibold mb-4">Download from URL</h3>
                <div className="flex space-x-3">
                  <Input
                    placeholder="Paste YouTube, Vimeo, or other supported URL..."
                    value={downloadUrl}
                    onChange={(e) => setDownloadUrl(e.target.value)}
                    className="flex-1"
                  />
                  <Button onClick={handleDownload} disabled={!downloadUrl.trim()}>
                    <Download className="h-4 w-4 mr-2" />
                    Download
                  </Button>
                </div>
                <p className="text-sm text-gray-400 mt-2">
                  Supports: YouTube, Vimeo, Dailymotion, TikTok, Instagram, Twitter, and more
                </p>
              </div>

              {/* Download Queue */}
              {downloads.length > 0 && (
                <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
                  <h4 className="text-lg font-semibold mb-4">Downloads</h4>
                  <div className="space-y-4">
                    {downloads.map((download) => (
                      <div key={download.id} className="bg-gray-800 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex-1">
                            <h5 className="font-medium">{download.title}</h5>
                            <p className="text-sm text-gray-400 truncate">{download.url}</p>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-400">
                              {download.quality} • {download.format}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeItem(download.id, 'download')}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          <Progress value={download.progress} className="flex-1" />
                          <span className="text-sm text-gray-400 min-w-[3rem]">
                            {download.progress}%
                          </span>
                        </div>
                        <div className="mt-2 text-sm">
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${
                            download.status === 'completed' 
                              ? 'bg-green-900 text-green-300' 
                              : 'bg-gray-800 text-gray-300'
                          }`}>
                            {download.status === 'completed' ? '✓ Completed' : '⏳ Processing'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="convert" className="space-y-6">
              <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
                <h3 className="text-lg font-semibold mb-4">Convert Media Files</h3>
                <div className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center">
                  <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-gray-400 mb-4">
                    Drop your files here or click to browse
                  </p>
                  <input
                    type="file"
                    accept="video/*,audio/*"
                    onChange={handleFileUpload}
                    className="hidden"
                    id="file-upload"
                  />
                  <Button asChild variant="outline">
                    <label htmlFor="file-upload" className="cursor-pointer">
                      Choose Files
                    </label>
                  </Button>
                  <p className="text-sm text-gray-500 mt-2">
                    Supports: MP4, AVI, MOV, MP3, WAV, FLAC, and more (Max: 500MB)
                  </p>
                </div>
              </div>

              {/* Conversion Queue */}
              {conversions.length > 0 && (
                <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
                  <h4 className="text-lg font-semibold mb-4">Conversions</h4>
                  <div className="space-y-4">
                    {conversions.map((conversion) => (
                      <div key={conversion.id} className="bg-gray-800 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex-1">
                            <h5 className="font-medium">{conversion.filename}</h5>
                            <p className="text-sm text-gray-400">
                              {(conversion.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-400">
                              {conversion.inputFormat} → {conversion.outputFormat}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeItem(conversion.id, 'conversion')}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          <Progress value={conversion.progress} className="flex-1" />
                          <span className="text-sm text-gray-400 min-w-[3rem]">
                            {conversion.progress}%
                          </span>
                        </div>
                        <div className="mt-2 text-sm">
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${
                            conversion.status === 'completed' 
                              ? 'bg-green-900 text-green-300' 
                              : 'bg-gray-800 text-gray-300'
                          }`}>
                            {conversion.status === 'completed' ? '✓ Completed' : '⏳ Converting'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 bg-gray-950">
        <div className="container mx-auto">
          <h3 className="text-3xl font-bold text-center mb-12">Why Choose MedKIT?</h3>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="h-16 w-16 bg-white rounded-full mx-auto mb-4 flex items-center justify-center">
                <Download className="h-8 w-8 text-black" />
              </div>
              <h4 className="text-xl font-semibold mb-3">Fast Downloads</h4>
              <p className="text-gray-400">
                Download from 50+ platforms at maximum speed with our optimized downloader.
              </p>
            </div>
            <div className="text-center">
              <div className="h-16 w-16 bg-white rounded-full mx-auto mb-4 flex items-center justify-center">
                <RefreshCw className="h-8 w-8 text-black" />
              </div>
              <h4 className="text-xl font-semibold mb-3">Universal Converter</h4>
              <p className="text-gray-400">
                Convert between any video and audio format with professional quality.
              </p>
            </div>
            <div className="text-center">
              <div className="h-16 w-16 bg-white rounded-full mx-auto mb-4 flex items-center justify-center">
                <Play className="h-8 w-8 text-black" />
              </div>
              <h4 className="text-xl font-semibold mb-3">Real-time Progress</h4>
              <p className="text-gray-400">
                Track your downloads and conversions with real-time progress updates.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-black border-t border-gray-800 py-12 px-4">
        <div className="container mx-auto text-center">
          <div className="flex items-center justify-center space-x-2 mb-4">
            <div className="h-6 w-6 bg-white rounded-md flex items-center justify-center">
              <span className="text-black font-bold text-xs">MK</span>
            </div>
            <span className="font-semibold">MedKIT</span>
          </div>
          <p className="text-gray-400 mb-4">
            Professional media download and conversion tool
          </p>
          <div className="flex justify-center space-x-6 text-sm text-gray-400">
            <Link href="/privacy" className="hover:text-white transition-colors">
              Privacy Policy
            </Link>
            <Link href="/terms" className="hover:text-white transition-colors">
              Terms of Service
            </Link>
            <Link href="/contact" className="hover:text-white transition-colors">
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
