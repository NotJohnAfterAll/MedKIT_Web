/**
 * Example Download Component using Smart Progress Hook
 * This shows how to integrate the progress smoothing with your download logic
 */
import React, { useState } from 'react';
import useSmartProgress from '../hooks/useSmartProgress';

const DownloadComponent = () => {
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadId, setDownloadId] = useState(null);
  const [url, setUrl] = useState('');
  
  // Use the smart progress hook
  const { 
    progress, 
    message, 
    status, 
    updateProgress, 
    reset, 
    handleComplete, 
    handleError 
  } = useSmartProgress();
  
  const startDownload = async () => {
    if (!url.trim()) return;
    
    setIsDownloading(true);
    reset(); // Reset progress state
    
    try {
      // Generate unique download ID
      const newDownloadId = `download_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setDownloadId(newDownloadId);
      
      // Start progress polling BEFORE starting download
      let pollCount = 0;
      const progressInterval = setInterval(async () => {
        pollCount++;
        console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollCount} - Checking progress for ${newDownloadId}`);
        
        try {
          const progressResponse = await fetch(`/api/downloads/download-progress/${newDownloadId}/`);
          console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollCount} - Response status: ${progressResponse.status}`);
          
          if (!progressResponse.ok) {
            console.error(`[${new Date().toLocaleTimeString()}] POLL ${pollCount} - HTTP Error: ${progressResponse.status}`);
            return;
          }
          
          const progressData = await progressResponse.json();
          console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollCount} - Data:`, progressData);
          
          if (progressData.progress !== undefined) {
            // Let the smart hook handle all the smoothing and anti-backwards logic
            updateProgress(
              progressData.progress, 
              progressData.message || 'Downloading...', 
              progressData.status || 'downloading'
            );
            
            // Only stop polling when REALLY complete - be more careful
            if (progressData.status === 'completed' && progressData.progress >= 99) {
              console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollCount} - STOPPING - Download completed at ${progressData.progress}%`);
              clearInterval(progressInterval);
              handleComplete();
            } else {
              console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollCount} - CONTINUING - Progress: ${progressData.progress}%, Status: ${progressData.status}`);
            }
          } else {
            console.log(`[${new Date().toLocaleTimeString()}] POLL ${pollCount} - No progress data received`);
          }
        } catch (error) {
          console.error(`[${new Date().toLocaleTimeString()}] POLL ${pollCount} - ERROR:`, error);
          // Don't stop polling on error - might be temporary
        }
      }, 500); // Poll every 500ms
      
      // Start the actual download
      console.log(`[${new Date().toLocaleTimeString()}] STARTING DOWNLOAD - Fetch beginning for ${newDownloadId}`);
      const downloadResponse = await fetch('/api/downloads/stream/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: url,
          download_id: newDownloadId,
          quality: '1080p'
        }),
      });
      
      console.log(`[${new Date().toLocaleTimeString()}] DOWNLOAD RESPONSE - Status: ${downloadResponse.status}, OK: ${downloadResponse.ok}`);

      if (!downloadResponse.ok) {
        clearInterval(progressInterval);
        throw new Error(`Download failed: ${downloadResponse.statusText}`);
      }

      // Handle the download response (file stream)
      console.log(`[${new Date().toLocaleTimeString()}] DOWNLOADING BLOB - Starting blob download`);
      const blob = await downloadResponse.blob();
      console.log(`[${new Date().toLocaleTimeString()}] BLOB COMPLETE - Size: ${blob.size} bytes`);
      
      // Stop progress polling since download is complete
      console.log(`[${new Date().toLocaleTimeString()}] CLEANING UP - Stopping progress polling`);
      clearInterval(progressInterval);
      
      const downloadUrl = window.URL.createObjectURL(blob);      // Create download link
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `video_${newDownloadId}.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      
      // Cleanup
      window.URL.revokeObjectURL(downloadUrl);
      
      // Final progress update
      handleComplete();
      console.log(`[${new Date().toLocaleTimeString()}] DOWNLOAD SUCCESS - File saved successfully`);
      
    } catch (error) {
      console.error(`[${new Date().toLocaleTimeString()}] DOWNLOAD ERROR:`, error);
      
      // Make sure to clear interval on any error
      if (typeof progressInterval !== 'undefined') {
        clearInterval(progressInterval);
      }
      
      handleError(`Download failed: ${error.message}`);
    } finally {
      console.log(`[${new Date().toLocaleTimeString()}] DOWNLOAD FINISHED - Cleaning up`);
      
      // Final cleanup
      if (typeof progressInterval !== 'undefined') {
        clearInterval(progressInterval);
      }
      
      setIsDownloading(false);
      setDownloadId(null);
    }
  };
  
  const cancelDownload = () => {
    setIsDownloading(false);
    setDownloadId(null);
    reset();
  };
  
  return (
    <div className="download-container">
      <h2>Smart Progress Download</h2>
      
      <div className="input-section">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Enter video URL..."
          disabled={isDownloading}
          className="url-input"
        />
        
        <button
          onClick={startDownload}
          disabled={isDownloading || !url.trim()}
          className="download-button"
        >
          {isDownloading ? 'Downloading...' : 'Download'}
        </button>
        
        {isDownloading && (
          <button onClick={cancelDownload} className="cancel-button">
            Cancel
          </button>
        )}
      </div>
      
      {/* Progress Display */}
      {(isDownloading || status !== 'idle') && (
        <div className="progress-section">
          <div className="progress-bar-container">
            <div 
              className="progress-bar"
              style={{ 
                width: `${progress}%`,
                backgroundColor: status === 'error' ? '#ef4444' : '#3b82f6',
                transition: 'width 0.2s ease-out' // Smooth CSS transition
              }}
            />
          </div>
          
          <div className="progress-info">
            <span className="progress-percentage">{progress}%</span>
            <span className="progress-message">{message}</span>
          </div>
          
          <div className="status-info">
            Status: <span className={`status-${status}`}>{status}</span>
            {downloadId && <span className="download-id">ID: {downloadId}</span>}
          </div>
        </div>
      )}
    </div>
  );
};

export default DownloadComponent;
