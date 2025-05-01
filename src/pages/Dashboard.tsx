import React from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CardMedia,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

// Placeholder data
const detectionData = [
  { time: '00:00', count: 0 },
  { time: '04:00', count: 2 },
  { time: '08:00', count: 5 },
  { time: '12:00', count: 8 },
  { time: '16:00', count: 6 },
  { time: '20:00', count: 3 },
];

const recentDetections = [
  {
    id: 1,
    timestamp: '2024-02-20 14:30:00',
    image: 'https://via.placeholder.com/150',
    confidence: 0.95,
  },
  {
    id: 2,
    timestamp: '2024-02-20 14:25:00',
    image: 'https://via.placeholder.com/150',
    confidence: 0.88,
  },
  {
    id: 3,
    timestamp: '2024-02-20 14:20:00',
    image: 'https://via.placeholder.com/150',
    confidence: 0.92,
  },
];

const Dashboard: React.FC = () => {
  return (
    <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={3}>
        {/* Statistics Cards */}
        <Grid item xs={12} md={4}>
          <Paper
            sx={{
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              height: 140,
            }}
          >
            <Typography component="h2" variant="h6" color="primary" gutterBottom>
              Total Detections Today
            </Typography>
            <Typography component="p" variant="h4">
              24
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper
            sx={{
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              height: 140,
            }}
          >
            <Typography component="h2" variant="h6" color="primary" gutterBottom>
              Camera Status
            </Typography>
            <Typography component="p" variant="h4" color="success.main">
              Active
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper
            sx={{
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              height: 140,
            }}
          >
            <Typography component="h2" variant="h6" color="primary" gutterBottom>
              Notifications Sent
            </Typography>
            <Typography component="p" variant="h4">
              18
            </Typography>
          </Paper>
        </Grid>

        {/* Detection Chart */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column' }}>
            <Typography component="h2" variant="h6" color="primary" gutterBottom>
              Detections by Hour
            </Typography>
            <div style={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <BarChart data={detectionData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#1976d2" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Paper>
        </Grid>

        {/* Recent Detections */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column' }}>
            <Typography component="h2" variant="h6" color="primary" gutterBottom>
              Recent Detections
            </Typography>
            <Grid container spacing={2}>
              {recentDetections.map((detection) => (
                <Grid item xs={12} sm={6} md={4} key={detection.id}>
                  <Card>
                    <CardMedia
                      component="img"
                      height="140"
                      image={detection.image}
                      alt={`Detection ${detection.id}`}
                    />
                    <CardContent>
                      <Typography gutterBottom variant="h6" component="div">
                        {detection.timestamp}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Confidence: {(detection.confidence * 100).toFixed(1)}%
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard; 