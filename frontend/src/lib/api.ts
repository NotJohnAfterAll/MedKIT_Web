// API utility functions for the MedKIT application

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

interface LoginResponse {
  access: string;
  refresh: string;
  user: {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
    is_premium: boolean;
    date_joined: string;
  };
}

interface DownloadRequest {
  id: string;
  url: string;
  title: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  format: string;
  quality: string;
  file_size?: number;
  created_at: string;
  completed_at?: string;
  download_url?: string;
  error_message?: string;
}

interface ConversionRequest {
  id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  input_format: string;
  output_format: string;
  quality: string;
  file_size: number;
  created_at: string;
  completed_at?: string;
  download_url?: string;
  error_message?: string;
}

interface VideoInfo {
  title: string;
  duration: number;
  thumbnail: string;
  available_formats: VideoFormat[];
}

interface VideoFormat {
  quality: string;
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
}

interface SupportedFormats {
  video: string[];
  audio: string[];
  image: string[];
}

interface UserProfile {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  is_premium: boolean;
  date_joined: string;
  daily_downloads: number;
  daily_conversions: number;
}

interface UserUpdateData {
  first_name?: string;
  last_name?: string;
  email?: string;
}

class ApiClient {
  private baseURL: string;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
    // Initialize tokens from localStorage if available
    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('access_token');
      this.refreshToken = localStorage.getItem('refresh_token');
    }
  }

  setTokens(accessToken: string, refreshToken: string) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);
    }
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  }

  private async refreshAccessToken(): Promise<boolean> {
    if (!this.refreshToken) return false;

    try {
      const response = await fetch(`${this.baseURL}/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: this.refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        this.accessToken = data.access;
        if (typeof window !== 'undefined') {
          localStorage.setItem('access_token', data.access);
        }
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }

    this.clearTokens();
    return false;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    skipAuth = false
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...(!skipAuth && this.accessToken && { 
          Authorization: `Bearer ${this.accessToken}` 
        }),
        ...options.headers,
      },
      ...options,
    };

    try {
      let response = await fetch(url, config);

      // If unauthorized and we have a refresh token, try to refresh
      if (response.status === 401 && !skipAuth && this.refreshToken) {
        const refreshed = await this.refreshAccessToken();
        if (refreshed) {
          // Retry the request with new token
          config.headers = {
            ...config.headers,
            Authorization: `Bearer ${this.accessToken}`,
          };
          response = await fetch(url, config);
        }
      }

      const contentType = response.headers.get('content-type');
      let data;

      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        return {
          error: typeof data === 'object' ? data.detail || data.message || `HTTP ${response.status}` : data,
          status: response.status,
        };
      }

      return {
        data,
        status: response.status,
      };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      };
    }
  }

  // Authentication methods
  async login(email: string, password: string): Promise<ApiResponse<LoginResponse>> {
    const response = await this.request<LoginResponse>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }, true);

    if (response.data) {
      this.setTokens(response.data.access, response.data.refresh);
    }

    return response;
  }

  async register(userData: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
  }): Promise<ApiResponse<LoginResponse>> {
    const response = await this.request<LoginResponse>('/auth/register/', {
      method: 'POST',
      body: JSON.stringify(userData),
    }, true);

    if (response.data) {
      this.setTokens(response.data.access, response.data.refresh);
    }

    return response;
  }

  async logout(): Promise<ApiResponse<void>> {
    const response = await this.request<void>('/auth/logout/', {
      method: 'POST',
      body: JSON.stringify({ refresh: this.refreshToken }),
    });
    this.clearTokens();
    return response;
  }

  // User profile methods
  async getProfile() {
    return this.request<UserProfile>('/profile/');
  }

  async updateProfile(userData: UserUpdateData) {
    return this.request<UserProfile>('/profile/', {
      method: 'PATCH',
      body: JSON.stringify(userData),
    });
  }

  // Stats methods
  async getSystemStats() {
    return this.request('/stats/');
  }

  async getDownloadStats() {
    return this.request('/downloads/stats/');
  }

  async getConversionStats() {
    return this.request('/conversions/stats/');
  }

  // Activity methods
  async getActivityLogs(limit = 10) {
    return this.request(`/activity-logs/?limit=${limit}`);
  }

  // Recent items
  async getRecentDownloads(limit = 5) {
    return this.request<DownloadRequest[]>(`/downloads/history/?limit=${limit}`);
  }

  async getRecentConversions(limit = 5) {
    return this.request<ConversionRequest[]>(`/conversions/history/?limit=${limit}`);
  }

  // Download methods
  async createDownload(
    url: string, 
    format = 'mp4', 
    quality = '720p'
  ): Promise<ApiResponse<DownloadRequest>> {
    return this.request<DownloadRequest>('/downloads/requests/', {
      method: 'POST',
      body: JSON.stringify({ url, format, quality }),
    }, true); // Allow anonymous access
  }

  async getDownloads(): Promise<ApiResponse<DownloadRequest[]>> {
    return this.request<DownloadRequest[]>('/downloads/requests/');
  }

  async getDownload(id: string): Promise<ApiResponse<DownloadRequest>> {
    return this.request<DownloadRequest>(`/downloads/requests/${id}/`, {}, true); // Allow anonymous access
  }

  async deleteDownload(id: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/downloads/requests/${id}/`, {
      method: 'DELETE',
    });
  }

  // Conversion methods
  async createConversion(
    file: File,
    outputFormat: string,
    quality = 'medium'
  ): Promise<ApiResponse<ConversionRequest>> {
    const formData = new FormData();
    formData.append('input_file', file);
    formData.append('output_format', outputFormat);
    formData.append('quality', quality);

    return this.request<ConversionRequest>('/conversions/requests/', {
      method: 'POST',
      body: formData,
      headers: {
        // Remove Content-Type to let browser set it with boundary
        ...(this.accessToken && { Authorization: `Bearer ${this.accessToken}` }),
      },
    });
  }

  async getConversions(): Promise<ApiResponse<ConversionRequest[]>> {
    return this.request<ConversionRequest[]>('/conversions/requests/');
  }

  async getConversion(id: string): Promise<ApiResponse<ConversionRequest>> {
    return this.request<ConversionRequest>(`/conversions/requests/${id}/`, {}, true); // Allow anonymous access
  }

  async deleteConversion(id: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/conversions/requests/${id}/`, {
      method: 'DELETE',
    });
  }

  // Get video information
  async getVideoInfo(url: string): Promise<ApiResponse<VideoInfo>> {
    return this.request<VideoInfo>('/downloads/video-info/', {
      method: 'POST',
      body: JSON.stringify({ url }),
    }, true); // Skip auth for anonymous access
  }

  // Get supported conversion formats
  async getSupportedFormats(inputFormat?: string): Promise<ApiResponse<SupportedFormats | { input_format: string; supported_outputs: string[] }>> {
    const endpoint = inputFormat 
      ? `/conversions/supported-formats/?input_format=${encodeURIComponent(inputFormat)}`
      : '/conversions/supported-formats/';
    
    return this.request<SupportedFormats | { input_format: string; supported_outputs: string[] }>(endpoint, {}, true);
  }

  // File download
  async downloadFile(id: string, type: 'download' | 'conversion'): Promise<Blob> {
    const endpoint = type === 'download' 
      ? `/downloads/requests/${id}/download_file/`
      : `/conversions/requests/${id}/download_file/`;
    
    const url = `${this.baseURL}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        ...(this.accessToken && { Authorization: `Bearer ${this.accessToken}` }),
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.blob();
  }

  // Utility method to check if user is authenticated
  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  // Get current user info from token (for quick access)
  getCurrentUser() {
    if (!this.accessToken) return null;
    
    try {
      // Decode JWT token to get user info
      const payload = JSON.parse(atob(this.accessToken.split('.')[1]));
      return payload;
    } catch {
      return null;
    }
  }
}

export const api = new ApiClient(API_BASE_URL);
export default api;

// Export types for use in components
export type { 
  ApiResponse, 
  LoginResponse, 
  DownloadRequest, 
  ConversionRequest, 
  VideoInfo, 
  VideoFormat, 
  SupportedFormats 
};
