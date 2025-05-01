import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';

// Placeholder data
const detections = [
  {
    id: 1,
    timestamp: '2024-02-20 14:30:00',
    location: 'Room 101',
    confidence: 0.95,
    image: 'https://via.placeholder.com/150',
    status: 'Notified',
  },
  {
    id: 2,
    timestamp: '2024-02-20 14:25:00',
    location: 'Room 102',
    confidence: 0.88,
    image: 'https://via.placeholder.com/150',
    status: 'Pending',
  },
  // Add more placeholder data as needed
];

const Detections: React.FC = () => {
  const [selectedDetection, setSelectedDetection] = useState<any>(null);
  const [openDialog, setOpenDialog] = useState(false);

  const columns: GridColDef[] = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'timestamp', headerName: 'Timestamp', width: 200 },
    { field: 'location', headerName: 'Location', width: 130 },
    {
      field: 'confidence',
      headerName: 'Confidence',
      width: 130,
      valueFormatter: (params) => `${(params.value * 100).toFixed(1)}%`,
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 130,
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 130,
      renderCell: (params) => (
        <Button
          variant="contained"
          size="small"
          onClick={() => {
            setSelectedDetection(params.row);
            setOpenDialog(true);
          }}
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <Box sx={{ height: '100%', width: '100%' }}>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom component="div">
          Phone Detections
        </Typography>
        <DataGrid
          rows={detections}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: { page: 0, pageSize: 10 },
            },
          }}
          pageSizeOptions={[10, 25, 50]}
          checkboxSelection
          disableRowSelectionOnClick
        />
      </Paper>

      <Dialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        maxWidth="md"
        fullWidth
      >
        {selectedDetection && (
          <>
            <DialogTitle>Detection Details</DialogTitle>
            <DialogContent>
              <Box sx={{ mt: 2 }}>
                <img
                  src={selectedDetection.image}
                  alt="Detection"
                  style={{ width: '100%', maxHeight: '400px', objectFit: 'contain' }}
                />
                <Typography variant="h6" sx={{ mt: 2 }}>
                  Details
                </Typography>
                <Typography>
                  <strong>Timestamp:</strong> {selectedDetection.timestamp}
                </Typography>
                <Typography>
                  <strong>Location:</strong> {selectedDetection.location}
                </Typography>
                <Typography>
                  <strong>Confidence:</strong>{' '}
                  {(selectedDetection.confidence * 100).toFixed(1)}%
                </Typography>
                <Typography>
                  <strong>Status:</strong> {selectedDetection.status}
                </Typography>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOpenDialog(false)}>Close</Button>
              <Button variant="contained" color="primary">
                Download Image
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default Detections; 