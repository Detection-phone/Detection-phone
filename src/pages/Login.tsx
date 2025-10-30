import React, { useState } from 'react';
import {
  Box,
  Container,
  TextField,
  Typography,
  Card,
  CardContent,
  InputAdornment,
  IconButton,
  Alert,
  Fade,
  Avatar,
  alpha,
} from '@mui/material';
import { LoadingButton } from '@mui/lab';
import {
  PersonOutline,
  LockOutlined,
  Visibility,
  VisibilityOff,
  PhonelinkRing,
  LoginOutlined,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
    } catch (err) {
      setError('Invalid username or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePassword = () => {
    setShowPassword(!showPassword);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: (theme) =>
          `linear-gradient(135deg, ${theme.palette.background.default} 0%, ${alpha(
            theme.palette.primary.main,
            0.05
          )} 100%)`,
        position: 'relative',
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: (theme) =>
            `radial-gradient(circle at 20% 50%, ${alpha(
              theme.palette.primary.main,
              0.1
            )} 0%, transparent 50%), radial-gradient(circle at 80% 80%, ${alpha(
              theme.palette.secondary.main,
              0.08
            )} 0%, transparent 50%)`,
          pointerEvents: 'none',
        },
      }}
    >
      <Container component="main" maxWidth="xs">
        <Fade in={true} timeout={600}>
          <Card
            elevation={24}
            sx={{
              position: 'relative',
              backdropFilter: 'blur(10px)',
              backgroundColor: (theme) => alpha(theme.palette.background.paper, 0.8),
              border: (theme) => `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
              overflow: 'visible',
            }}
          >
            <CardContent sx={{ p: 4 }}>
              {/* Logo/Icon */}
              <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
                <Avatar
                  sx={{
                    width: 72,
                    height: 72,
                    background: (theme) =>
                      `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
                    boxShadow: (theme) => `0 8px 24px ${alpha(theme.palette.primary.main, 0.4)}`,
                  }}
                >
                  <PhonelinkRing sx={{ fontSize: 40 }} />
                </Avatar>
              </Box>

              {/* Title */}
              <Typography
                variant="h4"
                align="center"
                gutterBottom
                sx={{
                  fontWeight: 700,
                  background: (theme) =>
                    `linear-gradient(135deg, ${theme.palette.primary.light} 0%, ${theme.palette.primary.main} 100%)`,
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  mb: 1,
                }}
              >
                Phone Detection System
              </Typography>

              <Typography
                variant="body2"
                align="center"
                color="text.secondary"
                sx={{ mb: 4 }}
              >
                Login to your account
              </Typography>

              {/* Error Alert */}
              {error && (
                <Fade in={true}>
                  <Alert
                    severity="error"
                    onClose={() => setError('')}
                    sx={{ mb: 3 }}
                  >
                    {error}
                  </Alert>
                </Fade>
              )}

              {/* Login Form */}
              <Box component="form" onSubmit={handleSubmit} noValidate>
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  id="username"
                  label="Username"
                  name="username"
                  autoComplete="username"
                  autoFocus
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <PersonOutline color="action" />
                      </InputAdornment>
                    ),
                  }}
                  sx={{ mb: 2 }}
                />

                <TextField
                  margin="normal"
                  required
                  fullWidth
                  name="password"
                  label="Password"
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <LockOutlined color="action" />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          aria-label="toggle password visibility"
                          onClick={handleTogglePassword}
                          edge="end"
                          disabled={loading}
                        >
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />

                <LoadingButton
                  type="submit"
                  fullWidth
                  variant="contained"
                  size="large"
                  loading={loading}
                  loadingPosition="start"
                  startIcon={<LoginOutlined />}
                  sx={{
                    mt: 4,
                    mb: 2,
                    py: 1.5,
                    fontSize: '1rem',
                    fontWeight: 600,
                    background: (theme) =>
                      `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
                    '&:hover': {
                      background: (theme) =>
                        `linear-gradient(135deg, ${theme.palette.primary.light} 0%, ${theme.palette.primary.main} 100%)`,
                    },
                  }}
                >
                  Login
                </LoadingButton>
              </Box>
            </CardContent>
          </Card>
        </Fade>

        {/* Footer */}
        <Typography
          variant="caption"
          align="center"
          color="text.secondary"
          sx={{ mt: 3, display: 'block' }}
        >
          © 2025 Phone Detection System
        </Typography>
      </Container>
    </Box>
  );
};

export default Login; 