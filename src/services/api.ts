import axios from 'axios';

// Base URL for Flask API
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Send cookies with requests for Flask session
});

// Add request interceptor for auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear auth and redirect to login
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ========================
// Authentication APIs
// ========================

export const authAPI = {
  login: async (username: string, password: string) => {
    const response = await api.post('/api/login', { username, password });
    return response.data;
  },
  
  logout: async () => {
    const response = await api.get('/api/logout');
    return response.data;
  },
};

// ========================
// Detection APIs
// ========================

export interface Detection {
  id: number;
  timestamp: string;
  location: string;
  confidence: number;
  image_path: string;
  status: string;
}

export const detectionAPI = {
  getAll: async (): Promise<Detection[]> => {
    const response = await api.get<Detection[]>('/api/detections');
    return response.data;
  },
  
  getById: async (id: number): Promise<Detection> => {
    const response = await api.get<Detection>(`/api/detections/${id}`);
    return response.data;
  },
  
  delete: async (id: number) => {
    const response = await api.delete(`/api/detections/${id}`);
    return response.data;
  },
  
  downloadImage: async (imagePath: string) => {
    const response = await api.get(`/detections/${imagePath}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

// ========================
// Dashboard Stats APIs
// ========================

export interface DashboardStats {
  total_detections: number;
  today_detections: number;
  camera_status: string;
  notifications_sent: number;
  weekly_data: Array<{ day: string; detections: number; avgConfidence: number }>;
  location_data: Array<{ location: string; count: number }>;
  recent_detections: Detection[];
}

export const dashboardAPI = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await api.get<DashboardStats>('/api/dashboard-stats');
    return response.data;
  },
};

// ========================
// Camera Control APIs
// ========================

export const cameraAPI = {
  start: async () => {
    const response = await api.post('/api/camera/start');
    return response.data;
  },
  
  stop: async () => {
    const response = await api.post('/api/camera/stop');
    return response.data;
  },
  
  getStatus: async () => {
    const response = await api.get('/api/camera/status');
    return response.data;
  },
};

// ========================
// Settings APIs
// ========================

export interface CameraDevice {
  index: number;
  name: string;
  resolution: string;
  fps: number;
}

export interface Settings {
  camera_start_time: string;
  camera_end_time: string;
  blur_faces: boolean;
  confidence_threshold: number;
  camera_index: number;
  camera_name: string;
  sms_notifications: boolean;
  email_notifications: boolean;
  anonymization_percent?: number;
  telegram_notifications?: boolean;
  available_cameras?: CameraDevice[];
  notifications?: {
    email: boolean;
    sms: boolean;
    telegram?: boolean;
  };
}

export const settingsAPI = {
  get: async (): Promise<Settings> => {
    const response = await api.get<Settings>('/api/settings');
    return response.data;
  },
  
  update: async (settings: Partial<Settings>) => {
    const response = await api.post('/api/settings', settings);
    return response.data;
  },
};

export default api;

