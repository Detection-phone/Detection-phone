import React, { useState, useEffect } from 'react';
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
} from '@mui/material';
import { LoadingButton } from '@mui/lab';
import { settingsAPI, cameraAPI, CameraDevice } from '../services/api';
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
  Telegram,
  Videocam,
  VideocamOff,
  PlayArrow,
  Stop,
  Camera,
} from '@mui/icons-material';
import { TimePicker } from '@mui/x-date-pickers/TimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
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

const Settings: React.FC = () => {
  const [settings, setSettings] = useState({
    cameraStartTime: new Date(),
    cameraEndTime: new Date(),
    blurFaces: true,
    telegramEnabled: true,
    emailEnabled: true,
    smsEnabled: false,
    confidenceThreshold: 20,
    cameraIndex: 0,
    cameraName: 'Camera 1',
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
        
        setSettings({
          cameraStartTime: timeStringToDate(fetchedSettings.camera_start_time),
          cameraEndTime: timeStringToDate(fetchedSettings.camera_end_time),
          blurFaces: fetchedSettings.blur_faces,
          emailEnabled: fetchedSettings.email_notifications || fetchedSettings.notifications?.email || false,
          smsEnabled: fetchedSettings.sms_notifications || fetchedSettings.notifications?.sms || false,
          telegramEnabled: fetchedSettings.telegram_notifications || fetchedSettings.notifications?.telegram || false,
          confidenceThreshold: Math.round(fetchedSettings.confidence_threshold * 100), // Convert 0-1 to 0-100
          cameraIndex: fetchedSettings.camera_index || 0,
          cameraName: fetchedSettings.camera_name || 'Camera 1',
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

  const handleAccordionChange = (panel: string) => (_event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpanded(isExpanded ? panel : false);
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      // Convert to API format
      const payload = {
        camera_start_time: dateToTimeString(settings.cameraStartTime),
        camera_end_time: dateToTimeString(settings.cameraEndTime),
        blur_faces: settings.blurFaces,
        confidence_threshold: settings.confidenceThreshold / 100, // Convert 0-100 to 0-1
        camera_index: settings.cameraIndex,
        camera_name: settings.cameraName,
        notifications: {
          email: settings.emailEnabled,
          sms: settings.smsEnabled,
          telegram: settings.telegramEnabled,
        },
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
      cameraStartTime: new Date(),
      cameraEndTime: new Date(),
      blurFaces: true,
      telegramEnabled: true,
      emailEnabled: true,
      smsEnabled: false,
      confidenceThreshold: 20,
      cameraIndex: 0,
      cameraName: 'Camera 1',
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
    const startTime = new Date();
    startTime.setHours(0, 0, 0, 0);
    
    const endTime = new Date();
    endTime.setHours(23, 59, 0, 0);
    
    setSettings({
      ...settings,
      cameraStartTime: startTime,
      cameraEndTime: endTime,
    });
    
    setSnackbar({
      open: true,
      message: '24/7 schedule set (00:00 - 23:59)',
      severity: 'info',
    });
  };

  const handleSetBusinessHours = () => {
    const startTime = new Date();
    startTime.setHours(9, 0, 0, 0);
    
    const endTime = new Date();
    endTime.setHours(17, 0, 0, 0);
    
    setSettings({
      ...settings,
      cameraStartTime: startTime,
      cameraEndTime: endTime,
    });
    
    setSnackbar({
      open: true,
      message: 'Business Hours schedule set (09:00 - 17:00)',
      severity: 'info',
    });
  };

  const handleSetNightOnly = () => {
    const startTime = new Date();
    startTime.setHours(18, 0, 0, 0);
    
    const endTime = new Date();
    endTime.setHours(6, 0, 0, 0);
    
    setSettings({
      ...settings,
      cameraStartTime: startTime,
      cameraEndTime: endTime,
    });
    
    setSnackbar({
      open: true,
      message: 'Night Only schedule set (18:00 - 06:00)',
      severity: 'info',
    });
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
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <FormControl fullWidth>
                  <FormLabel sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <WbTwilight fontSize="small" />
                    Start Time
                  </FormLabel>
                  <TimePicker
                    value={settings.cameraStartTime}
                    onChange={(newValue) =>
                      setSettings({ ...settings, cameraStartTime: newValue || new Date() })
                    }
                  />
                  <FormHelperText>When to start detection</FormHelperText>
                </FormControl>
              </LocalizationProvider>
            </Grid>
            <Grid item xs={12} md={6}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <FormControl fullWidth>
                  <FormLabel sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Brightness4 fontSize="small" />
                    End Time
                  </FormLabel>
                  <TimePicker
                    value={settings.cameraEndTime}
                    onChange={(newValue) =>
                      setSettings({ ...settings, cameraEndTime: newValue || new Date() })
                    }
                  />
                  <FormHelperText>When to stop detection</FormHelperText>
                </FormControl>
              </LocalizationProvider>
            </Grid>
            <Grid item xs={12}>
              <Stack direction="row" spacing={1}>
                <Chip 
                  label="24/7" 
                  size="small" 
                  variant="outlined" 
                  clickable 
                  onClick={handleSet247}
                  icon={<Schedule fontSize="small" />}
                />
                <Chip 
                  label="Business Hours (9-5)" 
                  size="small" 
                  variant="outlined" 
                  clickable 
                  onClick={handleSetBusinessHours}
                  icon={<WbTwilight fontSize="small" />}
                />
                <Chip 
                  label="Night Only" 
                  size="small" 
                  variant="outlined" 
                  clickable 
                  onClick={handleSetNightOnly}
                  icon={<Brightness4 fontSize="small" />}
                />
              </Stack>
            </Grid>
          </Grid>
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
                Adjust detection sensitivity and thresholds
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
            <FormHelperText>
              Minimum confidence score required to trigger a detection. Higher values reduce false
              positives but may miss some detections.
            </FormHelperText>
          </FormControl>
          <Divider sx={{ my: 3 }} />
          <Stack direction="row" spacing={1}>
            <Chip
              label="Low Sensitivity"
              size="small"
              variant="outlined"
              clickable
              onClick={() => setSettings({ ...settings, confidenceThreshold: 70 })}
            />
            <Chip
              label="Medium (Recommended)"
              size="small"
              variant="outlined"
              clickable
              onClick={() => setSettings({ ...settings, confidenceThreshold: 40 })}
            />
            <Chip
              label="High Sensitivity"
              size="small"
              variant="outlined"
              clickable
              onClick={() => setSettings({ ...settings, confidenceThreshold: 20 })}
            />
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
                  Blur faces in images
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Automatically blur detected faces to protect privacy
                </Typography>
              </Box>
            }
            sx={{ mb: 2 }}
          />
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
            <FormControlLabel
              control={
                <Switch
                  checked={settings.telegramEnabled}
                  onChange={(e) => setSettings({ ...settings, telegramEnabled: e.target.checked })}
                  color="primary"
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Telegram fontSize="small" color={settings.telegramEnabled ? 'primary' : 'disabled'} />
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      Telegram Notifications
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Receive alerts via Telegram
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