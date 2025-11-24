import axios from 'axios';


const API_BASE_URL = process.env.REACT_APP_API_URL || '';


const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});


export const getBaseUrl = (): string => API_BASE_URL;

(api as any).getBaseUrl = getBaseUrl;


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


api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {

      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);





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

    const response = await api.get(`/api/camera/config_snapshot?t=${Date.now()}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};





export interface CameraDevice {
  index: number;
  name: string;
  resolution: string;
  fps: number;
}

export interface DaySchedule {
  enabled: boolean;
  start: string;
  end: string;
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
  schedule?: WeeklySchedule;
  camera_start_time?: string;
  camera_end_time?: string;
  blur_faces: boolean;
  confidence_threshold: number;
  camera_index: number;
  camera_name: string;
  sms_notifications: boolean;
  email_notifications: boolean;
  anonymization_percent?: number;
  roi_coordinates?: [number, number, number, number] | null;
  roi_zones?: ROIZone[];
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
    x: number;
    y: number;
    w: number;
    h: number;
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

