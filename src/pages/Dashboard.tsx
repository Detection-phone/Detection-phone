import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  IconButton,
  Avatar,
  alpha,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Videocam,
  Notifications,
  Visibility,
  Download,
  PhonelinkRing,
  LocationOn,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area,
  AreaChart,
} from 'recharts';
import { dashboardAPI, DashboardStats } from '../services/api';
import { handleDownloadImage } from '../utils/download';

// KPI Card Component
interface KPICardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  color: string;
}

const KPICard: React.FC<KPICardProps> = ({ title, value, change, icon, color }) => {
  const isPositive = change !== undefined && change >= 0;

  const [chartData, setChartData] = useState<Array<{ name: string; count: number }>>([]);

  useEffect(() => {
    const fetchChart = async () => {
      try {
        const res = await fetch('http://localhost:5000/api/stats/detections_over_time');
        const data = await res.json();
        setChartData(Array.isArray(data) ? data : []);
      } catch (e) {
        console.error('Failed to load chart data', e);
      }
    };
    fetchChart();
  }, []);

  return (
    <Card
      sx={{
        height: '100%',
        background: (theme) =>
          `linear-gradient(135deg, ${alpha(color, 0.1)} 0%, ${alpha(
            color,
            0.05
          )} 100%)`,
        border: (theme) => `1px solid ${alpha(color, 0.2)}`,
        position: 'relative',
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          right: 0,
          width: '100px',
          height: '100px',
          background: `radial-gradient(circle, ${alpha(color, 0.2)} 0%, transparent 70%)`,
          borderRadius: '50%',
          transform: 'translate(30%, -30%)',
        },
      }}
    >
      <CardContent sx={{ position: 'relative', zIndex: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
            {title}
          </Typography>
          <Avatar
            sx={{
              bgcolor: alpha(color, 0.2),
              width: 40,
              height: 40,
            }}
          >
            {icon}
          </Avatar>
        </Box>
        <Typography variant="h3" sx={{ fontWeight: 700, mb: 1, color }}>
          {value}
        </Typography>
        {change !== undefined && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {isPositive ? (
              <TrendingUp sx={{ fontSize: 18, color: 'success.main' }} />
            ) : (
              <TrendingDown sx={{ fontSize: 18, color: 'error.main' }} />
            )}
            <Typography
              variant="caption"
              sx={{
                color: isPositive ? 'success.main' : 'error.main',
                fontWeight: 600,
              }}
            >
              {Math.abs(change)}% from last week
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

const Dashboard: React.FC = () => {
  // ✅ FIXED: Fetch real data from API
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<Array<{ name: string; count: number }>>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const data = await dashboardAPI.getStats();
        setStats(data);
        setError(null);
      } catch (err: any) {
        console.error('❌ Failed to fetch dashboard data:', err);
        setError('Failed to load dashboard data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // fetch chart data
    const fetchChart = async () => {
      try {
        const res = await fetch('http://localhost:5000/api/stats/detections_over_time');
        const data = await res.json();
        setChartData(Array.isArray(data) ? data : []);
      } catch (e) {
        console.error('Failed to load chart data', e);
      }
    };
    fetchChart();
    
    // Refresh data every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !stats) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress size={60} />
      </Box>
    );
  }

  if (error && !stats) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  // Use fetched data or fallback to defaults
  const totalDetections = stats?.total_detections ?? 0;
  const todayDetections = stats?.today_detections ?? 0;
  const cameraStatus = stats?.camera_status ?? 'Offline';
  const notificationsSent = stats?.notifications_sent ?? 0;
  const weeklyData = stats?.weekly_data ?? [];
  const locationData = stats?.location_data ?? [];
  const recentDetections = stats?.recent_detections ?? [];

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={3}>
        {/* KPI Cards */}
        <Grid item xs={12} sm={6} lg={4}>
          <KPICard
            title="Total Detections"
            value={totalDetections}
            change={12}
            icon={<PhonelinkRing sx={{ color: '#3B82F6' }} />}
            color="#3B82F6"
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={4}>
          <KPICard
            title="Today's Detections"
            value={todayDetections}
            change={-8}
            icon={<TrendingUp sx={{ color: '#10B981' }} />}
            color="#10B981"
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={4}>
          <KPICard
            title="Camera Status"
            value={cameraStatus}
            icon={<Videocam sx={{ color: cameraStatus === 'Active' ? '#10B981' : '#F59E0B' }} />}
            color={cameraStatus === 'Active' ? '#10B981' : '#F59E0B'}
          />
        </Grid>

        {/* Detections Over Time Chart */}
        <Grid item xs={12} lg={12}>
          <Paper sx={{ p: 3, height: '480px' }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
              Detections Over Time (Last 7 Days)
            </Typography>
            <ResponsiveContainer width="100%" height="90%">
              <AreaChart data={chartData.length ? chartData : weeklyData}>
                <defs>
                  <linearGradient id="colorDetections" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey={chartData.length ? 'name' : 'day'}
                  stroke="#94A3B8"
                  style={{ fontSize: '0.75rem' }}
                />
                <YAxis stroke="#94A3B8" style={{ fontSize: '0.75rem' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey={chartData.length ? 'count' : 'detections'}
                  stroke="#3B82F6"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorDetections)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        

        {/* Recent Detections Table */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
              Recent Detections
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Time</TableCell>
                    <TableCell>Location</TableCell>
                    <TableCell>Confidence</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recentDetections.map((detection) => (
                    <TableRow
                      key={detection.id}
                      sx={{
                        '&:hover': {
                          backgroundColor: (theme) =>
                            alpha(theme.palette.primary.main, 0.05),
                        },
                        transition: 'background-color 0.2s',
                      }}
                    >
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {new Date((detection.timestamp as any) + 'Z').toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <LocationOn sx={{ fontSize: 18, color: 'text.secondary' }} />
                          <Typography variant="body2">{detection.location}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ minWidth: 120 }}>
                          <Typography variant="caption" sx={{ mb: 0.5, display: 'block' }}>
                            {(detection.confidence * 100).toFixed(1)}%
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={Math.min(detection.confidence * 100, 100)}
                            sx={{
                              '& .MuiLinearProgress-bar': {
                                backgroundColor:
                                  detection.confidence * 100 > 70
                                    ? 'success.main'
                                    : detection.confidence * 100 > 40
                                    ? 'warning.main'
                                    : 'error.main',
                              },
                            }}
                          />
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={detection.status}
                          size="small"
                          color="warning"
                          sx={{ fontWeight: 500 }}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => {
                            const url = `http://localhost:5000/detections/${detection.image_path}`;
                            window.open(url, '_blank');
                          }}
                        >
                          <Visibility fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => handleDownloadImage(detection.image_path)}
                        >
                          <Download fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard; 