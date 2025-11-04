import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Card,
  CardMedia,
  CardContent,
  Chip,
  LinearProgress,
  IconButton,
  ToggleButtonGroup,
  ToggleButton,
  TextField,
  InputAdornment,
  Divider,
  alpha,
  CircularProgress,
  Alert,
  Snackbar,
  Pagination,
  Stack,
  Checkbox,
} from '@mui/material';
import {
  GridView,
  ViewList,
  Search,
  Download,
  Delete,
  Visibility,
  AccessTime,
  LocationOn,
  TrendingUp,
  Close,
  NavigateBefore,
  NavigateNext,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { detectionAPI, Detection } from '../services/api';
import { handleDownloadImage } from '../utils/download';

const Detections: React.FC = () => {
  // ✅ FIXED: Real state with API data
  const [detections, setDetections] = useState<Detection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedDetection, setSelectedDetection] = useState<Detection | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [selectedDetections, setSelectedDetections] = useState<Set<number>>(new Set());
  const [isSelectAll, setIsSelectAll] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error';
  }>({ open: false, message: '', severity: 'success' });

  // ✅ FIXED: Fetch detections from API with pagination
  useEffect(() => {
    fetchDetections();
    const intervalId = setInterval(() => {
      fetchDetections();
    }, 20000); // 20s polling to keep list fresh
    return () => clearInterval(intervalId);
  }, [page]);

  const fetchDetections = async () => {
    try {
      setLoading(true);
      const response = await detectionAPI.getAll(page, 20);
      // ✅ FIXED: Ensure detections is always an array
      setDetections(response.detections || []);
      setTotalPages(response.total_pages || 0);
      const detectionsCount = (response.detections || []).length;
      console.log('✅ Detections loaded:', detectionsCount, 'items (page', page, 'of', response.total_pages || 0, ')');
      setError(null);
    } catch (err: any) {
      console.error('❌ Failed to fetch detections:', err);
      setError('Failed to load detections. Please try again.');
      // ✅ FIXED: Set empty array on error to prevent undefined
      setDetections([]);
    } finally {
      setLoading(false);
    }
  };

  // Navigate to previous/next detection in the current list
  const handlePrev = () => {
    if (!selectedDetection) return;
    const idx = detections.findIndex((d) => d.id === selectedDetection.id);
    if (idx > 0) {
      setSelectedDetection(detections[idx - 1]);
    }
  };

  const handleNext = () => {
    if (!selectedDetection) return;
    const idx = detections.findIndex((d) => d.id === selectedDetection.id);
    if (idx >= 0 && idx < detections.length - 1) {
      setSelectedDetection(detections[idx + 1]);
    }
  };

  const handleViewChange = (_event: React.MouseEvent<HTMLElement>, newView: 'grid' | 'list' | null) => {
    if (newView !== null) {
      setViewMode(newView);
    }
  };

  const handleViewDetails = (detection: Detection) => {
    setSelectedDetection(detection);
    setOpenDialog(true);
  };

  // ✅ FIXED: Real download handler
  const handleDownload = async (detection: Detection) => {
    try {
      await handleDownloadImage(detection.image_path);
      setSnackbar({ open: true, message: 'Image downloaded successfully!', severity: 'success' });
    } catch (error) {
      console.error('❌ Download failed:', error);
      setSnackbar({ open: true, message: 'Failed to download image', severity: 'error' });
    }
  };

  // ✅ FIXED: Real delete handler
  const handleDelete = async (detection: Detection) => {
    if (!window.confirm(`Delete detection from ${detection.timestamp}?`)) {
      return;
    }

    try {
      console.log('🗑️ Deleting detection:', detection.id);
      // Optimistic UI: remove immediately
      const backup = detections;
      setDetections(prev => prev.filter(d => d.id !== detection.id));
      await detectionAPI.delete(detection.id);
      // Ensure sync with server state
      await fetchDetections();
      
      setSnackbar({
        open: true,
        message: 'Detection deleted successfully!',
        severity: 'success',
      });
    } catch (error) {
      console.error('❌ Delete failed:', error);
      // Re-sync state if deletion fails
      await fetchDetections();
      setSnackbar({
        open: true,
        message: 'Failed to delete detection',
        severity: 'error',
      });
    }
  };

  // Batch selection handlers
  const handleToggleSelection = (detectionId: number) => {
    setSelectedDetections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(detectionId)) {
        newSet.delete(detectionId);
      } else {
        newSet.add(detectionId);
      }
      return newSet;
    });
  };

  const handleSelectAll = (checked: boolean) => {
    setIsSelectAll(checked);
    if (checked) {
      const allIds = new Set(detections.map(d => d.id));
      setSelectedDetections(allIds);
    } else {
      // Usuń tylko ID z aktualnej strony
      const currentPageIds = new Set(detections.map(d => d.id));
      setSelectedDetections(prev => {
        const newSet = new Set(prev);
        currentPageIds.forEach(id => newSet.delete(id));
        return newSet;
      });
    }
  };

  // Automatycznie aktualizuj isSelectAll gdy zmienia się selectedDetections
  useEffect(() => {
    if (detections.length === 0) {
      setIsSelectAll(false);
      return;
    }
    const currentPageIds = new Set(detections.map(d => d.id));
    const allSelected = Array.from(currentPageIds).every(id => selectedDetections.has(id));
    setIsSelectAll(allSelected);
  }, [selectedDetections, detections]);

  // Wyczyść zaznaczenie przy zmianie strony
  useEffect(() => {
    setSelectedDetections(new Set());
    setIsSelectAll(false);
  }, [page]);

  // Batch delete handler
  const handleDeleteSelected = async () => {
    const idsToDelete = Array.from(selectedDetections);
    if (idsToDelete.length === 0) return;

    try {
      console.log('🗑️ Deleting detections:', idsToDelete);
      await detectionAPI.deleteBatch(idsToDelete);
      
      // Odśwież stronę
      await fetchDetections();
      
      // Wyczyść zaznaczenie
      setSelectedDetections(new Set());
      setIsSelectAll(false);
      setDeleteDialogOpen(false);
      
      setSnackbar({
        open: true,
        message: `Usunięto ${idsToDelete.length} detekcji.`,
        severity: 'success',
      });
    } catch (error) {
      console.error('❌ Batch delete failed:', error);
      setSnackbar({
        open: true,
        message: 'Nie udało się usunąć detekcji',
        severity: 'error',
      });
    }
  };

  const getConfidenceColor = (confidenceFraction: number) => {
    const confidencePercent = confidenceFraction * 100;
    if (confidencePercent > 70) return 'success';
    if (confidencePercent > 40) return 'warning';
    return 'error';
  };

  // Get image URL
  const getImageUrl = (imagePath: string) => {
    // Flask serves images from /detections/<filename>
    return `http://localhost:5000/detections/${imagePath}`;
  };

  // Grid View Component
  const GridView_Component = () => (
    <Grid container spacing={3}>
      {detections.map((detection) => (
        <Grid item xs={12} sm={6} md={4} lg={3} key={detection.id}>
          <Card
            sx={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: (theme) => `0 12px 24px ${alpha(theme.palette.primary.main, 0.2)}`,
              },
            }}
          >
            <Box sx={{ position: 'relative' }}>
              <CardMedia
                component="img"
                height="180"
                image={getImageUrl(detection.image_path)}
                alt={`Detection ${detection.id}`}
                sx={{
                  objectFit: 'cover',
                  backgroundColor: '#1E293B',
                }}
                onError={(e: any) => {
                  // Fallback to placeholder if image fails to load
                  e.target.src = 'https://via.placeholder.com/300x200?text=No+Image';
                }}
              />
              <Box
                sx={{
                  position: 'absolute',
                  top: 8,
                  left: 8,
                  backgroundColor: (theme) => alpha(theme.palette.background.paper, 0.9),
                  borderRadius: 1,
                }}
              >
                <Checkbox
                  checked={selectedDetections.has(detection.id)}
                  onChange={(e) => {
                    e.stopPropagation();
                    handleToggleSelection(detection.id);
                  }}
                  size="small"
                  sx={{
                    color: 'white',
                    '&.Mui-checked': {
                      color: 'primary.main',
                    },
                  }}
                />
              </Box>
              <Box
                sx={{
                  position: 'absolute',
                  top: 8,
                  right: 8,
                }}
              >
                <Chip
                  label={detection.status}
                  size="small"
                  color="warning"
                  sx={{
                    fontWeight: 600,
                    backdropFilter: 'blur(8px)',
                    backgroundColor: (theme) => alpha(theme.palette.warning.main, 0.9),
                  }}
                />
              </Box>
            </Box>
            <CardContent sx={{ flexGrow: 1, pb: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                <AccessTime sx={{ fontSize: 14, color: 'text.secondary' }} />
                <Typography variant="caption" color="text.secondary">
                  {new Date((detection.timestamp as any) + 'Z').toLocaleString()}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 2 }}>
                <LocationOn sx={{ fontSize: 14, color: 'text.secondary' }} />
                <Typography variant="caption" color="text.secondary">
                  {detection.location}
                </Typography>
              </Box>
              <Box sx={{ mb: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
                    Confidence
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      fontWeight: 700,
                      color: `${getConfidenceColor(detection.confidence)}.main`,
                    }}
                  >
                    {(detection.confidence * 100).toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(detection.confidence * 100, 100)}
                  color={getConfidenceColor(detection.confidence)}
                />
              </Box>
            </CardContent>
            <Divider />
            <Box sx={{ p: 1, display: 'flex', justifyContent: 'space-around' }}>
              <IconButton
                size="small"
                color="primary"
                onClick={() => handleViewDetails(detection)}
                title="View details"
              >
                <Visibility fontSize="small" />
              </IconButton>
              <IconButton 
                size="small" 
                color="primary"
                onClick={() => handleDownload(detection)}
                title="Download image"
              >
                <Download fontSize="small" />
              </IconButton>
              <IconButton 
                size="small" 
                color="error"
                onClick={() => handleDelete(detection)}
                title="Delete detection"
              >
                <Delete fontSize="small" />
              </IconButton>
            </Box>
          </Card>
        </Grid>
      ))}
    </Grid>
  );

  // List View Component
  const columns: GridColDef[] = [
    {
      field: 'image',
      headerName: 'Image',
      width: 100,
      renderCell: (params: GridRenderCellParams) => (
        <Box
          component="img"
          src={params.row.image}
          alt={`Detection ${params.row.id}`}
          sx={{
            width: 60,
            height: 40,
            objectFit: 'cover',
            borderRadius: 1,
          }}
        />
      ),
    },
    { 
      field: 'timestamp', 
      headerName: 'Timestamp', 
      width: 200,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AccessTime sx={{ fontSize: 16, color: 'text.secondary' }} />
          <Typography variant="body2">{new Date((params.value as any) + 'Z').toLocaleString()}</Typography>
        </Box>
      ),
    },
    { 
      field: 'location', 
      headerName: 'Location', 
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <LocationOn sx={{ fontSize: 16, color: 'text.secondary' }} />
          <Typography variant="body2">{params.value}</Typography>
        </Box>
      ),
    },
    {
      field: 'confidence',
      headerName: 'Confidence',
      width: 200,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ width: '100%' }}>
          <Typography variant="caption" sx={{ mb: 0.5, display: 'block' }}>
            {(params.value * 100).toFixed(1)}%
          </Typography>
          <LinearProgress
            variant="determinate"
            value={Math.min(params.value * 100, 100)}
            color={getConfidenceColor(params.value)}
          />
        </Box>
      ),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 130,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value}
          size="small"
          color="warning"
          sx={{ fontWeight: 500 }}
        />
      ),
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 150,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <IconButton
          size="small"
            color="primary"
            onClick={() => handleViewDetails(params.row)}
            title="View details"
          >
            <Visibility fontSize="small" />
          </IconButton>
          <IconButton 
            size="small" 
            color="primary"
            onClick={() => handleDownload(params.row)}
            title="Download image"
          >
            <Download fontSize="small" />
          </IconButton>
          <IconButton 
            size="small" 
            color="error"
            onClick={() => handleDelete(params.row)}
            title="Delete detection"
          >
            <Delete fontSize="small" />
          </IconButton>
        </Box>
      ),
    },
  ];

  // Loading state
  if (loading && detections.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress size={60} />
      </Box>
    );
  }

  // Error state
  if (error && detections.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={fetchDetections}>
            Retry
          </Button>
        }>
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header with Controls */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 2,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {detections.length > 0 && (
              <Checkbox
                checked={isSelectAll}
                indeterminate={selectedDetections.size > 0 && !isSelectAll}
                onChange={(e) => handleSelectAll(e.target.checked)}
                size="small"
              />
            )}
            <Typography variant="h5" sx={{ fontWeight: 600 }}>
              All Detections {detections.length > 0 && `(${detections.length})`}
              {selectedDetections.size > 0 && ` - Zaznaczono: ${selectedDetections.size}`}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            {selectedDetections.size > 0 && (
              <Button
                variant="contained"
                color="error"
                size="small"
                startIcon={<Delete />}
                onClick={() => setDeleteDialogOpen(true)}
              >
                Usuń zaznaczone ({selectedDetections.size})
              </Button>
            )}
            <TextField
              size="small"
              placeholder="Search detections..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search fontSize="small" />
                  </InputAdornment>
                ),
              }}
              sx={{ minWidth: 250 }}
            />
            <ToggleButtonGroup
              value={viewMode}
              exclusive
              onChange={handleViewChange}
              size="small"
              sx={{
                '& .MuiToggleButton-root': {
                  px: 2,
                },
              }}
            >
              <ToggleButton value="grid">
                <GridView fontSize="small" sx={{ mr: 0.5 }} />
                Grid
              </ToggleButton>
              <ToggleButton value="list">
                <ViewList fontSize="small" sx={{ mr: 0.5 }} />
                List
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>
        </Box>
      </Paper>

      {/* Content Area */}
      {detections.length === 0 ? (
        <Paper sx={{ p: 6, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No detections found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Detections will appear here when the camera captures phone usage
          </Typography>
        </Paper>
      ) : viewMode === 'grid' ? (
        <GridView_Component />
      ) : (
        <Paper sx={{ height: 600, width: '100%' }}>
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
            rowHeight={80}
            sx={{
              '& .MuiDataGrid-row:hover': {
                backgroundColor: (theme) => alpha(theme.palette.primary.main, 0.05),
              },
            }}
          />
        </Paper>
      )}

      {/* Pagination */}
      {totalPages > 0 && (
        <Stack spacing={2} alignItems="center" sx={{ mt: 3, mb: 2 }}>
          <Pagination 
            count={totalPages} 
            page={page} 
            onChange={(event, value) => setPage(value)} 
            color="primary" 
          />
        </Stack>
      )}

      {/* Detail Dialog */}
      <Dialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 2,
          },
        }}
      >
        {selectedDetection && (
          <>
            <DialogTitle
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                pb: 1,
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Detection Details
              </Typography>
              <IconButton
                edge="end"
                color="inherit"
                onClick={() => setOpenDialog(false)}
                aria-label="close"
              >
                <Close />
              </IconButton>
            </DialogTitle>
            <Divider />
            <DialogContent sx={{ p: 3 }}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={7}>
                  <Box
                    component="img"
                    src={getImageUrl(selectedDetection.image_path)}
                    alt="Detection"
                    sx={{
                      width: '100%',
                      borderRadius: 2,
                      border: (theme) => `1px solid ${theme.palette.divider}`,
                      backgroundColor: '#1E293B',
                    }}
                    onError={(e: any) => {
                      e.target.src = 'https://via.placeholder.com/600x400?text=No+Image';
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={5}>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 2,
                      backgroundColor: (theme) => alpha(theme.palette.background.default, 0.3),
                    }}
                  >
                    <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Information
                    </Typography>
                    <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Timestamp
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                          {new Date((selectedDetection.timestamp as any) + 'Z').toLocaleString()}
                </Typography>
                      </Box>
                      <Divider />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Location
                </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                          {selectedDetection.location}
                </Typography>
                      </Box>
                      <Divider />
                      <Box>
                        <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                          Confidence Score
                </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Typography
                            variant="h5"
                              sx={{
                                fontWeight: 700,
                                color: `${getConfidenceColor(selectedDetection.confidence)}.main`,
                              }}
                          >
                            {(selectedDetection.confidence * 100).toFixed(1)}%
                </Typography>
              </Box>
                        <LinearProgress
                          variant="determinate"
                          value={Math.min(selectedDetection.confidence * 100, 100)}
                          color={getConfidenceColor(selectedDetection.confidence)}
                          sx={{ height: 8 }}
                        />
                      </Box>
                      <Divider />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Status
                        </Typography>
                        <Box sx={{ mt: 0.5 }}>
                          <Chip
                            label={selectedDetection.status}
                            color="warning"
                            size="small"
                            sx={{ fontWeight: 600 }}
                          />
                        </Box>
                      </Box>
                    </Box>
                  </Paper>
                </Grid>
              </Grid>
            </DialogContent>
            <Divider />
            <DialogActions sx={{ p: 2, gap: 1 }}>
              <Button
                startIcon={<NavigateBefore />}
                variant="outlined"
                color="inherit"
                onClick={handlePrev}
                disabled={!selectedDetection || detections.findIndex(d => d.id === selectedDetection.id) === 0}
              >
                Previous
              </Button>
              <Box sx={{ flexGrow: 1 }} />
              <Button
                onClick={() => setOpenDialog(false)}
                variant="outlined"
                color="inherit"
              >
                Close
              </Button>
              <Button
                variant="contained"
                startIcon={<Download />}
                color="primary"
                onClick={() => selectedDetection && handleDownload(selectedDetection)}
              >
                Download
              </Button>
              <Button
                endIcon={<NavigateNext />}
                variant="outlined"
                color="inherit"
                onClick={handleNext}
                disabled={!selectedDetection || detections.findIndex(d => d.id === selectedDetection.id) === detections.length - 1}
              >
                Next
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ fontWeight: 600 }}>
          Potwierdź usunięcie
        </DialogTitle>
        <DialogContent>
          <Typography>
            Czy na pewno chcesz usunąć <strong>{selectedDetections.size}</strong> {selectedDetections.size === 1 ? 'zaznaczoną detekcję' : 'zaznaczonych detekcji'}?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Ta operacja jest nieodwracalna.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setDeleteDialogOpen(false)}
            color="inherit"
          >
            Anuluj
          </Button>
          <Button
            onClick={handleDeleteSelected}
            variant="contained"
            color="error"
            startIcon={<Delete />}
          >
            Usuń
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
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

export default Detections; 