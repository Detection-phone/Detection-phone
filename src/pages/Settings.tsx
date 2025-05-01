import React, { useState } from 'react';
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
  Alert,
} from '@mui/material';
import { TimePicker } from '@mui/x-date-pickers/TimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

const Settings: React.FC = () => {
  const [settings, setSettings] = useState({
    cameraStartTime: new Date(),
    cameraEndTime: new Date(),
    blurFaces: true,
    telegramEnabled: true,
    emailEnabled: true,
    smsEnabled: false,
    confidenceThreshold: 0.5,
  });

  const [saveStatus, setSaveStatus] = useState<'success' | 'error' | null>(null);

  const handleSave = () => {
    // TODO: Implement actual save functionality
    setSaveStatus('success');
    setTimeout(() => setSaveStatus(null), 3000);
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={3}>
        {/* Camera Settings */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Camera Settings
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <TimePicker
                    label="Camera Start Time"
                    value={settings.cameraStartTime}
                    onChange={(newValue) =>
                      setSettings({ ...settings, cameraStartTime: newValue || new Date() })
                    }
                  />
                </LocalizationProvider>
              </Grid>
              <Grid item xs={12} md={6}>
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <TimePicker
                    label="Camera End Time"
                    value={settings.cameraEndTime}
                    onChange={(newValue) =>
                      setSettings({ ...settings, cameraEndTime: newValue || new Date() })
                    }
                  />
                </LocalizationProvider>
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.blurFaces}
                      onChange={(e) =>
                        setSettings({ ...settings, blurFaces: e.target.checked })
                      }
                    />
                  }
                  label="Blur Faces in Detections"
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  type="number"
                  label="Detection Confidence Threshold"
                  value={settings.confidenceThreshold}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      confidenceThreshold: parseFloat(e.target.value),
                    })
                  }
                  inputProps={{ min: 0, max: 1, step: 0.1 }}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Notification Settings */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Notification Settings
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.telegramEnabled}
                      onChange={(e) =>
                        setSettings({ ...settings, telegramEnabled: e.target.checked })
                      }
                    />
                  }
                  label="Enable Telegram Notifications"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.emailEnabled}
                      onChange={(e) =>
                        setSettings({ ...settings, emailEnabled: e.target.checked })
                      }
                    />
                  }
                  label="Enable Email Notifications"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.smsEnabled}
                      onChange={(e) =>
                        setSettings({ ...settings, smsEnabled: e.target.checked })
                      }
                    />
                  }
                  label="Enable SMS Notifications"
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Save Button */}
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
            {saveStatus === 'success' && (
              <Alert severity="success">Settings saved successfully!</Alert>
            )}
            {saveStatus === 'error' && (
              <Alert severity="error">Error saving settings!</Alert>
            )}
            <Button variant="contained" color="primary" onClick={handleSave}>
              Save Settings
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Settings; 