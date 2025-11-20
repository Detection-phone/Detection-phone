import axios from 'axios';

// Base URL for Flask API - używa proxy, więc puste = względne ścieżki
const API_BASE_URL = process.env.REACT_APP_API_URL || '';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Send cookies with requests for Flask session
});

// Helper to expose base URL when needed by consumers
export const getBaseUrl = (): string => API_BASE_URL;
// Also attach for default export access (api.getBaseUrl())
(api as any).getBaseUrl = getBaseUrl;

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

export interface PaginatedDetectionsResponse {
  detections: Detection[];
  total_pages: number;
  current_page: number;
  has_next: boolean;
  has_prev: boolean;
}

export const detectionAPI = {
  getAll: async (page: number = 1, perPage: number = 20): Promise<PaginatedDetectionsResponse> => {
    const response = await api.get<PaginatedDetectionsResponse>('/api/detections', {
      params: { page, per_page: perPage }
    });
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
  
  deleteBatch: async (ids: (number | string)[]) => {
    const response = await api.delete('/api/detections/batch', {
      data: { ids }
    });
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
  
  getConfigSnapshot: async (): Promise<Blob> => {
    // Dodajemy parametr 't' z aktualnym czasem, aby przełamać cache
    const response = await api.get(`/api/camera/config_snapshot?t=${Date.now()}`, {
      responseType: 'blob',
    });
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

export interface DaySchedule {
  enabled: boolean;
  start: string; // HH:MM format
  end: string; // HH:MM format
}

export interface WeeklySchedule {
  monday: DaySchedule;
  tuesday: DaySchedule;
  wednesday: DaySchedule;
  thursday: DaySchedule;
  friday: DaySchedule;
  saturday: DaySchedule;
  sunday: DaySchedule;
}

export interface Settings {
  schedule?: WeeklySchedule; // New weekly schedule
  camera_start_time?: string; // Legacy - kept for backward compatibility
  camera_end_time?: string; // Legacy - kept for backward compatibility
  blur_faces: boolean;
  confidence_threshold: number;
  camera_index: number;
  camera_name: string;
  sms_notifications: boolean;
  email_notifications: boolean;
  anonymization_percent?: number;
  roi_coordinates?: [number, number, number, number] | null; // Legacy single ROI
  roi_zones?: ROIZone[]; // New multiple ROI zones
  telegram_notifications?: boolean;
  available_cameras?: CameraDevice[];
  notifications?: {
    email: boolean;
    sms: boolean;
    telegram?: boolean;
  };
}

export interface ROIZone {
  id: string;
  name: string;
  coords: {
    x: number; // normalized 0-1
    y: number; // normalized 0-1
    w: number; // normalized 0-1
    h: number; // normalized 0-1
  };
}

export interface ROIZonesResponse {
  roi_zones: ROIZone[];
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
  
  getROIZones: async (): Promise<ROIZone[]> => {
    const response = await api.get<ROIZonesResponse>('/api/settings/roi');
    return response.data.roi_zones;
  },
  
  saveROIZones: async (roiZones: ROIZone[]) => {
    const response = await api.post<ROIZonesResponse>('/api/settings/roi', {
      roi_zones: roiZones,
    });
    return response.data;
  },
};

export default api;

