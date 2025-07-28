'use client';

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Download, RefreshCw, Upload, X, User, LogOut } from "lucide-react";
import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { api, type DownloadRequest, type ConversionRequest } from "@/lib/api";

interface DownloadItem {
  id: string;
  url: string;
  title: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'ready_for_download';
  progress: number;
  format: string;
  quality: string;
  availableFormats?: VideoFormat[];
  videoInfo?: {
    title: string;
    duration: number;
    thumbnail: string;
  };
}

type VideoFormat = {
  quality: string;
  label?: string;
  format_id: string;
  ext: string;
  filesize?: number;
  has_audio: boolean;
  video_codec: string;
  audio_codec: string;
  fps?: number;
  width?: number;
  height?: number;
  type?: string;
  resolution?: string;
  description?: string;
};

interface ConversionItem {
  id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  input_format: string;
  output_format: string;
  file_size: number;
}

export default function HomePage() {
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  
  const [downloadUrl, setDownloadUrl] = useState("");
  const [downloads, setDownloads] = useState<DownloadItem[]>([]);
  const [conversions, setConversions] = useState<ConversionItem[]>([]);

  // Helper function to simulate progress for offline functionality
  const simulateProgress = (id: string, type: 'download' | 'conversion') => {
    let progress = 0;
    const interval = setInterval(() => {
      progress += 10;
      if (progress >= 100) {
        clearInterval(interval);
        if (type === 'download') {
          setDownloads(prev => prev.map(d => 
            d.id === id 
              ? { ...d, status: "completed", progress: 100 }
              : d
          ));
        } else {
          setConversions(prev => prev.map(c => 
            c.id === id 
              ? { ...c, status: "completed", progress: 100 }
              : c
          ));
        }
      } else {
        if (type === 'download') {
          setDownloads(prev => prev.map(d => 
            d.id === id 
              ? { ...d, progress }
              : d
          ));
        } else {
          setConversions(prev => prev.map(c => 
            c.id === id 
              ? { ...c, progress }
              : c
          ));
        }
      }
    }, 500);
  };

  // Helper function to poll API for progress updates
  const pollProgress = async (id: string, type: 'download' | 'conversion') => {
    const poll = async () => {
      try {
        const response = type === 'download' 
          ? await api.getDownload(id)
          : await api.getConversion(id);
        
        if (response.data) {
          if (type === 'download') {
            const downloadData = response.data as DownloadRequest;
            setDownloads(prev => prev.map(d => 
              d.id === id 
                ? {
                    ...d,
                    status: downloadData.status,
                    progress: downloadData.progress,
                    title: downloadData.title || d.title
                  }
                : d
            ));
          } else {
            const conversionData = response.data as ConversionRequest;
            setConversions(prev => prev.map(c => 
              c.id === id 
                ? {
                    ...c,
                    status: conversionData.status,
                    progress: conversionData.progress
                  }
                : c
            ));
          }

          // Continue polling if not complete
          const status = response.data.status;
          if (status === 'processing' || status === 'pending') {
            setTimeout(poll, 2000);
          }
        }
      } catch {
        console.error('Polling error');
      }
    };

    // Start polling
    setTimeout(poll, 1000);
  };

  const handleDownload = async () => {
    if (!downloadUrl.trim()) return;
    
    // Create a download job first (just to show it's being processed)
    const newDownload: DownloadItem = {
      id: Date.now().toString(),
      url: downloadUrl,
      title: "Loading...",
      status: "processing",
      progress: 0,
      format: "",
      quality: ""
    };
    
    setDownloads([newDownload, ...downloads]);
    setDownloadUrl("");
    
    try {
      // Use new progress tracking API
      const response = await fetch('/api/downloads/video-info-progress/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: downloadUrl })
      });
      
      if (response.ok) {
        const data = await response.json();
        const taskId = data.task_id;
        
        // Start polling for progress updates
        const pollProgress = async () => {
          try {
            const progressResponse = await fetch(`/api/downloads/progress/${taskId}/`);
            if (progressResponse.ok) {
              const progressData = await progressResponse.json();
              const { status, message } = progressData;
              
              // Update download item with loading animation (no progress %)
              setDownloads(prev => prev.map(d => 
                d.id === newDownload.id 
                  ? {
                      ...d,
                      title: message,
                      progress: -1, // Special value for indeterminate progress
                      status: status === 'completed' ? 'ready_for_download' : 'processing'
                    }
                  : d
              ));
              
              if (status === 'completed') {
                const result = progressData.result;
                // Update with final video info and formats - RESET progress to 0
                setDownloads(prev => prev.map(d => 
                  d.id === newDownload.id 
                    ? {
                        ...d,
                        title: result.title,
                        status: "ready_for_download" as const,
                        progress: 0, // Reset to 0 after info extraction
                        availableFormats: result.available_formats,
                        videoInfo: {
                          title: result.title,
                          duration: result.duration,
                          thumbnail: result.thumbnail
                        }
                      }
                    : d
                ));
              } else if (status === 'error') {
                setDownloads(prev => prev.map(d => 
                  d.id === newDownload.id 
                    ? { ...d, status: "failed" as const, title: `Error: ${progressData.error}` }
                    : d
                ));
              } else {
                // Continue polling
                setTimeout(pollProgress, 1000);
              }
            }
          } catch (error) {
            console.error('Progress polling error:', error);
            setDownloads(prev => prev.map(d => 
              d.id === newDownload.id 
                ? { ...d, status: "failed" as const, title: "Failed to get video info" }
                : d
            ));
          }
        };
        
        // Start progress polling
        pollProgress();
        
      } else {
        // Handle error
        setDownloads(prev => prev.map(d => 
          d.id === newDownload.id 
            ? { ...d, status: "failed" as const, title: "Failed to get video info" }
            : d
        ));
      }
    } catch (error) {
      console.error('Error getting video info:', error);
      setDownloads(prev => prev.map(d => 
        d.id === newDownload.id 
          ? { ...d, status: "failed" as const, title: "Failed to get video info" }
          : d
      ));
    }
  };

  const handleFormatDownload = async (downloadId: string, format: VideoFormat) => {
    // Start the actual download by creating a download link
    const downloadUrl = downloads.find(d => d.id === downloadId)?.url;
    if (!downloadUrl) return;
    
    try {
      // Update status to show download is starting
      setDownloads(prev => prev.map(d => 
        d.id === downloadId 
          ? { ...d, status: "processing" as const, progress: 0, title: `${d.videoInfo?.title || 'Video'} - Starting download...` }
          : d
      ));

      // START PROGRESS POLLING IMMEDIATELY - BEFORE the fetch request!
      let serverProgressActive = false;
      
      // Start polling for server-side download progress
      let pollAttempts = 0;
      const maxPollAttempts = 120; // Poll for 30 seconds (120 * 250ms) instead of just 2.5 seconds
      
      const pollDownloadProgress = async () => {
        try {
          pollAttempts++;
          console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - Fetching progress for ${downloadId}`);
          
          const progressResponse = await fetch(`/api/downloads/download-progress/${downloadId}/`);
          console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - Response status: ${progressResponse.status}`);
          if (progressResponse.ok) {
            const progressData = await progressResponse.json();
            const { progress, message, status } = progressData;
            
            console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - Server data:`, {progress, message, status});
            
            // Check if we got actual progress data from server (progress > 0 indicates real data)
            if (progress > 0 && (status === 'downloading' || status === 'unknown')) {
              serverProgressActive = true;
              console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - ACTIVE PROGRESS: ${progress}%`);
              
              // Anti-backwards protection: only update if progress increased or stayed the same
              setDownloads(prev => prev.map(d => {
                if (d.id === downloadId) {
                  const currentProgress = d.progress;
                  const newProgress = Math.max(progress, currentProgress); // Never go backwards
                  
                  if (newProgress > currentProgress) {
                    console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - PROGRESS UPDATED: ${currentProgress}% → ${newProgress}%`);
                  } else if (newProgress < progress) {
                    console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - BACKWARDS BLOCKED: ${progress}% blocked, keeping ${currentProgress}%`);
                  }
                  
                  return {
                    ...d,
                    progress: newProgress,
                    title: message || `${d.videoInfo?.title || 'Video'} - ${newProgress}%`
                  };
                }
                return d;
              }));
              
              // Continue polling if still downloading (check against the protected progress)
              const currentDownload = downloads.find(d => d.id === downloadId);
              const currentProgress = currentDownload?.progress || 0;
              const finalProgress = Math.max(progress, currentProgress);
              
              if (finalProgress < 95) {
                console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - CONTINUING - ${finalProgress}% < 95%`);
                setTimeout(pollDownloadProgress, 250); // Faster polling during active download
                return;
              } else {
                // Server progress nearly complete, stop polling
                console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - STOPPING - Progress complete at ${finalProgress}%`);
                return;
              }
            } else if (progress === 0 && message === 'No progress data available') {
              // No server progress available yet, continue polling if under limit
              if (pollAttempts < maxPollAttempts) {
                console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - NO DATA YET - Continuing (${pollAttempts}/${maxPollAttempts})`);
                setTimeout(pollDownloadProgress, 250); // Faster initial polling too
                return;
              } else {
                console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - MAX ATTEMPTS REACHED - Server progress not available`);
                return;
              }
            } else {
              // Got some progress data but not downloading status
              console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - UNEXPECTED DATA - Progress: ${progress}, Status: ${status}`);
              if (pollAttempts < maxPollAttempts) {
                setTimeout(pollDownloadProgress, 250);
                return;
              }
            }
          } else {
            // Server progress endpoint failed
            console.error(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - HTTP ERROR: ${progressResponse.status}`);
            if (pollAttempts < maxPollAttempts) {
              setTimeout(pollDownloadProgress, 250);
              return;
            }
          }
        } catch (error) {
          console.error(`[${new Date().toLocaleTimeString()}] POLL ${pollAttempts} - EXCEPTION:`, error);
          // Continue polling if not max attempts
          if (pollAttempts < maxPollAttempts) {
            setTimeout(pollDownloadProgress, 250);
            return;
          }
        }
      };
      
      // Start server-side progress polling IMMEDIATELY
      pollDownloadProgress(); // Start immediately before fetch!
      
      // NOW make the fetch request (this will block until download completes)
      const response = await fetch('/api/downloads/stream/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          url: downloadUrl,
          format_id: format.format_id,
          quality: format.quality,
          download_id: downloadId // Pass download ID for progress tracking
        })
      });

      console.log(`Download completed for ID: ${downloadId}`); // This will show AFTER download

      if (response.ok && response.body) {
        // Download completed - handle client streaming for final file transfer
        console.log(`Starting client streaming for ${downloadId}, content length: ${response.headers.get('content-length')}`);
        
        // Determine starting progress based on server progress activity
        const startProgress = serverProgressActive ? 95 : 0;
        console.log(`Starting client streaming from ${startProgress}% (server was ${serverProgressActive ? 'active' : 'inactive'})`);
        
        handleClientStreamingProgress(response, downloadId, format, startProgress);
        
      } else {
        throw new Error('Download failed');
      }
    } catch (error) {
      console.error('Download error:', error);
      setDownloads(prev => prev.map(d => 
        d.id === downloadId 
          ? { ...d, status: "failed" as const, title: "Download failed" }
          : d
      ));
    }
  };

  // Helper function to handle client-side streaming progress
  const handleClientStreamingProgress = async (response: Response, downloadId: string, format: VideoFormat, startProgress: number = 0) => {
    try {
      // Check if download still exists and isn't already completed
      const currentDownload = downloads.find(d => d.id === downloadId);
      if (!currentDownload || currentDownload.status === 'completed') {
        console.log('Download already completed or not found, skipping client streaming');
        return;
      }

      const reader = response.body!.getReader();
      const contentLength = +response.headers.get('Content-Length')!;
      
      console.log(`Starting client streaming for ${downloadId}, content length: ${contentLength}, starting from ${startProgress}%`);
      
      let receivedLength = 0;
      const chunks: Uint8Array[] = [];
      let lastProgressUpdate = Date.now();
      
      // Set a timeout to prevent infinite streaming
      const streamingTimeout = setTimeout(() => {
        console.log('Streaming timeout reached, aborting');
        reader.cancel();
      }, 300000); // 5 minutes max
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        chunks.push(value);
        receivedLength += value.length;
        
        // Calculate progress based on received data, starting from startProgress
        let streamProgress;
        if (contentLength && contentLength > 0) {
          // If we have content length, show real progress from startProgress to 100%
          const downloadProgress = (receivedLength / contentLength) * 100;
          streamProgress = Math.round(startProgress + (downloadProgress * (100 - startProgress) / 100));
        } else {
          // If no content length, estimate based on MB received (fallback)
          const mbReceived = receivedLength / 1024 / 1024;
          streamProgress = Math.min(99, startProgress + Math.round(mbReceived * 2));
        }
        
        // Throttle progress updates to every 500ms to avoid too frequent re-renders
        const now = Date.now();
        if (now - lastProgressUpdate > 500) {
          setDownloads(prev => prev.map(d => 
            d.id === downloadId 
              ? { 
                  ...d, 
                  progress: streamProgress,
                  title: `${d.videoInfo?.title || 'Video'} - Downloading ${Math.round(receivedLength / 1024 / 1024)}MB (${streamProgress}%)`
                }
              : d
          ));
          lastProgressUpdate = now;
        }
      }
      
      clearTimeout(streamingTimeout);
      
      // Create blob from chunks
      const blob = new Blob(chunks);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      
      // Get the actual video title for filename
      const download = downloads.find(d => d.id === downloadId);
      const videoTitle = download?.videoInfo?.title || download?.title || 'video';
      const safeTitle = videoTitle.replace(/[^a-zA-Z0-9\s\-_]/g, '').slice(0, 50);
      
      a.download = `${safeTitle}.${format.ext}`; // Remove quality suffix
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      // Update status to completed
      setDownloads(prev => prev.map(d => 
        d.id === downloadId 
          ? { 
              ...d, 
              status: "completed" as const, 
              progress: 100,
              format: format.ext,
              quality: format.quality,
              title: `Downloaded: ${safeTitle}` // Use actual video title
            }
          : d
      ));
    } catch (error) {
      console.error('Streaming error:', error);
      
      // Only show error if it's not due to download already being completed
      const currentDownload = downloads.find(d => d.id === downloadId);
      if (currentDownload && currentDownload.status !== 'completed') {
        setDownloads(prev => prev.map(d => 
          d.id === downloadId 
            ? { ...d, status: "failed" as const, title: "Download failed" }
            : d
        ));
      }
    }
  };

  // Quick download functions that bypass format selection
  const handleQuickAudioDownload = async () => {
    if (!downloadUrl.trim()) return;
    
    // First get video info, then download
    const newDownload: DownloadItem = {
      id: Date.now().toString(),
      url: downloadUrl,
      title: "Getting video info...",
      status: "processing",
      progress: -1, // Use loading animation
      format: "mp3",
      quality: "audio"
    };
    
    setDownloads([newDownload, ...downloads]);
    const urlToDownload = downloadUrl;
    setDownloadUrl("");
    
    try {
      // Get video info first
      const response = await fetch('/api/downloads/video-info-progress/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: urlToDownload })
      });
      
      if (response.ok) {
        const data = await response.json();
        const taskId = data.task_id;
        
        // Poll for video info completion
        const pollInfoProgress = async () => {
          try {
            const progressResponse = await fetch(`/api/downloads/progress/${taskId}/`);
            if (progressResponse.ok) {
              const progressData = await progressResponse.json();
              const { status, message } = progressData;
              
              if (status === 'completed') {
                const result = progressData.result;
                // Update with video info and start download
                setDownloads(prev => prev.map(d => 
                  d.id === newDownload.id 
                    ? {
                        ...d,
                        title: result.title,
                        progress: 0,
                        videoInfo: {
                          title: result.title,
                          duration: result.duration,
                          thumbnail: result.thumbnail
                        }
                      }
                    : d
                ));
                
                // Now start the audio download
                const audioFormat: VideoFormat = {
                  quality: 'audio',
                  label: 'Audio Only - MP3',
                  format_id: 'bestaudio[ext=mp3]/bestaudio/best[acodec!=none]',
                  ext: 'mp3',
                  has_audio: true,
                  video_codec: 'none',
                  audio_codec: 'auto'
                };
                
                await handleFormatDownload(newDownload.id, audioFormat);
              } else if (status === 'error') {
                setDownloads(prev => prev.map(d => 
                  d.id === newDownload.id 
                    ? { ...d, status: "failed" as const, title: `Error: ${progressData.error}` }
                    : d
                ));
              } else {
                setDownloads(prev => prev.map(d => 
                  d.id === newDownload.id 
                    ? { ...d, title: message, progress: -1 }
                    : d
                ));
                setTimeout(pollInfoProgress, 1000);
              }
            }
          } catch (error) {
            console.error('Info polling error:', error);
            setDownloads(prev => prev.map(d => 
              d.id === newDownload.id 
                ? { ...d, status: "failed" as const, title: "Failed to get video info" }
                : d
            ));
          }
        };
        
        pollInfoProgress();
      } else {
        throw new Error('Failed to start info extraction');
      }
    } catch (error) {
      console.error('Quick audio download error:', error);
      setDownloads(prev => prev.map(d => 
        d.id === newDownload.id 
          ? { ...d, status: "failed" as const, title: "Failed to start download" }
          : d
      ));
    }
  };

  const handleQuickBestQualityDownload = async () => {
    if (!downloadUrl.trim()) return;
    
    // First get video info, then download
    const newDownload: DownloadItem = {
      id: Date.now().toString(),
      url: downloadUrl,
      title: "Getting video info...",
      status: "processing",
      progress: -1, // Use loading animation
      format: "mp4",
      quality: "1080p"
    };
    
    setDownloads([newDownload, ...downloads]);
    const urlToDownload = downloadUrl;
    setDownloadUrl("");
    
    try {
      // Get video info first
      const response = await fetch('/api/downloads/video-info-progress/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: urlToDownload })
      });
      
      if (response.ok) {
        const data = await response.json();
        const taskId = data.task_id;
        
        // Poll for video info completion
        const pollInfoProgress = async () => {
          try {
            const progressResponse = await fetch(`/api/downloads/progress/${taskId}/`);
            if (progressResponse.ok) {
              const progressData = await progressResponse.json();
              const { status, message } = progressData;
              
              if (status === 'completed') {
                const result = progressData.result;
                // Update with video info and start download
                setDownloads(prev => prev.map(d => 
                  d.id === newDownload.id 
                    ? {
                        ...d,
                        title: result.title,
                        progress: 0,
                        videoInfo: {
                          title: result.title,
                          duration: result.duration,
                          thumbnail: result.thumbnail
                        }
                      }
                    : d
                ));
                
                // Now start the best quality download
                const bestFormat: VideoFormat = {
                  quality: '1080p',
                  label: 'Best Quality - 1080p',
                  format_id: 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                  ext: 'mp4',
                  has_audio: true,
                  video_codec: 'auto',
                  audio_codec: 'auto'
                };
                
                await handleFormatDownload(newDownload.id, bestFormat);
              } else if (status === 'error') {
                setDownloads(prev => prev.map(d => 
                  d.id === newDownload.id 
                    ? { ...d, status: "failed" as const, title: `Error: ${progressData.error}` }
                    : d
                ));
              } else {
                setDownloads(prev => prev.map(d => 
                  d.id === newDownload.id 
                    ? { ...d, title: message, progress: -1 }
                    : d
                ));
                setTimeout(pollInfoProgress, 1000);
              }
            }
          } catch (error) {
            console.error('Info polling error:', error);
            setDownloads(prev => prev.map(d => 
              d.id === newDownload.id 
                ? { ...d, status: "failed" as const, title: "Failed to get video info" }
                : d
            ));
          }
        };
        
        pollInfoProgress();
      } else {
        throw new Error('Failed to start info extraction');
      }
    } catch (error) {
      console.error('Quick best quality download error:', error);
      setDownloads(prev => prev.map(d => 
        d.id === newDownload.id 
          ? { ...d, status: "failed" as const, title: "Failed to start download" }
          : d
      ));
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const response = await api.createConversion(file, 'mp4', 'medium');
      
      if (response.error) {
        console.error('Conversion failed:', response.error);
        return;
      }

      if (response.data) {
        const newConversion: ConversionItem = {
          id: response.data.id,
          filename: response.data.filename,
          status: response.data.status,
          progress: response.data.progress,
          input_format: response.data.input_format,
          output_format: response.data.output_format,
          file_size: response.data.file_size
        };
        
        setConversions([newConversion, ...conversions]);
        
        // Start polling for progress updates
        pollProgress(response.data.id, 'conversion');
      }
    } catch {
      // Fallback to mock functionality if API isn't available
      const newConversion: ConversionItem = {
        id: Date.now().toString(),
        filename: file.name,
        status: "processing",
        progress: 0,
        input_format: file.name.split('.').pop() || 'unknown',
        output_format: "mp4",
        file_size: file.size
      };
      
      setConversions([newConversion, ...conversions]);
      
      // Simulate progress
      simulateProgress(newConversion.id, 'conversion');
    }
  };

  const removeItem = (id: string, type: 'download' | 'conversion') => {
    if (type === 'download') {
      setDownloads(prev => prev.filter(d => d.id !== id));
    } else {
      setConversions(prev => prev.filter(c => c.id !== id));
    }
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="border-b border-neutral-800 bg-black sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center">
            {/* Logo Section - Fixed Width */}
            <div className="flex items-center space-x-3 w-1/3">
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
            </div>
            
            {/* Navigation Section - Centered */}
            <nav className="hidden md:flex items-center justify-center space-x-8 w-1/3">
              <Link href="/features" className="text-neutral-400 hover:text-white transition-colors cursor-pointer">
                Features
              </Link>
              <Link href="/pricing" className="text-neutral-400 hover:text-white transition-colors cursor-pointer">
                Pricing
              </Link>
              <Link href="/docs" className="text-neutral-400 hover:text-white transition-colors cursor-pointer">
                Docs
              </Link>
            </nav>
            
            {/* Auth Section - Right Aligned */}
            <div className="flex items-center justify-end space-x-4 w-1/3">
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 border-2 border-neutral-600 border-t-white rounded-full animate-spin"></div>
                </div>
              ) : isAuthenticated ? (
                <>
                  <span className="text-neutral-400 text-sm">
                    Welcome, {user?.first_name}
                  </span>
                  <Button variant="ghost" className="text-neutral-400 hover:text-white" asChild>
                    <Link href="/dashboard">
                      <User className="w-4 h-4 mr-2" />
                      Dashboard
                    </Link>
                  </Button>
                  <Button 
                    variant="ghost" 
                    className="text-neutral-400 hover:text-white" 
                    onClick={logout}
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    Logout
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="ghost" className="text-neutral-400 hover:text-white" asChild>
                    <Link href="/login">Login</Link>
                  </Button>
                  <Button className="bg-white text-black hover:bg-neutral-200" asChild>
                    <Link href="/register">Sign Up</Link>
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-20 px-6">
        <div className="container mx-auto text-center max-w-4xl">
          <h2 className="text-6xl font-bold mb-6 bg-gradient-to-r from-white to-neutral-400 bg-clip-text text-transparent">
            Download & Convert
            <br />
            Media Files
          </h2>
          <p className="text-xl text-neutral-400 mb-12 max-w-3xl mx-auto leading-relaxed">
            Professional-grade media processing tool. Download from YouTube, Vimeo, TikTok and more. 
            Convert between any format with lightning speed.
          </p>
        </div>
      </section>

      {/* Main Tool Section */}
      <section className="pb-16 px-6">
        <div className="container mx-auto max-w-5xl">
          <Tabs defaultValue="download" className="w-full">
            {/* Horizontal Tabs */}
            <div className="flex justify-center mb-12">
              <TabsList className="flex bg-neutral-900 p-2 rounded-xl border border-neutral-800">
                <TabsTrigger 
                  value="download" 
                  className="flex-1 flex items-center justify-center space-x-3 px-8 py-4 rounded-lg data-[state=active]:bg-white data-[state=active]:text-black text-neutral-400"
                >
                  <Download className="h-5 w-5" />
                  <span className="font-medium">Download</span>
                </TabsTrigger>
                <TabsTrigger 
                  value="convert" 
                  className="flex-1 flex items-center justify-center space-x-3 px-8 py-4 rounded-lg data-[state=active]:bg-white data-[state=active]:text-black text-neutral-400"
                >
                  <RefreshCw className="h-5 w-5" />
                  <span className="font-medium">Convert</span>
                </TabsTrigger>
              </TabsList>
            </div>

            {/* Download Tab Content */}
            <TabsContent value="download" className="space-y-8">
              <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800">
                <div className="text-center mb-8">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-neutral-800 rounded-2xl mb-6">
                    <Download className="h-8 w-8 text-neutral-300" />
                  </div>
                  <h3 className="text-3xl font-bold text-white mb-3">Download Media</h3>
                  <p className="text-neutral-400 text-lg">Paste any video URL to get started</p>
                </div>
                
                <div className="max-w-4xl mx-auto">
                  <div className="space-y-4 mb-6">
                    {/* Main input row - wider text field */}
                    <div className="flex space-x-3">
                      <Input
                        placeholder="https://youtube.com/watch?v=..."
                        value={downloadUrl}
                        onChange={(e) => setDownloadUrl(e.target.value)}
                        className="flex-1 h-14 text-lg bg-neutral-800 border-neutral-700 text-white placeholder-neutral-500 focus:border-white"
                      />
                      <Button 
                        onClick={handleDownload} 
                        disabled={!downloadUrl.trim()}
                        className="bg-white text-black hover:bg-neutral-200 h-14 px-8 text-lg font-medium"
                      >
                        <Download className="h-5 w-5 mr-2" />
                        Download
                      </Button>
                    </div>
                    
                    {/* Quick action buttons under the input */}
                    <div className="flex justify-center space-x-4 mt-4">
                      <Button 
                        onClick={handleQuickAudioDownload} 
                        disabled={!downloadUrl.trim()}
                        className="bg-neutral-600 hover:bg-neutral-700 text-white h-12 px-8 text-md font-medium"
                      >
                        Audio Only
                      </Button>
                      <Button 
                        onClick={handleQuickBestQualityDownload} 
                        disabled={!downloadUrl.trim()}
                        className="bg-neutral-600 hover:bg-neutral-700 text-white h-12 px-8 text-md font-medium"
                      >
                        Best Quality
                      </Button>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-center space-x-8 text-sm text-neutral-500">
                    <span className="flex items-center">
                      Supported sites: YouTube, Vimeo, ...
                    </span>
                  </div>
                </div>
              </div>

              {/* Download Queue */}
              {downloads.length > 0 && (
                <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800">
                  <h4 className="text-2xl font-bold text-white mb-6">Downloads</h4>
                  <div className="space-y-4">
                    {downloads.map((download) => (
                      <div key={download.id} className="bg-neutral-800 rounded-xl p-6">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <h5 className="font-bold text-white mb-2">{download.title}</h5>
                            <p className="text-sm text-neutral-400 truncate">{download.url}</p>
                          </div>
                          <div className="flex items-center space-x-4">
                            <span className="text-sm text-neutral-300 bg-neutral-700 px-3 py-1 rounded-lg">
                              {download.quality} • {download.format}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeItem(download.id, 'download')}
                              className="h-10 w-10 text-neutral-400 hover:text-white hover:bg-neutral-700"
                            >
                              <X className="h-5 w-5" />
                            </Button>
                          </div>
                        </div>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-neutral-400">Progress</span>
                            <span className="text-white font-bold">
                              {download.progress === -1 ? '...' : `${download.progress}%`}
                            </span>
                          </div>
                          {download.progress === -1 ? (
                            <div className="h-3 bg-neutral-700 rounded-full overflow-hidden">
                              <div className="h-full bg-white rounded-full animate-enhanced-pulse w-full"></div>
                            </div>
                          ) : (
                            <Progress value={download.progress} className="h-3" />
                          )}
                        </div>
                        {download.status === 'ready_for_download' && download.availableFormats && (
                          <div className="mt-6 space-y-4">
                            <h6 className="text-white font-semibold">Choose Quality & Download:</h6>
                            
                            {/* Fix overlapping text with better button sizing */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                              {download.availableFormats.map((format, index) => (
                                <Button
                                  key={index}
                                  onClick={() => handleFormatDownload(download.id, format)}
                                  className="bg-neutral-900 hover:bg-neutral-900 border border-neutral-800 text-white p-3 h-auto min-h-[80px] flex flex-col items-start justify-start space-y-1 text-left"
                                >
                                  <div className="flex items-center justify-between w-full">
                                    <span className="font-bold text-sm leading-tight">
                                      {format.label || 
                                       (format.quality === 'audio' ? '🎵 Audio' : 
                                        `📹 ${format.quality}`)}
                                    </span>
                                    <Download className="h-4 w-4 flex-shrink-0" />
                                  </div>
                                  <div className="text-xs text-neutral-100 text-left w-full">
                                    <div>{format.ext.toUpperCase()} • {format.has_audio ? 'With Audio' : 'Video Only'}</div>
                                    {format.filesize && (
                                      <div>{Math.round(format.filesize / 1024 / 1024)}MB</div>
                                    )}
                                  </div>
                                  {format.video_codec !== 'none' && format.width && format.height && (
                                    <div className="text-xs text-neutral-200 w-full">
                                      {format.width}x{format.height}
                                      {format.fps && ` • ${format.fps}fps`}
                                    </div>
                                  )}
                                </Button>
                              ))}
                            </div>
                          </div>
                        )}
                        {download.status === 'completed' && (
                          <div className="mt-6">
                            <Button className="bg-green-600 hover:bg-green-700 text-white">
                              ✅ Downloaded: {download.videoInfo?.title || download.title.replace('Downloaded: ', '')}
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>

            {/* Convert Tab Content */}
            <TabsContent value="convert" className="space-y-8">
              <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800">
                <div className="text-center mb-8">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-neutral-800 rounded-2xl mb-6">
                    <RefreshCw className="h-8 w-8 text-neutral-300" />
                  </div>
                  <h3 className="text-3xl font-bold text-white mb-3">Convert Files</h3>
                  <p className="text-neutral-400 text-lg">Upload your files to convert between formats</p>
                </div>

                <div className="max-w-3xl mx-auto">
                  <div className="border-2 border-dashed border-neutral-700 rounded-2xl p-12 text-center hover:border-neutral-600 transition-colors bg-neutral-800">
                    <Upload className="h-16 w-16 mx-auto mb-6 text-neutral-400" />
                    <h4 className="text-2xl font-bold text-white mb-3">
                      Drop files here
                    </h4>
                    <p className="text-neutral-400 mb-8 text-lg">
                      or click to browse from your computer
                    </p>
                    <input
                      type="file"
                      accept="video/*,audio/*"
                      onChange={handleFileUpload}
                      className="hidden"
                      id="file-upload"
                    />
                    <Button asChild className="bg-white text-black hover:bg-neutral-200 h-14 px-8 text-lg font-medium">
                      <label htmlFor="file-upload" className="cursor-pointer">
                        Choose Files
                      </label>
                    </Button>
                    <p className="text-sm text-neutral-500 mt-6">
                      Supports MP4, AVI, MOV, MP3, WAV, FLAC and more • Max 500MB per file
                    </p>
                  </div>
                </div>
              </div>

              {/* Conversion Queue */}
              {conversions.length > 0 && (
                <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800">
                  <h4 className="text-2xl font-bold text-white mb-6">Conversions</h4>
                  <div className="space-y-4">
                    {conversions.map((conversion) => (
                      <div key={conversion.id} className="bg-neutral-800 rounded-xl p-6">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <h5 className="font-bold text-white mb-2">{conversion.filename}</h5>
                            <p className="text-sm text-neutral-400">
                              {(conversion.file_size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                          <div className="flex items-center space-x-4">
                            <span className="text-sm text-neutral-300 bg-neutral-700 px-3 py-1 rounded-lg">
                              {conversion.input_format} → {conversion.output_format}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeItem(conversion.id, 'conversion')}
                              className="h-10 w-10 text-neutral-400 hover:text-white hover:bg-neutral-700"
                            >
                              <X className="h-5 w-5" />
                            </Button>
                          </div>
                        </div>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-neutral-400">Progress</span>
                            <span className="text-white font-bold">{conversion.progress}%</span>
                          </div>
                          <Progress value={conversion.progress} className="h-3" />
                        </div>
                        {conversion.status === 'completed' && (
                          <div className="mt-6">
                            <Button className="bg-white text-black hover:bg-neutral-200">
                              Download Converted File
                            </Button>
                          </div>
                        )}
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
      <section className="py-20 px-6 bg-neutral-950">
        <div className="container mx-auto max-w-6xl">
          <h3 className="text-4xl font-bold text-center mb-16 text-white">Why Choose MedKIT?</h3>
          <div className="grid md:grid-cols-3 gap-12">
            <div className="text-center">
              <div className="h-20 w-20 bg-white rounded-2xl mx-auto mb-6 flex items-center justify-center">
                <Download className="h-10 w-10 text-black" />
              </div>
              <h4 className="text-2xl font-bold mb-4 text-white">Lightning Fast</h4>
              <p className="text-neutral-400 text-lg leading-relaxed">
                Download from 50+ platforms at maximum speed with our optimized downloader engine.
              </p>
            </div>
            <div className="text-center">
              <div className="h-20 w-20 bg-white rounded-2xl mx-auto mb-6 flex items-center justify-center">
                <RefreshCw className="h-10 w-10 text-black" />
              </div>
              <h4 className="text-2xl font-bold mb-4 text-white">Universal Converter</h4>
              <p className="text-neutral-400 text-lg leading-relaxed">
                Convert between any video and audio format with professional quality and speed.
              </p>
            </div>
            <div className="text-center">
              <div className="h-20 w-20 bg-white rounded-2xl mx-auto mb-6 flex items-center justify-center">
                <Upload className="h-10 w-10 text-black" />
              </div>
              <h4 className="text-2xl font-bold mb-4 text-white">Real-time Progress</h4>
              <p className="text-neutral-400 text-lg leading-relaxed">
                Track your downloads and conversions with real-time progress updates and status.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-black border-t border-neutral-800 py-16 px-6">
        <div className="container mx-auto text-center">
          <div className="flex items-center justify-center space-x-3 mb-6">
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
            <span className="text-2xl font-bold text-white">MedKIT</span>
          </div>
          <p className="text-neutral-400 mb-8 text-lg">
            Professional media download and conversion tool
          </p>
          <div className="flex justify-center space-x-8 text-neutral-400">
            <Link href="/privacy" className="hover:text-white transition-colors cursor-pointer">
              Privacy Policy
            </Link>
            <Link href="/terms" className="hover:text-white transition-colors cursor-pointer">
              Terms of Service
            </Link>
            <Link href="/contact" className="hover:text-white transition-colors cursor-pointer">
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
