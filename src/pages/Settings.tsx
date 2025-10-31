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
} from '@mui/material';
import { LoadingButton } from '@mui/lab';
import api, { settingsAPI, cameraAPI, CameraDevice, getBaseUrl } from '../services/api';
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
    severity: 'success' | 'error' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });
  const [expanded, setExpanded] = useState<string | false>('schedule');

  // ROI state
  const [isRoiExpanded, setIsRoiExpanded] = useState(false);

  // ROI local drawing state
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawEnd, setDrawEnd] = useState<{ x: number; y: number } | null>(null);
  const imgRef = React.useRef<HTMLImageElement | null>(null);
  const wrapperRef = React.useRef<HTMLDivElement | null>(null);
  const videoFeedRef = useRef<HTMLDivElement | null>(null);

  // Re-loadable video src with cache-busting
  const [videoSrc, setVideoSrc] = useState<string | null>(null);

  // Fetch settings and camera status on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch settings
        const fetchedSettings = await settingsAPI.get();
        
        console.log('📡 Fetched settings:', fetchedSettings);
        
        // Set available cameras
        if (fetchedSettings.available_cameras) {
          setAvailableCameras(fetchedSettings.available_cameras);
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

  // Reactive video stream management: responds to both ROI accordion state and camera status
  useEffect(() => {
    if (isRoiExpanded && cameraStatus.isRunning) {
      // PRZYPADEK 1: Akordeon jest otwarty I kamera działa
      // Uruchom lub odśwież stream
      setVideoSrc(`${getBaseUrl()}/api/camera/video_feed?t=${Date.now()}`);
    } else {
      // PRZYPADEK 2: Akordeon jest zamknięty LUB kamera jest zatrzymana
      // Zatrzymaj stream (wyczyść src)
      setVideoSrc(null);
    }
  }, [isRoiExpanded, cameraStatus.isRunning]); // Reaguj na obie te zmiany

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
    if (!rect) return { x: 0, y: 0 };
    const x = Math.min(Math.max(e.clientX - rect.left, 0), rect.width);
    const y = Math.min(Math.max(e.clientY - rect.top, 0), rect.height);
    return { x, y, width: rect.width, height: rect.height } as any;
  };

  const onMouseDown = (e: React.MouseEvent) => {
    const { x, y } = getRelativeCoords(e) as any;
    setIsDrawing(true);
    setDrawStart({ x, y });
    setDrawEnd({ x, y });
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (!isDrawing || !drawStart) return;
    const { x, y } = getRelativeCoords(e) as any;
    setDrawEnd({ x, y });
  };

  const onMouseUp = (e: React.MouseEvent) => {
    if (!isDrawing || !drawStart) return;
    const { x, y, width, height } = getRelativeCoords(e) as any;
    setIsDrawing(false);
    setDrawEnd({ x, y });
    // Normalize and save temp ROI
    const x1 = Math.min(drawStart.x, x) / width;
    const y1 = Math.min(drawStart.y, y) / height;
    const x2 = Math.max(drawStart.x, x) / width;
    const y2 = Math.max(drawStart.y, y) / height;
    const clamped: [number, number, number, number] = [
      Math.max(0, Math.min(1, x1)),
      Math.max(0, Math.min(1, y1)),
      Math.max(0, Math.min(1, x2)),
      Math.max(0, Math.min(1, y2)),
    ];
    setSettings({ ...settings, roi: clamped });
  };

  const clearROI = () => {
    setSettings({ ...settings, roi: null });
    setDrawStart(null);
    setDrawEnd(null);
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
      {/* NOWA SEKCJA ROI (wg wskazówek) */}
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
          <Typography>Region Zainteresowania (ROI)</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">
              Kliknij i przeciągnij na podglądzie na żywo, aby narysować obszar. Detekcje będą rejestrowane tylko w tym obszarze.
            </Typography>

            {/* --- Kontener do rysowania --- */}
            <Box
              ref={videoFeedRef}
              sx={{
                position: 'relative',
                cursor: 'crosshair',
                width: '100%',
                border: (theme) => `1px solid ${theme.palette.divider}`,
                overflow: 'hidden',
              }}
              onMouseDown={(e: React.MouseEvent<HTMLDivElement>) => {
                if (!videoFeedRef.current) return;
                const rect = videoFeedRef.current.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                setIsDrawing(true);
                setDrawStart({ x, y });
                setDrawEnd({ x, y });
              }}
              onMouseMove={(e: React.MouseEvent<HTMLDivElement>) => {
                if (!isDrawing || !videoFeedRef.current || !drawStart) return;
                const rect = videoFeedRef.current.getBoundingClientRect();
                const x = Math.min(Math.max(0, e.clientX - rect.left), rect.width);
                const y = Math.min(Math.max(0, e.clientY - rect.top), rect.height);
                setDrawEnd({ x, y });
              }}
              onMouseUp={(e: React.MouseEvent<HTMLDivElement>) => {
                if (!isDrawing || !videoFeedRef.current || !drawStart) return;
                setIsDrawing(false);
                const { width, height } = videoFeedRef.current.getBoundingClientRect();
                if (width === 0 || height === 0 || !drawEnd) return;
                const x1 = Math.min(drawStart.x, drawEnd.x) / width;
                const y1 = Math.min(drawStart.y, drawEnd.y) / height;
                const x2 = Math.max(drawStart.x, drawEnd.x) / width;
                const y2 = Math.max(drawStart.y, drawEnd.y) / height;
                if (x1 === x2 || y1 === y2) {
                  setSettings({ ...settings, roi: null });
                } else {
                  setSettings({
                    ...settings,
                    roi: [
                      parseFloat(x1.toFixed(4)),
                      parseFloat(y1.toFixed(4)),
                      parseFloat(x2.toFixed(4)),
                      parseFloat(y2.toFixed(4)),
                    ],
                  });
                }
              }}
              onMouseLeave={() => {
                if (isDrawing) setIsDrawing(false);
              }}
            >
              {/* Podgląd na żywo */}
              <Box sx={{ position: 'relative', minHeight: '200px', background: '#000' }}>
                {videoSrc ? (
                  <img
                    src={videoSrc}
                    alt="Live preview"
                    style={{
                      width: '100%',
                      height: 'auto',
                      display: 'block',
                      pointerEvents: 'none',
                    }}
                  />
                ) : (
                  <img
                    src={'/static/images/looking.png'}
                    alt="Live preview offline"
                    style={{
                      width: '100%',
                      height: 'auto',
                      display: 'block',
                      objectFit: 'contain',
                      maxHeight: '480px',
                    }}
                  />
                )}
              </Box>

              {/* Narysowany prostokąt (w trakcie) */}
              {isDrawing && drawStart && drawEnd && (
                <div
                  style={{
                    position: 'absolute',
                    border: '2px dashed #00bfff',
                    left: Math.min(drawStart.x, drawEnd.x),
                    top: Math.min(drawStart.y, drawEnd.y),
                    width: Math.abs(drawStart.x - drawEnd.x),
                    height: Math.abs(drawStart.y - drawEnd.y),
                    pointerEvents: 'none',
                  }}
                />
              )}

              {/* Zapisany prostokąt */}
              {!isDrawing && settings.roi && videoFeedRef.current && (
                <div
                  style={{
                    position: 'absolute',
                    border: '2px solid #00bfff',
                    backgroundColor: 'rgba(0, 191, 255, 0.2)',
                    left: settings.roi[0] * videoFeedRef.current.clientWidth,
                    top: settings.roi[1] * videoFeedRef.current.clientHeight,
                    width: (settings.roi[2] - settings.roi[0]) * videoFeedRef.current.clientWidth,
                    height: (settings.roi[3] - settings.roi[1]) * videoFeedRef.current.clientHeight,
                    pointerEvents: 'none',
                  }}
                />
              )}
            </Box>

            {/* Przyciski */}
            <Stack direction="row" spacing={1} justifyContent="space-between" alignItems="center">
              <Button variant="outlined" color="warning" onClick={() => setSettings({ ...settings, roi: null })}>
                Wyczyść ROI
              </Button>
              <Typography variant="body2" fontFamily="monospace" color="text.secondary">
                {settings?.roi ? `ROI: [${settings.roi.join(', ')}]` : 'ROI: [Brak]'}
              </Typography>
              <LoadingButton variant="contained" startIcon={<Save />} loading={loading} onClick={handleSave}>
                Zapisz ROI
              </LoadingButton>
            </Stack>
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
                    Loading cameras...
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

      {/* Snackbar for Feedback */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
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