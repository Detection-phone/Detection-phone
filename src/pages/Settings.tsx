import React, { useState, useEffect, useRef, MouseEvent } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Grid,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Slider,
  Snackbar,
  Alert,
  Chip,
  IconButton,
  FormControl,
  FormLabel,
  FormHelperText,
  Stack,
  alpha,
  CircularProgress,
  Checkbox,
  ButtonGroup,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Radio,
  RadioGroup,
} from '@mui/material';
import { LoadingButton } from '@mui/lab';
import api, { settingsAPI, cameraAPI, CameraDevice, ROIZone } from '../services/api';
import { useConfig } from '../contexts/ConfigContext';
import {
  ExpandMore,
  Schedule,
  Tune,
  Security,
  Notifications,
  Settings as SettingsIcon,
  Save,
  Refresh,
  WbTwilight,
  Brightness4,
  NotificationsActive,
  Email,
  Sms,
  Videocam,
  VideocamOff,
  PlayArrow,
  Stop,
  Camera,
  FilterCenterFocus,
  Delete,
  Edit,
  Add,
} from '@mui/icons-material';
import { TimePicker } from '@mui/x-date-pickers/TimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { pl } from 'date-fns/locale';
import { Select, MenuItem, InputLabel } from '@mui/material';

// Confidence threshold marks
const confidenceMarks = [
  { value: 0, label: '0%' },
  { value: 20, label: '20%' },
  { value: 40, label: '40%' },
  { value: 60, label: '60%' },
  { value: 80, label: '80%' },
  { value: 100, label: '100%' },
];

// Helper: Convert time string (HH:MM) to Date
const timeStringToDate = (timeStr: string): Date => {
  const [hours, minutes] = timeStr.split(':').map(Number);
  const date = new Date();
  date.setHours(hours, minutes, 0, 0);
  return date;
};

