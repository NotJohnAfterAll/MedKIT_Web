'use client';

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Download, RefreshCw, Upload, X, ArrowRight, Sparkles } from "lucide-react";
import { useState } from "react";
import Link from "next/link";
import Image from "next/image";

type ActiveTab = 'download' | 'convert';

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
  const [activeTab, setActiveTab] = useState<ActiveTab>('download');
  const [downloadUrl, setDownloadUrl] = useState("");
  const [downloads, setDownloads] = useState<DownloadItem[]>([]);
  const [conversions, setConversions] = useState<ConversionItem[]>([]);

  const handleDownload = () => {
    if (!downloadUrl.trim()) return;
    
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
    <div className="min-h-screen bg-white text-gray-900">
      {/* Navigation */}
      <header className="border-b border-gray-200 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="relative h-8 w-8">
                <Image 
                  src="/medkit.svg" 
                  alt="MedKIT" 
                  width={32} 
                  height={32}
                  className="h-8 w-8"
                />
              </div>
              <h1 className="text-xl font-semibold text-gray-900">MedKIT</h1>
            </div>
            <nav className="hidden md:flex items-center space-x-8">
              <Link href="/features" className="text-gray-600 hover:text-gray-900 transition-colors text-sm font-medium">
                Features
              </Link>
              <Link href="/pricing" className="text-gray-600 hover:text-gray-900 transition-colors text-sm font-medium">
                Pricing
              </Link>
              <Link href="/docs" className="text-gray-600 hover:text-gray-900 transition-colors text-sm font-medium">
                Documentation
              </Link>
            </nav>
            <div className="flex items-center space-x-3">
              <Button variant="ghost" asChild className="text-gray-600 hover:text-gray-900">
                <Link href="/login">Sign in</Link>
              </Button>
              <Button asChild className="bg-gray-900 hover:bg-gray-800 text-white">
                <Link href="/register">Get started</Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-24 px-4">
        <div className="container mx-auto text-center max-w-4xl">
          <div className="inline-flex items-center space-x-2 bg-gray-100 rounded-full px-4 py-2 mb-8">
            <div className="w-3 h-3">
              <svg viewBox="0 0 12 12" fill="none">
                <path d="M6 2 L10 8 L2 8 Z" fill="#374151"/>
              </svg>
            </div>
            <span className="text-sm font-medium text-gray-700">Professional media processing</span>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6">
            Download & Convert
            <br />
            <span className="bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
              Media Files
            </span>
          </h1>
          
          <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto leading-relaxed">
            Professional-grade tool for downloading from YouTube, Vimeo, TikTok and converting 
            between any media format. Fast, reliable, and beautifully simple.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <Button 
              size="lg" 
              className="bg-gray-900 hover:bg-gray-800 text-white px-8 py-3"
              onClick={() => setActiveTab('download')}
            >
              Start downloading
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <Button 
              variant="outline" 
              size="lg" 
              className="border-gray-300 text-gray-700 hover:bg-gray-50 px-8 py-3"
            >
              View examples
            </Button>
          </div>
        </div>
      </section>

      {/* Main Interface */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="container mx-auto max-w-4xl">
          {/* Tab Selector */}
          <div className="flex justify-center mb-12">
            <div className="bg-white rounded-xl p-1.5 border border-gray-200 shadow-sm">
              <button
                onClick={() => setActiveTab('download')}
                className={`px-6 py-3 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
                  activeTab === 'download'
                    ? 'bg-gray-900 text-white shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <Download className="h-4 w-4" />
                <span>Download</span>
              </button>
              <button
                onClick={() => setActiveTab('convert')}
                className={`px-6 py-3 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
                  activeTab === 'convert'
                    ? 'bg-gray-900 text-white shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <RefreshCw className="h-4 w-4" />
                <span>Convert</span>
              </button>
            </div>
          </div>

          {/* Content Area */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            {activeTab === 'download' ? (
              <div className="p-8">
                <div className="text-center mb-8">
                  <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-100 rounded-xl mb-4">
                    <Download className="h-6 w-6 text-gray-700" />
                  </div>
                  <h3 className="text-2xl font-semibold text-gray-900 mb-2">Download Media</h3>
                  <p className="text-gray-600">Paste any video URL to get started</p>
                </div>
                
                <div className="max-w-2xl mx-auto">
                  <div className="flex space-x-3 mb-4">
                    <Input
                      placeholder="https://youtube.com/watch?v=..."
                      value={downloadUrl}
                      onChange={(e) => setDownloadUrl(e.target.value)}
                      className="flex-1 h-12 border-gray-300 focus:border-gray-900 focus:ring-gray-900"
                    />
                    <Button 
                      onClick={handleDownload} 
                      disabled={!downloadUrl.trim()}
                      className="bg-gray-900 hover:bg-gray-800 text-white h-12 px-6"
                    >
                      Download
                    </Button>
                  </div>
                  
                  <div className="flex items-center justify-center space-x-6 text-sm text-gray-500">
                    <span className="flex items-center">
                      <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                      YouTube
                    </span>
                    <span className="flex items-center">
                      <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                      Vimeo
                    </span>
                    <span className="flex items-center">
                      <div className="w-2 h-2 bg-red-500 rounded-full mr-2"></div>
                      TikTok
                    </span>
                    <span className="flex items-center">
                      <div className="w-2 h-2 bg-purple-500 rounded-full mr-2"></div>
                      Instagram
                    </span>
                  </div>
                </div>

                {downloads.length > 0 && (
                  <div className="mt-12 space-y-4">
                    <h4 className="font-semibold text-gray-900 mb-4">Downloads</h4>
                    {downloads.map((download) => (
                      <div key={download.id} className="bg-gray-50 rounded-xl p-6 border border-gray-200">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <h5 className="font-medium text-gray-900 mb-1">{download.title}</h5>
                            <p className="text-sm text-gray-500 truncate">{download.url}</p>
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className="text-sm text-gray-500 bg-white px-2 py-1 rounded-md border">
                              {download.quality} • {download.format}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeItem(download.id, 'download')}
                              className="h-8 w-8 text-gray-400 hover:text-gray-600"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-600">Progress</span>
                            <span className="text-gray-900 font-medium">{download.progress}%</span>
                          </div>
                          <Progress value={download.progress} className="h-2" />
                        </div>
                        {download.status === 'completed' && (
                          <div className="mt-4">
                            <Button size="sm" className="bg-gray-900 hover:bg-gray-800 text-white">
                              Download file
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8">
                <div className="text-center mb-8">
                  <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-100 rounded-xl mb-4">
                    <RefreshCw className="h-6 w-6 text-gray-700" />
                  </div>
                  <h3 className="text-2xl font-semibold text-gray-900 mb-2">Convert Files</h3>
                  <p className="text-gray-600">Upload your files to convert between formats</p>
                </div>

                <div className="max-w-2xl mx-auto">
                  <div className="border-2 border-dashed border-gray-300 rounded-2xl p-12 text-center hover:border-gray-400 transition-colors bg-gray-50">
                    <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      Drop files here
                    </h4>
                    <p className="text-gray-600 mb-6">
                      or click to browse from your computer
                    </p>
                    <input
                      type="file"
                      accept="video/*,audio/*"
                      onChange={handleFileUpload}
                      className="hidden"
                      id="file-upload"
                    />
                    <Button asChild className="bg-gray-900 hover:bg-gray-800 text-white">
                      <label htmlFor="file-upload" className="cursor-pointer">
                        Choose files
                      </label>
                    </Button>
                    <p className="text-sm text-gray-500 mt-4">
                      Supports MP4, AVI, MOV, MP3, WAV, FLAC and more • Max 500MB per file
                    </p>
                  </div>
                </div>

                {conversions.length > 0 && (
                  <div className="mt-12 space-y-4">
                    <h4 className="font-semibold text-gray-900 mb-4">Conversions</h4>
                    {conversions.map((conversion) => (
                      <div key={conversion.id} className="bg-gray-50 rounded-xl p-6 border border-gray-200">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <h5 className="font-medium text-gray-900 mb-1">{conversion.filename}</h5>
                            <p className="text-sm text-gray-500">
                              {(conversion.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className="text-sm text-gray-500 bg-white px-2 py-1 rounded-md border">
                              {conversion.inputFormat} → {conversion.outputFormat}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeItem(conversion.id, 'conversion')}
                              className="h-8 w-8 text-gray-400 hover:text-gray-600"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-600">Progress</span>
                            <span className="text-gray-900 font-medium">{conversion.progress}%</span>
                          </div>
                          <Progress value={conversion.progress} className="h-2" />
                        </div>
                        {conversion.status === 'completed' && (
                          <div className="mt-4">
                            <Button size="sm" className="bg-gray-900 hover:bg-gray-800 text-white">
                              Download converted file
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-4">
        <div className="container mx-auto max-w-6xl">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Everything you need
            </h2>
            <p className="text-xl text-gray-600">
              Professional tools for all your media processing needs
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center group">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-2xl mb-6 group-hover:bg-gray-200 transition-colors">
                <div className="w-6 h-6">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path d="M12 4 L20 16 L4 16 Z" fill="#374151"/>
                  </svg>
                </div>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Lightning Fast</h3>
              <p className="text-gray-600 leading-relaxed">
                Download from 50+ platforms at maximum speed with our optimized processing engine.
              </p>
            </div>
            
            <div className="text-center group">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-2xl mb-6 group-hover:bg-gray-200 transition-colors">
                <div className="w-6 h-6">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path d="M12 4 L20 16 L4 16 Z" fill="#374151"/>
                    <path d="M12 8 L16 14 L8 14 Z" fill="#ffffff"/>
                  </svg>
                </div>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Universal Support</h3>
              <p className="text-gray-600 leading-relaxed">
                Convert between any video and audio format with professional quality output.
              </p>
            </div>
            
            <div className="text-center group">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-2xl mb-6 group-hover:bg-gray-200 transition-colors">
                <Sparkles className="h-6 w-6 text-gray-700" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Real-time Progress</h3>
              <p className="text-gray-600 leading-relaxed">
                Track your downloads and conversions with detailed progress updates and analytics.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-50 border-t border-gray-200 py-12 px-4">
        <div className="container mx-auto text-center">
          <div className="flex items-center justify-center space-x-3 mb-6">
            <div className="relative h-8 w-8">
              <Image 
                src="/medkit.svg" 
                alt="MedKIT" 
                width={32} 
                height={32}
                className="h-8 w-8"
              />
            </div>
            <span className="font-semibold text-xl text-gray-900">MedKIT</span>
          </div>
          <p className="text-gray-600 mb-8 max-w-md mx-auto">
            Professional media download and conversion tool. 
            Fast, reliable, and beautifully simple.
          </p>
          <div className="flex justify-center space-x-8 text-sm text-gray-500">
            <Link href="/privacy" className="hover:text-gray-900 transition-colors">
              Privacy Policy
            </Link>
            <Link href="/terms" className="hover:text-gray-900 transition-colors">
              Terms of Service
            </Link>
            <Link href="/contact" className="hover:text-gray-900 transition-colors">
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