// Helper: Convert Date to time string (HH:MM)
const dateToTimeString = (date: Date): string => {
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${hours}:${minutes}`;
};

// Type for weekly schedule
type DaySchedule = {
  enabled: boolean;
  start: string; // HH:MM format
  end: string; // HH:MM format
};

type WeeklySchedule = {
  monday: DaySchedule;
  tuesday: DaySchedule;
  wednesday: DaySchedule;
  thursday: DaySchedule;
  friday: DaySchedule;
  saturday: DaySchedule;
  sunday: DaySchedule;
};

// Default schedule structure
const DEFAULT_SCHEDULE: WeeklySchedule = {
  monday: { enabled: true, start: '07:00', end: '16:00' },
  tuesday: { enabled: true, start: '07:00', end: '16:00' },
  wednesday: { enabled: true, start: '07:00', end: '16:00' },
  thursday: { enabled: true, start: '07:00', end: '16:00' },
  friday: { enabled: true, start: '07:00', end: '16:00' },
  saturday: { enabled: false, start: '07:00', end: '16:00' },
  sunday: { enabled: false, start: '07:00', end: '16:00' },
};

const Settings: React.FC = () => {
  const [settings, setSettings] = useState({
    schedule: DEFAULT_SCHEDULE,
    blurFaces: true,
    anonymizationPercent: 50,
    emailEnabled: true,
    smsEnabled: false,
    confidenceThreshold: 20,
    cameraIndex: 0,
    cameraName: 'Camera 1',
    roi: null as [number, number, number, number] | null,
  });

  const [availableCameras, setAvailableCameras] = useState<CameraDevice[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);
  const [cameraStatus, setCameraStatus] = useState({
    isRunning: false,
    withinSchedule: false,
  });
  const [cameraLoading, setCameraLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
    autoHideDuration?: number;
  }>({
    open: false,
    message: '',
    severity: 'success',
  });
  const [expanded, setExpanded] = useState<string | false>('schedule');

  // ROI state
  const [isRoiExpanded, setIsRoiExpanded] = useState(false);

  // Config photo state (for ROI configuration) - using global context
  const { configPhotoUrl, setConfigPhotoUrl } = useConfig();
  const [isLoadingPhoto, setIsLoadingPhoto] = useState(false);

  // New ROI zones state
  const [drawingMode, setDrawingMode] = useState<'none' | 'single' | 'grid' | 'edit'>('none');
  const [currentRect, setCurrentRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const [savedROIs, setSavedROIs] = useState<ROIZone[]>([]);
  const [gridGeneratorRect, setGridGeneratorRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const [numRows, setNumRows] = useState<number>(4);
  const [numCols, setNumCols] = useState<number>(5);
  const [gridPrefix, setGridPrefix] = useState<string>('');
  const [gridNamingOrder, setGridNamingOrder] = useState<'rows-cols' | 'cols-rows'>('rows-cols');
  const [gridNamingMode, setGridNamingMode] = useState<'sequential' | 'grid'>('sequential');
  
  // Drawing state
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawEnd, setDrawEnd] = useState<{ x: number; y: number } | null>(null);
  const [pendingZoneName, setPendingZoneName] = useState<string>('');
  const [editingZoneId, setEditingZoneId] = useState<string | null>(null);
  const [editingZoneName, setEditingZoneName] = useState<string>('');
  
  // ROI editing state
  const [selectedROIId, setSelectedROIId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeHandle, setResizeHandle] = useState<'nw' | 'ne' | 'sw' | 'se' | null>(null);
  const [resizeStart, setResizeStart] = useState<{ x: number; y: number; coords: { x: number; y: number; w: number; h: number } } | null>(null);
  
  // Dialog state
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  
  // Autosave state
  const autosaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const imgRef = React.useRef<HTMLImageElement | null>(null);
  const wrapperRef = React.useRef<HTMLDivElement | null>(null);

  // Fetch settings and camera status on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch settings
        const fetchedSettings = await settingsAPI.get();
        
        console.log('📡 Fetched settings:', fetchedSettings);
        
        // Set available cameras (ensure it's always an array)
        if (fetchedSettings.available_cameras && Array.isArray(fetchedSettings.available_cameras)) {
          setAvailableCameras(fetchedSettings.available_cameras);
        } else {
          setAvailableCameras([]);
        }
        
        // Handle schedule - check for new weekly schedule or fallback to old format
        let schedule = DEFAULT_SCHEDULE;
        if ((fetchedSettings as any).schedule) {
          // New weekly schedule format
          schedule = (fetchedSettings as any).schedule as WeeklySchedule;
        } else if ((fetchedSettings as any).camera_start_time && (fetchedSettings as any).camera_end_time) {
          // Legacy format - convert to weekly schedule (Mon-Fri enabled)
          const startTime = (fetchedSettings as any).camera_start_time;
          const endTime = (fetchedSettings as any).camera_end_time;
          schedule = {
            monday: { enabled: true, start: startTime, end: endTime },
            tuesday: { enabled: true, start: startTime, end: endTime },
            wednesday: { enabled: true, start: startTime, end: endTime },
            thursday: { enabled: true, start: startTime, end: endTime },
            friday: { enabled: true, start: startTime, end: endTime },
            saturday: { enabled: false, start: startTime, end: endTime },
            sunday: { enabled: false, start: startTime, end: endTime },
          };
        }
        
        setSettings({
          schedule: schedule,
          blurFaces: fetchedSettings.blur_faces,
          anonymizationPercent: fetchedSettings.anonymization_percent ?? 50,
          emailEnabled: fetchedSettings.email_notifications || fetchedSettings.notifications?.email || false,
          smsEnabled: fetchedSettings.sms_notifications || fetchedSettings.notifications?.sms || false,
          confidenceThreshold: Math.round(fetchedSettings.confidence_threshold * 100), // Convert 0-1 to 0-100
          cameraIndex: fetchedSettings.camera_index || 0,
          cameraName: fetchedSettings.camera_name || 'Camera 1',
          roi: (fetchedSettings as any).roi_coordinates || null,
        });

        // Fetch camera status
        const status = await cameraAPI.getStatus();
        setCameraStatus({
          isRunning: status.is_running,
          withinSchedule: status.within_schedule,
        });

        // Fetch ROI zones
        // ✅ FIXED: Ensure savedROIs is always an array
        if (fetchedSettings.roi_zones && Array.isArray(fetchedSettings.roi_zones)) {
          setSavedROIs(fetchedSettings.roi_zones);
        } else {
          // Try to fetch from dedicated endpoint
          try {
            const roiZones = await settingsAPI.getROIZones();
            setSavedROIs(Array.isArray(roiZones) ? roiZones : []);
          } catch (error) {
            console.error('Error fetching ROI zones:', error);
            // ✅ FIXED: Set empty array on error to prevent undefined
            setSavedROIs([]);
          }
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        setSnackbar({
          open: true,
          message: 'Failed to load settings',
          severity: 'error',
        });
      } finally {
        setInitialLoad(false);
      }
    };

    fetchData();
  }, []);

  // Handle loading config photo
  const handleLoadConfigPhoto = async () => {
    setIsLoadingPhoto(true);
    setConfigPhotoUrl(null);
    
    try {
      const blob = await cameraAPI.getConfigSnapshot();
      const url = URL.createObjectURL(blob);
      setConfigPhotoUrl(url);
      setIsLoadingPhoto(false);
    } catch (error: any) {
      console.error('Error loading config photo:', error);
      setSnackbar({
        open: true,
        message: error.response?.data?.error || 'Nie udało się załadować zdjęcia konfiguracyjnego',
        severity: 'error',
      });
      setIsLoadingPhoto(false);
    }
  };

  // Note: Cleanup blob URL is now handled in ConfigContext

  const handleAccordionChange = (panel: string) => (_event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpanded(isExpanded ? panel : false);
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      // Convert to API format
      const payload = {
        schedule: settings.schedule, // Weekly schedule object
        blur_faces: settings.blurFaces,
        confidence_threshold: settings.confidenceThreshold / 100, // Convert 0-100 to 0-1
        anonymization_percent: settings.anonymizationPercent,
        camera_index: settings.cameraIndex,
        camera_name: settings.cameraName,
        notifications: {
          email: settings.emailEnabled,
          sms: settings.smsEnabled,
        },
        ...(settings.roi ? { roi_coordinates: settings.roi } : {}),
      };

      console.log('💾 Saving settings:', payload);
      const response = await settingsAPI.update(payload);
      
      // Update camera status from response
      if (response.camera_status) {
        setCameraStatus({
          isRunning: response.camera_status.is_running,
          withinSchedule: response.camera_status.within_schedule,
        });
      }

      setSnackbar({
        open: true,
        message: 'Settings saved successfully! 🎉',
        severity: 'success',
      });
    } catch (error) {
      console.error('Error saving settings:', error);
      setSnackbar({
        open: true,
        message: 'Error saving settings. Please try again.',
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  // ROI drawing helpers
  const getRelativeCoords = (e: React.MouseEvent) => {
    const rect = wrapperRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0, width: 0, height: 0 };
    const x = Math.min(Math.max(e.clientX - rect.left, 0), rect.width);
    const y = Math.min(Math.max(e.clientY - rect.top, 0), rect.height);
    return { x, y, width: rect.width, height: rect.height };
  };

  // Check if point is inside ROI
  const isPointInROI = (x: number, y: number, roi: ROIZone, width: number, height: number): boolean => {
    const roiX = roi.coords.x * width;
    const roiY = roi.coords.y * height;
    const roiW = roi.coords.w * width;
    const roiH = roi.coords.h * height;
    return x >= roiX && x <= roiX + roiW && y >= roiY && y <= roiY + roiH;
  };

  // Check if point is in resize handle
  const getResizeHandle = (x: number, y: number, roi: ROIZone, width: number, height: number): 'nw' | 'ne' | 'sw' | 'se' | null => {
    const handleSize = 8;
    const roiX = roi.coords.x * width;
    const roiY = roi.coords.y * height;
    const roiW = roi.coords.w * width;
    const roiH = roi.coords.h * height;

    // Check corners
    if (Math.abs(x - roiX) < handleSize && Math.abs(y - roiY) < handleSize) return 'nw';
    if (Math.abs(x - (roiX + roiW)) < handleSize && Math.abs(y - roiY) < handleSize) return 'ne';
    if (Math.abs(x - roiX) < handleSize && Math.abs(y - (roiY + roiH)) < handleSize) return 'sw';
    if (Math.abs(x - (roiX + roiW)) < handleSize && Math.abs(y - (roiY + roiH)) < handleSize) return 'se';
    
    return null;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!wrapperRef.current) return;
    
    const { x, y, width, height } = getRelativeCoords(e);
    
    // Check if clicking on a resize handle
    if (selectedROIId) {
      const selectedROI = savedROIs.find(r => r.id === selectedROIId);
      if (selectedROI) {
        const handle = getResizeHandle(x, y, selectedROI, width, height);
        if (handle) {
          e.preventDefault();
          setIsResizing(true);
          setResizeHandle(handle);
          setResizeStart({ x, y, coords: { ...selectedROI.coords } });
          return;
        }
      }
    }
    
    // Check if clicking on an existing ROI
    let clickedROI: ROIZone | null = null;
    for (const roi of savedROIs) {
      if (isPointInROI(x, y, roi, width, height)) {
        clickedROI = roi;
        break;
      }
    }
    
    if (drawingMode === 'none' || drawingMode === 'edit') {
      if (clickedROI) {
        e.preventDefault();
        setSelectedROIId(clickedROI.id);
        setIsDragging(true);
        setDragStart({ x, y });
        return;
      } else {
        setSelectedROIId(null);
      }
    }
    
    // Start drawing new ROI (only if not in edit mode and not clicking on existing ROI)
    if ((drawingMode === 'single' || drawingMode === 'grid') && !clickedROI) {
      setIsDrawing(true);
      setDrawStart({ x, y });
      setDrawEnd({ x, y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!wrapperRef.current) return;
    
    const { x, y, width, height } = getRelativeCoords(e);
    
    // Handle resizing
    if (isResizing && resizeHandle && resizeStart && selectedROIId) {
      const deltaX = (x - resizeStart.x) / width;
      const deltaY = (y - resizeStart.y) / height;
      const startCoords = resizeStart.coords;
      
      let newCoords = { ...startCoords };
      
      switch (resizeHandle) {
        case 'nw':
          newCoords.x = Math.max(0, Math.min(1, startCoords.x + deltaX));
          newCoords.y = Math.max(0, Math.min(1, startCoords.y + deltaY));
          newCoords.w = Math.max(0.01, startCoords.w - deltaX);
          newCoords.h = Math.max(0.01, startCoords.h - deltaY);
          break;
        case 'ne':
          newCoords.y = Math.max(0, Math.min(1, startCoords.y + deltaY));
          newCoords.w = Math.max(0.01, startCoords.w + deltaX);
          newCoords.h = Math.max(0.01, startCoords.h - deltaY);
          break;
        case 'sw':
          newCoords.x = Math.max(0, Math.min(1, startCoords.x + deltaX));
          newCoords.w = Math.max(0.01, startCoords.w - deltaX);
          newCoords.h = Math.max(0.01, startCoords.h + deltaY);
          break;
        case 'se':
          newCoords.w = Math.max(0.01, startCoords.w + deltaX);
          newCoords.h = Math.max(0.01, startCoords.h + deltaY);
          break;
      }
      
      // Ensure coordinates stay within bounds
      newCoords.x = Math.max(0, Math.min(1, newCoords.x));
      newCoords.y = Math.max(0, Math.min(1, newCoords.y));
      newCoords.w = Math.max(0.01, Math.min(1 - newCoords.x, newCoords.w));
      newCoords.h = Math.max(0.01, Math.min(1 - newCoords.y, newCoords.h));
      
      setSavedROIs(savedROIs.map(roi => 
        roi.id === selectedROIId ? { ...roi, coords: newCoords } : roi
      ));
      return;
    }
    
    // Handle dragging
    if (isDragging && dragStart && selectedROIId) {
      const deltaX = (x - dragStart.x) / width;
      const deltaY = (y - dragStart.y) / height;
      
      const selectedROI = savedROIs.find(r => r.id === selectedROIId);
      if (selectedROI) {
        let newX = selectedROI.coords.x + deltaX;
        let newY = selectedROI.coords.y + deltaY;
        
        // Keep within bounds
        newX = Math.max(0, Math.min(1 - selectedROI.coords.w, newX));
        newY = Math.max(0, Math.min(1 - selectedROI.coords.h, newY));
        
        setSavedROIs(savedROIs.map(roi => 
          roi.id === selectedROIId 
            ? { ...roi, coords: { ...roi.coords, x: newX, y: newY } }
            : roi
        ));
        setDragStart({ x, y });
      }
      return;
    }
    
    // Handle drawing new ROI
    if (isDrawing && drawStart && (drawingMode === 'single' || drawingMode === 'grid')) {
      setDrawEnd({ x, y });
    }
  };

  const handleMouseUp = (e: React.MouseEvent) => {
    if (isResizing) {
      setIsResizing(false);
      setResizeHandle(null);
      setResizeStart(null);
      return;
    }
    
    if (isDragging) {
      setIsDragging(false);
      setDragStart(null);
      return;
    }
    
    if (!isDrawing || !drawStart || !drawEnd || (drawingMode !== 'single' && drawingMode !== 'grid') || !wrapperRef.current) return;
    
    const { width, height } = wrapperRef.current.getBoundingClientRect();
    if (width === 0 || height === 0) return;

    const x1 = Math.min(drawStart.x, drawEnd.x) / width;
    const y1 = Math.min(drawStart.y, drawEnd.y) / height;
    const x2 = Math.max(drawStart.x, drawEnd.x) / width;
    const y2 = Math.max(drawStart.y, drawEnd.y) / height;

    // Normalize coordinates (0-1)
    const normalizedRect = {
      x: Math.max(0, Math.min(1, x1)),
      y: Math.max(0, Math.min(1, y1)),
      w: Math.max(0, Math.min(1, x2 - x1)),
      h: Math.max(0, Math.min(1, y2 - y1)),
    };

    if (normalizedRect.w < 0.01 || normalizedRect.h < 0.01) {
      // Too small, ignore
      setIsDrawing(false);
      setDrawStart(null);
      setDrawEnd(null);
      return;
    }

    setIsDrawing(false);

    if (drawingMode === 'single') {
      setCurrentRect(normalizedRect);
      setPendingZoneName('');
    } else if (drawingMode === 'grid') {
      setGridGeneratorRect(normalizedRect);
    }
  };

  const handleSaveSingleROI = () => {
    if (!currentRect || !pendingZoneName.trim()) {
      setSnackbar({
        open: true,
        message: 'Proszę podać nazwę strefy',
        severity: 'info',
      });
      return;
    }

    const newZone: ROIZone = {
      id: `zone_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      name: pendingZoneName.trim(),
      coords: currentRect,
    };

    setSavedROIs([...savedROIs, newZone]);
    setCurrentRect(null);
    setPendingZoneName('');
    setDrawingMode('none');
  };

  const handleGenerateGrid = () => {
    if (!gridGeneratorRect || numRows < 1 || numCols < 1) {
      setSnackbar({
        open: true,
        message: 'Proszę narysować prostokąt i podać liczbę rzędów i kolumn',
        severity: 'info',
      });
      return;
    }

    const newZones: ROIZone[] = [];
    const cellWidth = gridGeneratorRect.w / numCols;
    const cellHeight = gridGeneratorRect.h / numRows;
    
    // Counter for sequential naming mode - start from existing ROIs count + 1
    let counter = savedROIs.length + 1;
    
    // Get prefix from text field (e.g. 'ławka')
    const prefix = gridPrefix.trim();
    const prefixText = prefix ? `${prefix} ` : ''; // Add space if prefix is not empty

    for (let r = 0; r < numRows; r++) {
      for (let c = 0; c < numCols; c++) {
        const cellX = gridGeneratorRect.x + (c * cellWidth);
        const cellY = gridGeneratorRect.y + (r * cellHeight);
        
        // Generate name based on naming mode
        let name: string;
        if (gridNamingMode === 'sequential') {
          // Sequential mode: "Ławka 1", "Ławka 2", etc.
          name = `${prefixText}${counter}`;
          counter++;
        } else {
          // Grid mode: "R1-M1" or "M1-R1" based on naming order
          if (gridNamingOrder === 'rows-cols') {
            name = `R${r + 1}-M${c + 1}`;
          } else {
            name = `M${c + 1}-R${r + 1}`;
          }
          
          // Add prefix if provided
          if (gridPrefix.trim()) {
            name = `${gridPrefix.trim()}-${name}`;
          }
        }
        
        newZones.push({
          id: `grid-${r}-${c}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          name: name,
          coords: {
            x: cellX,
            y: cellY,
            w: cellWidth,
            h: cellHeight,
          },
        });
      }
    }

    setSavedROIs([...savedROIs, ...newZones]);
    setGridGeneratorRect(null);
    setNumRows(4);
    setNumCols(5);
    setGridPrefix('');
    setDrawingMode('none');
    
    setSnackbar({
      open: true,
      message: `Utworzono siatkę ${numRows}x${numCols} (${numRows * numCols} stref)`,
      severity: 'success',
    });
  };

  const handleDeleteROI = (id: string) => {
    setSavedROIs(savedROIs.filter(zone => zone.id !== id));
  };

  const handleEditROI = (id: string) => {
    const zone = savedROIs.find(z => z.id === id);
    if (zone) {
      setEditingZoneId(id);
      setEditingZoneName(zone.name);
    }
  };

  const handleSaveEditROI = () => {
    if (!editingZoneId || !editingZoneName.trim()) return;
    
    setSavedROIs(savedROIs.map(zone =>
      zone.id === editingZoneId
        ? { ...zone, name: editingZoneName.trim() }
        : zone
    ));
    setEditingZoneId(null);
    setEditingZoneName('');
  };

  const handleSaveROIsToBackend = async () => {
    setLoading(true);
    try {
      await settingsAPI.saveROIZones(savedROIs);
      setSnackbar({
        open: true,
        message: 'Strefy ROI zapisane pomyślnie! 🎉',
        severity: 'success',
      });
    } catch (error: any) {
      console.error('Error saving ROI zones:', error);
      setSnackbar({
        open: true,
        message: error.response?.data?.error || 'Błąd podczas zapisywania stref ROI',
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  // Autosave function with debounce
  const lastSavedROIsRef = useRef<ROIZone[]>([]);
  useEffect(() => {
    // Skip autosave on initial load
    if (initialLoad) {
      lastSavedROIsRef.current = savedROIs;
      return;
    }

    // Skip if nothing changed
    if (JSON.stringify(lastSavedROIsRef.current) === JSON.stringify(savedROIs)) {
      return;
    }

    // Clear existing timeout
    if (autosaveTimeoutRef.current) {
      clearTimeout(autosaveTimeoutRef.current);
    }

    // Set new timeout for autosave
    autosaveTimeoutRef.current = setTimeout(async () => {
      try {
        await settingsAPI.saveROIZones(savedROIs);
        lastSavedROIsRef.current = savedROIs;
        // Show subtle autosave notification (only when actually saved)
        setSnackbar({
          open: true,
          message: 'Ustawienia zapisane automatycznie',
          severity: 'success',
          autoHideDuration: 1500,
        } as typeof snackbar);
      } catch (error) {
        console.error('Autosave error:', error);
        // Don't show error for autosave failures
      }
    }, 2000); // 2 second delay

    // Cleanup
    return () => {
      if (autosaveTimeoutRef.current) {
        clearTimeout(autosaveTimeoutRef.current);
      }
    };
  }, [savedROIs, initialLoad]);

  const handleResetAllROIs = () => {
    setSavedROIs([]);
    setSelectedROIId(null);
    setResetDialogOpen(false);
    setSnackbar({
      open: true,
      message: 'Wszystkie strefy zostały usunięte',
      severity: 'info',
    });
  };

  const handleCameraChange = (cameraIndex: number) => {
    const selectedCamera = availableCameras.find((cam) => cam.index === cameraIndex);
    if (selectedCamera) {
      setSettings({
        ...settings,
        cameraIndex: selectedCamera.index,
        cameraName: selectedCamera.name,
      });
    }
  };

  const handleReset = () => {
    setSettings({
      schedule: DEFAULT_SCHEDULE,
      blurFaces: true,
      anonymizationPercent: 50,
      emailEnabled: true,
      smsEnabled: false,
      confidenceThreshold: 20,
      cameraIndex: 0,
      cameraName: 'Camera 1',
      roi: null,
    });
    setSnackbar({
      open: true,
      message: 'Settings reset to defaults',
      severity: 'info',
    });
  };

  const handleStartCamera = async () => {
    setCameraLoading(true);
    try {
      console.log('🚀 Starting camera...');
      const response = await cameraAPI.start();
      setCameraStatus({
        isRunning: response.camera_status.is_running,
        withinSchedule: response.camera_status.within_schedule,
      });
      setSnackbar({
        open: true,
        message: 'Camera started successfully! 📹',
        severity: 'success',
      });
    } catch (error) {
      console.error('Error starting camera:', error);
      setSnackbar({
        open: true,
        message: 'Failed to start camera',
        severity: 'error',
      });
    } finally {
      setCameraLoading(false);
    }
  };

  const handleStopCamera = async () => {
    setCameraLoading(true);
    try {
      console.log('🛑 Stopping camera...');
      const response = await cameraAPI.stop();
      setCameraStatus({
        isRunning: response.camera_status.is_running,
        withinSchedule: response.camera_status.within_schedule,
      });
      setSnackbar({
        open: true,
        message: 'Camera stopped successfully! 🛑',
        severity: 'info',
      });
    } catch (error) {
      console.error('Error stopping camera:', error);
      setSnackbar({
        open: true,
        message: 'Failed to stop camera',
        severity: 'error',
      });
    } finally {
      setCameraLoading(false);
    }
  };

  // ✅ Schedule Quick Select Handlers
  const handleSet247 = () => {
    const schedule24_7: WeeklySchedule = {
      monday: { enabled: true, start: '00:00', end: '23:59' },
      tuesday: { enabled: true, start: '00:00', end: '23:59' },
      wednesday: { enabled: true, start: '00:00', end: '23:59' },
      thursday: { enabled: true, start: '00:00', end: '23:59' },
      friday: { enabled: true, start: '00:00', end: '23:59' },
      saturday: { enabled: true, start: '00:00', end: '23:59' },
      sunday: { enabled: true, start: '00:00', end: '23:59' },
    };
    
    setSettings({
      ...settings,
      schedule: schedule24_7,
    });
    
    setSnackbar({
      open: true,
      message: '24/7 schedule set (all days 00:00 - 23:59)',
      severity: 'info',
    });
  };

  const handleSetBusinessHours = () => {
    const scheduleBusiness: WeeklySchedule = {
      monday: { enabled: true, start: '07:00', end: '16:00' },
      tuesday: { enabled: true, start: '07:00', end: '16:00' },
      wednesday: { enabled: true, start: '07:00', end: '16:00' },
      thursday: { enabled: true, start: '07:00', end: '16:00' },
      friday: { enabled: true, start: '07:00', end: '16:00' },
      saturday: { enabled: false, start: '07:00', end: '16:00' },
      sunday: { enabled: false, start: '07:00', end: '16:00' },
    };
    
    setSettings({
      ...settings,
      schedule: scheduleBusiness,
    });
    
    setSnackbar({
      open: true,
      message: 'Business Hours schedule set (Mon-Fri 07:00 - 16:00, weekends off)',
      severity: 'info',
    });
  };

  const handleSetNightOnly = () => {
    const scheduleNight: WeeklySchedule = {
      monday: { enabled: true, start: '22:00', end: '06:00' },
      tuesday: { enabled: true, start: '22:00', end: '06:00' },
      wednesday: { enabled: true, start: '22:00', end: '06:00' },
      thursday: { enabled: true, start: '22:00', end: '06:00' },
      friday: { enabled: true, start: '22:00', end: '06:00' },
      saturday: { enabled: false, start: '22:00', end: '06:00' },
      sunday: { enabled: false, start: '22:00', end: '06:00' },
    };
    
    setSettings({
      ...settings,
      schedule: scheduleNight,
    });
    
    setSnackbar({
      open: true,
      message: 'Night Only schedule set (Mon-Fri 22:00 - 06:00, weekends off)',
      severity: 'info',
    });
  };
  
  // Helper to update a single day's schedule
  const updateDaySchedule = (day: keyof WeeklySchedule, field: keyof DaySchedule, value: boolean | string) => {
    setSettings({
      ...settings,
      schedule: {
        ...settings.schedule,
        [day]: {
          ...settings.schedule[day],
          [field]: value,
        },
      },
    });
  };
  
  // Helper to convert time string (HH:MM) to Date for TimePicker
  const timeStringToDatePicker = (timeStr: string): Date => {
    const [hours, minutes] = timeStr.split(':').map(Number);
    const date = new Date();
    date.setHours(hours, minutes, 0, 0);
    return date;
  };
  
  // Helper to convert Date from TimePicker to time string (HH:MM)
  const datePickerToTimeString = (date: Date | null): string => {
    if (!date) return '00:00';
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
  };

  // Show loading spinner on initial load
  if (initialLoad) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '60vh',
        }}
      >
        <CircularProgress size={48} />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Paper
        sx={{
          p: 3,
          mb: 3,
          background: (theme) =>
            `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.05)} 0%, ${alpha(
              theme.palette.background.paper,
              1
            )} 100%)`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <SettingsIcon sx={{ fontSize: 32, color: 'primary.main' }} />
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                System Settings
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Configure your phone detection system
              </Typography>
            </Box>
          </Box>
          <Chip
            label={cameraStatus.isRunning ? 'Camera Online' : 'Camera Offline'}
            color={cameraStatus.isRunning ? 'success' : 'default'}
            variant="outlined"
            icon={cameraStatus.isRunning ? <Videocam /> : <VideocamOff />}
            sx={{ fontWeight: 600 }}
          />
        </Box>
      </Paper>

      {/* Camera Control Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Videocam sx={{ fontSize: 32, color: cameraStatus.isRunning ? 'success.main' : 'text.secondary' }} />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Camera Control
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Status: {cameraStatus.isRunning ? '🟢 Running' : '🔴 Stopped'}
                {cameraStatus.withinSchedule && ' (Within Schedule)'}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <LoadingButton
              variant="contained"
              color="success"
              startIcon={<PlayArrow />}
              onClick={handleStartCamera}
              loading={cameraLoading}
              disabled={cameraStatus.isRunning}
            >
              Start Camera
            </LoadingButton>
            <LoadingButton
              variant="contained"
              color="error"
              startIcon={<Stop />}
              onClick={handleStopCamera}
              loading={cameraLoading}
              disabled={!cameraStatus.isRunning}
            >
              Stop Camera
            </LoadingButton>
          </Box>
        </Box>
      </Paper>

      {/* Camera Schedule Section */}
      <Accordion
        expanded={expanded === 'schedule'}
        onChange={handleAccordionChange('schedule')}
        sx={{ mb: 2 }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Schedule color="primary" />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Camera Schedule
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Set active monitoring hours
              </Typography>
            </Box>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Stack spacing={2}>
            {/* Preset buttons */}
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Chip 
                label="24/7" 
                size="small" 
                variant="outlined" 
                clickable 
                onClick={handleSet247}
                icon={<Schedule fontSize="small" />}
              />
              <Chip 
                label="Business Hours (Mon-Fri 7-16)" 
                size="small" 
                variant="outlined" 
                clickable 
                onClick={handleSetBusinessHours}
                icon={<WbTwilight fontSize="small" />}
              />
              <Chip 
                label="Night Only (Mon-Fri 22-06)" 
                size="small" 
                variant="outlined" 
                clickable 
                onClick={handleSetNightOnly}
                icon={<Brightness4 fontSize="small" />}
              />
            </Stack>
            
            <Divider />
            
            {/* 7-day schedule grid */}
            <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={pl}>
              <Grid container spacing={2}>
                {(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] as const).map((day) => {
                  const dayConfig = settings.schedule[day];
                  const dayLabel = day.charAt(0).toUpperCase() + day.slice(1);
                  
                  return (
                    <Grid item xs={12} key={day}>
                      <Paper variant="outlined" sx={{ p: 2 }}>
                        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
                          {/* Checkbox for enabled */}
                          <Checkbox
                            checked={dayConfig.enabled}
                            onChange={(e) => updateDaySchedule(day, 'enabled', e.target.checked)}
                            size="small"
                          />
                          
                          {/* Day label */}
                          <Typography variant="body2" sx={{ minWidth: 80, fontWeight: 500 }}>
                            {dayLabel}
                          </Typography>
                          
                          {/* Start time picker */}
                          <TimePicker
                            label="Start"
                            value={timeStringToDatePicker(dayConfig.start)}
                            onChange={(newValue) => {
                              if (newValue) {
                                updateDaySchedule(day, 'start', datePickerToTimeString(newValue));
                              }
                            }}
                            disabled={!dayConfig.enabled}
                            slotProps={{
                              textField: {
                                size: 'small',
                                sx: { width: 120 },
                              },
                            }}
                          />
                          
                          <Typography variant="body2" color="text.secondary">
                            to
                          </Typography>
                          
                          {/* End time picker */}
                          <TimePicker
                            label="End"
                            value={timeStringToDatePicker(dayConfig.end)}
                            onChange={(newValue) => {
                              if (newValue) {
                                updateDaySchedule(day, 'end', datePickerToTimeString(newValue));
                              }
                            }}
                            disabled={!dayConfig.enabled}
                            slotProps={{
                              textField: {
                                size: 'small',
                                sx: { width: 120 },
                              },
                            }}
                          />
                        </Stack>
                      </Paper>
                    </Grid>
                  );
                })}
              </Grid>
            </LocalizationProvider>
          </Stack>
        </AccordionDetails>
      </Accordion>

      {/* Detection Settings Section */}
      <Accordion
        expanded={expanded === 'detection'}
        onChange={handleAccordionChange('detection')}
        sx={{ mb: 2 }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Tune color="primary" />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Detection Settings
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Adjust detection threshold and mode
              </Typography>
            </Box>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <FormControl fullWidth>
            <FormLabel sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  Confidence Threshold
                </Typography>
                <Chip
                  label={`${settings.confidenceThreshold}%`}
                  size="small"
                  color={
                    settings.confidenceThreshold > 60
                      ? 'success'
                      : settings.confidenceThreshold > 30
                      ? 'warning'
                      : 'error'
                  }
                  sx={{ fontWeight: 600 }}
                />
              </Box>
            </FormLabel>
            <Slider
              value={settings.confidenceThreshold}
              onChange={(_e, value) =>
                setSettings({ ...settings, confidenceThreshold: value as number })
              }
              valueLabelDisplay="auto"
              marks={confidenceMarks}
              min={0}
              max={100}
              sx={{ mb: 1 }}
            />
            <FormHelperText sx={{ mt: 2, mb: 4 }}>
              Wyższy próg = mniej fałszywych alarmów, ale ryzyko pominięcia. Niższy próg = bardziej czuły.
            </FormHelperText>
          </FormControl>
          <Divider sx={{ my: 3 }} />
          <Stack direction="row" spacing={1}>
            <Chip label="Czuły (więcej detekcji)" size="small" variant="outlined" clickable onClick={() => setSettings({ ...settings, confidenceThreshold: 30 })} />
            <Chip label="Zbalansowany (zalecany)" size="small" variant="outlined" clickable onClick={() => setSettings({ ...settings, confidenceThreshold: 60 })} />
            <Chip label="Precyzyjny (mniej detekcji)" size="small" variant="outlined" clickable onClick={() => setSettings({ ...settings, confidenceThreshold: 85 })} />
          </Stack>
        </AccordionDetails>
      </Accordion>

      {/* ================================================================== */}
      {/* NOWA SEKCJA ROI - System Stref */}
      {/* ================================================================== */}
      <Accordion
        expanded={isRoiExpanded}
        sx={{ mb: 2 }}
        onChange={(_e, isExpanded) => {
          setIsRoiExpanded(isExpanded);
        }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <FilterCenterFocus sx={{ mr: 1, color: 'text.secondary' }} />
          <Typography>Definiowanie Stref ROI</Typography>
          {savedROIs.length > 0 && (
            <Chip
              label={`${savedROIs.length} stref`}
              size="small"
              sx={{ ml: 2 }}
              color="primary"
            />
          )}
        </AccordionSummary>
        <AccordionDetails>
          <Stack spacing={3}>
            <Typography variant="body2" color="text.secondary">
              Załaduj obraz konfiguracyjny sali, a następnie użyj narzędzi do definiowania stref. Możesz rysować pojedyncze strefy lub generować siatkę (grid) automatycznie.
            </Typography>

            {/* Przycisk do ładowania zdjęcia */}
            {!configPhotoUrl && !isLoadingPhoto && (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<Camera />}
                  onClick={handleLoadConfigPhoto}
                  disabled={!cameraStatus.isRunning}
                >
                  Załaduj Obraz Konfiguracyjny
                </Button>
              </Box>
            )}

            {/* Loading indicator */}
            {isLoadingPhoto && (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            )}

            {/* Panel narzędzi i obraz konfiguracyjny */}
            {configPhotoUrl && (
              <Grid container spacing={2}>
                {/* Panel narzędzi */}
                <Grid item xs={12} md={3}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="h6" sx={{ mb: 2, fontSize: '1rem' }}>
                      Narzędzia
                    </Typography>
                    <Stack spacing={2}>
                      <Button
                        variant={drawingMode === 'single' ? 'contained' : 'outlined'}
                        fullWidth
                        startIcon={<Add />}
                        onClick={() => {
                          setDrawingMode('single');
                          setCurrentRect(null);
                          setGridGeneratorRect(null);
                          setSelectedROIId(null);
                        }}
                      >
                        Rysuj Pojedynczą Strefę
                      </Button>
                      <Button
                        variant={drawingMode === 'grid' ? 'contained' : 'outlined'}
                        fullWidth
                        startIcon={<Add />}
                        onClick={() => {
                          setDrawingMode('grid');
                          setCurrentRect(null);
                          setGridGeneratorRect(null);
                          setSelectedROIId(null);
                        }}
                      >
                        Generuj Siatkę (Grid)
                      </Button>
                      <Button
                        variant={drawingMode === 'edit' ? 'contained' : 'outlined'}
                        fullWidth
                        startIcon={<Edit />}
                        onClick={() => {
                          setDrawingMode('edit');
                          setCurrentRect(null);
                          setGridGeneratorRect(null);
                        }}
                      >
                        Tryb Edycji
                      </Button>
                      <Button
                        variant="outlined"
                        fullWidth
                        onClick={() => {
                          setDrawingMode('none');
                          setCurrentRect(null);
                          setGridGeneratorRect(null);
                          setSelectedROIId(null);
                        }}
                      >
                        Anuluj
                      </Button>
                    </Stack>

                    {/* Formularz dla pojedynczej strefy */}
                    {currentRect && drawingMode === 'single' && (
                      <Box sx={{ mt: 3, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>
                          Zapisz Pojedynczą Strefę
                        </Typography>
                        <TextField
                          fullWidth
                          size="small"
                          label="Nazwa strefy"
                          value={pendingZoneName}
                          onChange={(e) => setPendingZoneName(e.target.value)}
                          placeholder="np. Biurko 1"
                          sx={{ mb: 2 }}
                        />
                        <Button
                          variant="contained"
                          fullWidth
                          onClick={handleSaveSingleROI}
                          disabled={!pendingZoneName.trim()}
                        >
                          Zapisz Strefę
                        </Button>
                      </Box>
                    )}

                    {/* Formularz dla generatora siatki */}
                    {gridGeneratorRect && drawingMode === 'grid' && (
                      <Box sx={{ mt: 3, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                        <Typography variant="subtitle2" sx={{ mb: 2 }}>
                          Konfiguracja Siatki
                        </Typography>
                        <TextField
                          fullWidth
                          size="small"
                          type="number"
                          label="Liczba Rzędów"
                          value={numRows}
                          onChange={(e) => setNumRows(Math.max(1, parseInt(e.target.value) || 1))}
                          inputProps={{ min: 1, max: 50 }}
                          sx={{ mb: 2 }}
                        />
                        <TextField
                          fullWidth
                          size="small"
                          type="number"
                          label="Liczba Kolumn"
                          value={numCols}
                          onChange={(e) => setNumCols(Math.max(1, parseInt(e.target.value) || 1))}
                          inputProps={{ min: 1, max: 50 }}
                          sx={{ mb: 2 }}
                        />
                        <FormControl component="fieldset" sx={{ mb: 2 }}>
                          <FormLabel component="legend">Tryb Nazywania</FormLabel>
                          <RadioGroup
                            row
                            value={gridNamingMode}
                            onChange={(e) => setGridNamingMode(e.target.value as 'sequential' | 'grid')}
                          >
                            <FormControlLabel 
                              value="sequential" 
                              control={<Radio />} 
                              label="Kolejno (np. Ławka 1, 2, 3)" 
                            />
                            <FormControlLabel 
                              value="grid" 
                              control={<Radio />} 
                              label="Siatka (np. R1-M1)" 
                            />
                          </RadioGroup>
                        </FormControl>
                        <TextField
                          fullWidth
                          size="small"
                          label="Prefiks nazwy strefy (opcjonalnie)"
                          value={gridPrefix}
                          onChange={(e) => setGridPrefix(e.target.value)}
                          placeholder={gridNamingMode === 'sequential' ? 'np. Ławka' : 'np. ławka'}
                          sx={{ mb: 2 }}
                        />
                        {gridNamingMode === 'grid' && (
                          <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                            <InputLabel>Kolejność nazewnictwa</InputLabel>
                            <Select
                              value={gridNamingOrder}
                              label="Kolejność nazewnictwa"
                              onChange={(e) => setGridNamingOrder(e.target.value as 'rows-cols' | 'cols-rows')}
                            >
                              <MenuItem value="rows-cols">Rzędy x Kolumny (R1-M1, R1-M2...)</MenuItem>
                              <MenuItem value="cols-rows">Kolumny x Rzędy (M1-R1, M1-R2...)</MenuItem>
                            </Select>
                          </FormControl>
                        )}
                        <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
                          Utworzy {numRows * numCols} stref
                          {gridNamingMode === 'sequential' ? (
                            <>
                              {gridPrefix.trim() 
                                ? ` (${gridPrefix.trim()} 1, ${gridPrefix.trim()} 2, ..., ${gridPrefix.trim()} ${numRows * numCols})`
                                : ` (1, 2, ..., ${numRows * numCols})`}
                            </>
                          ) : (
                            <>
                              {gridPrefix.trim() && ` z prefiksem "${gridPrefix.trim()}"`}
                              {gridNamingOrder === 'rows-cols' 
                                ? ` (R1-M1, R1-M2, ..., R${numRows}-M${numCols})`
                                : ` (M1-R1, M1-R2, ..., M${numCols}-R${numRows})`}
                            </>
                          )}
                        </Typography>
                        <Button
                          variant="contained"
                          fullWidth
                          onClick={handleGenerateGrid}
                          disabled={numRows < 1 || numCols < 1}
                          sx={{ mb: 1 }}
                        >
                          Zatwierdź Siatkę
                        </Button>
                      </Box>
                    )}

                    {/* Lista zapisanych stref */}
                    {savedROIs.length > 0 && (
                      <Box sx={{ mt: 3 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle2">
                            Zapisane Strefy ({savedROIs.length})
                          </Typography>
                          <Button
                            size="small"
                            color="error"
                            variant="outlined"
                            startIcon={<Delete />}
                            onClick={() => setResetDialogOpen(true)}
                          >
                            Resetuj Wszystkie
                          </Button>
                        </Box>
                        <Stack spacing={1}>
                          {savedROIs.map((zone) => (
                            <Paper
                              key={zone.id}
                              sx={{
                                p: 1.5,
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                bgcolor: editingZoneId === zone.id ? 'action.selected' : 'background.paper',
                              }}
                            >
                              {editingZoneId === zone.id ? (
                                <TextField
                                  size="small"
                                  value={editingZoneName}
                                  onChange={(e) => setEditingZoneName(e.target.value)}
                                  onKeyPress={(e) => {
                                    if (e.key === 'Enter') {
                                      handleSaveEditROI();
                                    }
                                  }}
                                  autoFocus
                                  sx={{ flex: 1, mr: 1 }}
                                />
                              ) : (
                                <Typography variant="body2" sx={{ flex: 1 }}>
                                  {zone.name}
                                </Typography>
                              )}
                              <Box>
                                {editingZoneId === zone.id ? (
                                  <IconButton
                                    size="small"
                                    onClick={handleSaveEditROI}
                                    color="primary"
                                  >
                                    <Save />
                                  </IconButton>
                                ) : (
                                  <>
                                    <IconButton
                                      size="small"
                                      onClick={() => handleEditROI(zone.id)}
                                      color="primary"
                                    >
                                      <Edit fontSize="small" />
                                    </IconButton>
                                    <IconButton
                                      size="small"
                                      onClick={() => handleDeleteROI(zone.id)}
                                      color="error"
                                    >
                                      <Delete fontSize="small" />
                                    </IconButton>
                                  </>
                                )}
                              </Box>
                            </Paper>
                          ))}
                        </Stack>
                      </Box>
                    )}
                  </Paper>
                </Grid>

                {/* Obraz konfiguracyjny z rysowaniem */}
                <Grid item xs={12} md={9}>
                  <Box
                    ref={wrapperRef}
              sx={{
                position: 'relative',
                cursor: isDragging ? 'move' : isResizing ? (resizeHandle === 'nw' || resizeHandle === 'se' ? 'nwse-resize' : 'nesw-resize') : (drawingMode !== 'none' && drawingMode !== 'edit' ? 'crosshair' : 'default'),
                width: '100%',
                border: (theme) => `1px solid ${theme.palette.divider}`,
                overflow: 'hidden',
              }}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
              onMouseLeave={() => {
                if (isDrawing) {
                  setIsDrawing(false);
                  setDrawStart(null);
                  setDrawEnd(null);
                }
                if (isDragging) {
                  setIsDragging(false);
                  setDragStart(null);
                }
                if (isResizing) {
                  setIsResizing(false);
                  setResizeHandle(null);
                  setResizeStart(null);
                }
              }}
            >
                    {/* Statyczny obraz konfiguracyjny */}
                  <img
                      ref={imgRef}
                      src={configPhotoUrl}
                      alt="Podgląd Sali"
                    style={{
                      width: '100%',
                      height: 'auto',
                      display: 'block',
                      pointerEvents: 'none',
                    }}
                  />

              {/* Narysowany prostokąt (w trakcie) */}
                    {isDrawing && drawStart && drawEnd && wrapperRef.current && (
                <div
                  style={{
                    position: 'absolute',
                    border: '2px dashed #00bfff',
                          backgroundColor: 'rgba(0, 191, 255, 0.1)',
                    left: Math.min(drawStart.x, drawEnd.x),
                    top: Math.min(drawStart.y, drawEnd.y),
                    width: Math.abs(drawStart.x - drawEnd.x),
                    height: Math.abs(drawStart.y - drawEnd.y),
                    pointerEvents: 'none',
                  }}
                />
              )}

                    {/* Zapisane strefy ROI */}
                    {wrapperRef.current && savedROIs.map((zone) => {
                      const rect = wrapperRef.current?.getBoundingClientRect();
                      if (!rect) return null;
                      const isSelected = selectedROIId === zone.id;
                      const canEdit = drawingMode === 'edit' || drawingMode === 'none';
                      const roiX = zone.coords.x * rect.width;
                      const roiY = zone.coords.y * rect.height;
                      const roiW = zone.coords.w * rect.width;
                      const roiH = zone.coords.h * rect.height;
                      
                      return (
                        <div
                          key={zone.id}
                          style={{
                            position: 'absolute',
                            border: isSelected ? '3px solid #ffc107' : '2px solid #4caf50',
                            backgroundColor: isSelected ? 'rgba(255, 193, 7, 0.3)' : 'rgba(76, 175, 80, 0.2)',
                            left: roiX,
                            top: roiY,
                            width: roiW,
                            height: roiH,
                            pointerEvents: canEdit ? 'auto' : 'none',
                            cursor: canEdit ? (isSelected ? 'move' : 'pointer') : 'default',
                          }}
                        >
                          <Typography
                            variant="caption"
                            sx={{
                              position: 'absolute',
                              top: -24,
                              left: 0,
                              bgcolor: isSelected ? 'rgba(255, 193, 7, 0.95)' : 'rgba(76, 175, 80, 0.9)',
                              color: 'white',
                              px: 0.5,
                              borderRadius: 0.5,
                              fontSize: '0.7rem',
                              whiteSpace: 'nowrap',
                              fontWeight: isSelected ? 600 : 400,
                            }}
                          >
                            {zone.name}
                          </Typography>
                          
                          {/* Resize handles */}
                          {isSelected && canEdit && (
                            <>
                              {/* NW corner */}
                              <div
                                style={{
                                  position: 'absolute',
                                  left: -4,
                                  top: -4,
                                  width: 8,
                                  height: 8,
                                  backgroundColor: '#ffc107',
                                  border: '2px solid white',
                                  borderRadius: '50%',
                                  cursor: 'nw-resize',
                                }}
                              />
                              {/* NE corner */}
                              <div
                                style={{
                                  position: 'absolute',
                                  right: -4,
                                  top: -4,
                                  width: 8,
                                  height: 8,
                                  backgroundColor: '#ffc107',
                                  border: '2px solid white',
                                  borderRadius: '50%',
                                  cursor: 'ne-resize',
                                }}
                              />
                              {/* SW corner */}
                              <div
                                style={{
                                  position: 'absolute',
                                  left: -4,
                                  bottom: -4,
                                  width: 8,
                                  height: 8,
                                  backgroundColor: '#ffc107',
                                  border: '2px solid white',
                                  borderRadius: '50%',
                                  cursor: 'sw-resize',
                                }}
                              />
                              {/* SE corner */}
                              <div
                                style={{
                                  position: 'absolute',
                                  right: -4,
                                  bottom: -4,
                                  width: 8,
                                  height: 8,
                                  backgroundColor: '#ffc107',
                                  border: '2px solid white',
                                  borderRadius: '50%',
                                  cursor: 'se-resize',
                                }}
                              />
                            </>
                          )}
                        </div>
                      );
                    })}

                    {/* Podgląd prostokąta dla pojedynczej strefy */}
                    {currentRect && !isDrawing && wrapperRef.current && (
                      <div
                        style={{
                          position: 'absolute',
                          border: '2px solid #ff9800',
                          backgroundColor: 'rgba(255, 152, 0, 0.2)',
                          left: currentRect.x * wrapperRef.current.clientWidth,
                          top: currentRect.y * wrapperRef.current.clientHeight,
                          width: currentRect.w * wrapperRef.current.clientWidth,
                          height: currentRect.h * wrapperRef.current.clientHeight,
                    pointerEvents: 'none',
                  }}
                />
              )}

                    {/* Podgląd prostokąta dla generatora siatki */}
                    {gridGeneratorRect && !isDrawing && wrapperRef.current && (
                      <>
                        <div
                          style={{
                            position: 'absolute',
                            border: '2px solid #9c27b0',
                            backgroundColor: 'rgba(156, 39, 176, 0.2)',
                            left: gridGeneratorRect.x * wrapperRef.current.clientWidth,
                            top: gridGeneratorRect.y * wrapperRef.current.clientHeight,
                            width: gridGeneratorRect.w * wrapperRef.current.clientWidth,
                            height: gridGeneratorRect.h * wrapperRef.current.clientHeight,
                            pointerEvents: 'none',
                          }}
                        />
                        {/* Podgląd siatki - linie pionowe */}
                        {Array.from({ length: numCols - 1 }).map((_, i) => {
                          const cellWidth = gridGeneratorRect.w / numCols;
                          return (
                            <div
                              key={`v-${i}`}
                              style={{
                                position: 'absolute',
                                borderLeft: '1px dashed #9c27b0',
                                left: (gridGeneratorRect.x + (i + 1) * cellWidth) * wrapperRef.current!.clientWidth,
                                top: gridGeneratorRect.y * wrapperRef.current!.clientHeight,
                                width: 1,
                                height: gridGeneratorRect.h * wrapperRef.current!.clientHeight,
                                pointerEvents: 'none',
                              }}
                            />
                          );
                        })}
                        {/* Podgląd siatki - linie poziome */}
                        {Array.from({ length: numRows - 1 }).map((_, i) => {
                          const cellHeight = gridGeneratorRect.h / numRows;
                          return (
                            <div
                              key={`h-${i}`}
                              style={{
                                position: 'absolute',
                                borderTop: '1px dashed #9c27b0',
                                left: gridGeneratorRect.x * wrapperRef.current!.clientWidth,
                                top: (gridGeneratorRect.y + (i + 1) * cellHeight) * wrapperRef.current!.clientHeight,
                                width: gridGeneratorRect.w * wrapperRef.current!.clientWidth,
                                height: 1,
                                pointerEvents: 'none',
                              }}
                            />
                          );
                        })}
                      </>
                    )}
            </Box>

                  {/* Przycisk do ponownego załadowania */}
                  <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                    <Button
                      variant="outlined"
                      startIcon={<Refresh />}
                      onClick={handleLoadConfigPhoto}
                      disabled={isLoadingPhoto || !cameraStatus.isRunning}
                    >
                      Załaduj ponownie
              </Button>
                  </Box>
                </Grid>
              </Grid>
            )}

            {/* Przycisk zapisu do backendu */}
            {savedROIs.length > 0 && (
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', pt: 2 }}>
                <LoadingButton
                  variant="contained"
                  size="large"
                  startIcon={<Save />}
                  loading={loading}
                  onClick={handleSaveROIsToBackend}
                >
                  Zapisz Ustawienia ROI
              </LoadingButton>
              </Box>
            )}
          </Stack>
        </AccordionDetails>
      </Accordion>

      {/* Privacy Settings Section */}
      <Accordion
        expanded={expanded === 'privacy'}
        onChange={handleAccordionChange('privacy')}
        sx={{ mb: 2 }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Security color="primary" />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Privacy Settings
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Control data privacy and protection
              </Typography>
            </Box>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <FormControlLabel
            control={
              <Switch
                checked={settings.blurFaces}
                onChange={(e) => setSettings({ ...settings, blurFaces: e.target.checked })}
              />
            }
            label={
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  Enable anonymization (blur)
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Automatically blur detected people to protect privacy
                </Typography>
              </Box>
            }
            sx={{ mb: 2 }}
          />
          <FormControl fullWidth sx={{ opacity: settings.blurFaces ? 1 : 0.5 }}>
            <FormLabel>Anonymization Area</FormLabel>
            <Slider
              disabled={!settings.blurFaces}
              value={settings.anonymizationPercent}
              onChange={(_e, value) => setSettings({ ...settings, anonymizationPercent: value as number })}
              min={10}
              max={100}
              step={5}
              valueLabelDisplay="auto"
              valueLabelFormat={(v) => `${v}%`}
              sx={{ mt: 1 }}
            />
            <FormHelperText>
              Ustaw, jak duża górna część sylwetki ma zostać rozmyta.
            </FormHelperText>
          </FormControl>
        </AccordionDetails>
      </Accordion>

      {/* Camera Selection Section */}
      <Accordion
        expanded={expanded === 'camera'}
        onChange={handleAccordionChange('camera')}
        sx={{ mb: 2 }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Camera color="primary" />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Camera Selection
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Choose your camera device (e.g., Irium, Webcam)
              </Typography>
            </Box>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <FormControl fullWidth>
            <InputLabel id="camera-select-label">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Videocam fontSize="small" />
                Select Camera Device
              </Box>
            </InputLabel>
            <Select
              labelId="camera-select-label"
              value={settings.cameraIndex}
              label="Select Camera Device"
              onChange={(e) => handleCameraChange(Number(e.target.value))}
              disabled={cameraStatus.isRunning}
            >
              {availableCameras.length > 0 ? (
                availableCameras.map((camera) => (
                  <MenuItem key={camera.index} value={camera.index}>
                    <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {camera.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {camera.resolution} • {camera.fps} FPS
                      </Typography>
                    </Box>
                  </MenuItem>
                ))
              ) : (
                <MenuItem disabled>
                  <Typography variant="body2" color="text.secondary">
                    {availableCameras.length === 0 ? 'Brak dostępnych kamer' : 'Loading cameras...'}
                  </Typography>
                </MenuItem>
              )}
            </Select>
            <FormHelperText>
              {cameraStatus.isRunning ? (
                <Typography variant="caption" color="warning.main">
                  ⚠️ Stop the camera before changing devices
                </Typography>
              ) : (
                <Typography variant="caption">
                  Current: {settings.cameraName} (Index: {settings.cameraIndex})
                </Typography>
              )}
            </FormHelperText>
          </FormControl>
        </AccordionDetails>
      </Accordion>

      {/* Notification Settings Section */}
      <Accordion
        expanded={expanded === 'notifications'}
        onChange={handleAccordionChange('notifications')}
        sx={{ mb: 2 }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <NotificationsActive color="primary" />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Notification Settings
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Configure alert channels and preferences
              </Typography>
            </Box>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Stack spacing={2}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.emailEnabled}
                  onChange={(e) => setSettings({ ...settings, emailEnabled: e.target.checked })}
                  color="primary"
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Email fontSize="small" color={settings.emailEnabled ? 'primary' : 'disabled'} />
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      Email Notifications
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Receive alerts via email
                    </Typography>
                  </Box>
                </Box>
              }
            />
            <FormControlLabel
              control={
                <Switch
                  checked={settings.smsEnabled}
                  onChange={(e) => setSettings({ ...settings, smsEnabled: e.target.checked })}
                  color="primary"
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Sms fontSize="small" color={settings.smsEnabled ? 'primary' : 'disabled'} />
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      SMS Notifications
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Receive alerts via text message
                    </Typography>
                  </Box>
                </Box>
              }
            />
          </Stack>
        </AccordionDetails>
      </Accordion>

      {/* Action Buttons */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleReset}
            disabled={loading}
          >
            Reset to Defaults
          </Button>
          <LoadingButton
            variant="contained"
            size="large"
            startIcon={<Save />}
            loading={loading}
            onClick={handleSave}
            sx={{ px: 4 }}
          >
            Save Settings
          </LoadingButton>
        </Box>
      </Paper>

      {/* Reset Dialog */}
      <Dialog
        open={resetDialogOpen}
        onClose={() => setResetDialogOpen(false)}
        aria-labelledby="reset-dialog-title"
        aria-describedby="reset-dialog-description"
      >
        <DialogTitle id="reset-dialog-title">
          Potwierdź usunięcie wszystkich stref
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="reset-dialog-description">
            Czy na pewno chcesz usunąć wszystkie {savedROIs.length} zapisane strefy? Ta operacja jest nieodwracalna.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialogOpen(false)} color="inherit">
            Anuluj
          </Button>
          <Button onClick={handleResetAllROIs} color="error" variant="contained" autoFocus>
            Usuń wszystkie
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for Feedback */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={snackbar.autoHideDuration || 4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Settings; 