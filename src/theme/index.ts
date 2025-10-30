import { createTheme, alpha } from '@mui/material/styles';

// Color palette - Professional dark theme for security/monitoring app
const palette = {
  mode: 'dark' as const,
  primary: {
    main: '#3B82F6',      // Bright Blue
    light: '#60A5FA',
    dark: '#2563EB',
    contrastText: '#FFFFFF',
  },
  secondary: {
    main: '#10B981',      // Emerald Green
    light: '#34D399',
    dark: '#059669',
    contrastText: '#FFFFFF',
  },
  error: {
    main: '#EF4444',      // Red
    light: '#F87171',
    dark: '#DC2626',
  },
  warning: {
    main: '#F59E0B',      // Amber
    light: '#FBBF24',
    dark: '#D97706',
  },
  info: {
    main: '#3B82F6',      // Blue
    light: '#60A5FA',
    dark: '#2563EB',
  },
  success: {
    main: '#10B981',      // Green
    light: '#34D399',
    dark: '#059669',
  },
  background: {
    default: '#0F172A',   // Slate 900
    paper: '#1E293B',     // Slate 800
  },
  text: {
    primary: '#F1F5F9',   // Slate 100
    secondary: '#CBD5E1',  // Slate 300
    disabled: '#64748B',   // Slate 500
  },
  divider: alpha('#CBD5E1', 0.12),
};

// Typography configuration
const typography = {
  fontFamily: "'Inter', 'Roboto', 'Helvetica Neue', sans-serif",
  h1: {
    fontSize: '3rem',
    fontWeight: 700,
    letterSpacing: '-0.02em',
    lineHeight: 1.2,
  },
  h2: {
    fontSize: '2.25rem',
    fontWeight: 700,
    letterSpacing: '-0.01em',
    lineHeight: 1.3,
  },
  h3: {
    fontSize: '1.875rem',
    fontWeight: 600,
    lineHeight: 1.3,
  },
  h4: {
    fontSize: '1.5rem',
    fontWeight: 600,
    lineHeight: 1.4,
  },
  h5: {
    fontSize: '1.25rem',
    fontWeight: 500,
    lineHeight: 1.4,
  },
  h6: {
    fontSize: '1rem',
    fontWeight: 500,
    lineHeight: 1.5,
  },
  body1: {
    fontSize: '1rem',
    lineHeight: 1.6,
  },
  body2: {
    fontSize: '0.875rem',
    lineHeight: 1.5,
  },
  caption: {
    fontSize: '0.75rem',
    letterSpacing: '0.03em',
    lineHeight: 1.4,
  },
  button: {
    textTransform: 'none' as const,
    fontWeight: 500,
  },
};

// Create the theme
const theme = createTheme({
  palette,
  typography,
  spacing: 8,
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarWidth: 'thin',
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: palette.background.default,
          },
          '&::-webkit-scrollbar-thumb': {
            background: palette.text.disabled,
            borderRadius: '4px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: palette.text.secondary,
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: palette.background.paper,
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: `0 12px 24px ${alpha('#000000', 0.15)}`,
          },
        },
      },
      defaultProps: {
        elevation: 2,
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: palette.background.paper,
        },
      },
      defaultProps: {
        elevation: 1,
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          padding: '8px 16px',
          fontSize: '0.875rem',
          fontWeight: 500,
          transition: 'all 0.2s ease-in-out',
        },
        contained: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: `0 4px 12px ${alpha(palette.primary.main, 0.4)}`,
            transform: 'translateY(-1px)',
          },
        },
        outlined: {
          borderWidth: '1.5px',
          '&:hover': {
            borderWidth: '1.5px',
            backgroundColor: alpha(palette.primary.main, 0.08),
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
          fontSize: '0.75rem',
          height: '24px',
        },
        filled: {
          backgroundColor: alpha(palette.primary.main, 0.15),
          color: palette.primary.light,
          '&:hover': {
            backgroundColor: alpha(palette.primary.main, 0.25),
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            '& fieldset': {
              borderColor: alpha(palette.text.secondary, 0.23),
              borderWidth: '1.5px',
            },
            '&:hover fieldset': {
              borderColor: alpha(palette.primary.main, 0.5),
            },
            '&.Mui-focused fieldset': {
              borderColor: palette.primary.main,
              borderWidth: '2px',
            },
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottomColor: alpha(palette.divider, 0.08),
        },
        head: {
          fontWeight: 600,
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          letterSpacing: '0.05em',
          color: palette.text.secondary,
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: '4px',
          height: '6px',
          backgroundColor: alpha(palette.primary.main, 0.1),
        },
        bar: {
          borderRadius: '4px',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          '& .MuiAlert-icon': {
            fontSize: '22px',
          },
        },
        standardSuccess: {
          backgroundColor: alpha(palette.success.main, 0.15),
          color: palette.success.light,
          '& .MuiAlert-icon': {
            color: palette.success.light,
          },
        },
        standardError: {
          backgroundColor: alpha(palette.error.main, 0.15),
          color: palette.error.light,
          '& .MuiAlert-icon': {
            color: palette.error.light,
          },
        },
        standardWarning: {
          backgroundColor: alpha(palette.warning.main, 0.15),
          color: palette.warning.light,
          '& .MuiAlert-icon': {
            color: palette.warning.light,
          },
        },
        standardInfo: {
          backgroundColor: alpha(palette.info.main, 0.15),
          color: palette.info.light,
          '& .MuiAlert-icon': {
            color: palette.info.light,
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundImage: 'none',
          backgroundColor: palette.background.paper,
        },
      },
    },
    MuiAccordion: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: palette.background.paper,
          '&:before': {
            display: 'none',
          },
          '&.Mui-expanded': {
            margin: '16px 0',
          },
        },
      },
    },
    MuiSlider: {
      styleOverrides: {
        root: {
          '& .MuiSlider-thumb': {
            width: 20,
            height: 20,
            '&:hover, &.Mui-focusVisible': {
              boxShadow: `0 0 0 8px ${alpha(palette.primary.main, 0.16)}`,
            },
          },
          '& .MuiSlider-valueLabel': {
            backgroundColor: palette.primary.main,
            borderRadius: '4px',
          },
        },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        root: {
          width: 42,
          height: 26,
          padding: 0,
          '& .MuiSwitch-switchBase': {
            padding: 0,
            margin: 2,
            transitionDuration: '300ms',
            '&.Mui-checked': {
              transform: 'translateX(16px)',
              color: '#fff',
              '& + .MuiSwitch-track': {
                backgroundColor: palette.primary.main,
                opacity: 1,
                border: 0,
              },
            },
          },
          '& .MuiSwitch-thumb': {
            boxSizing: 'border-box',
            width: 22,
            height: 22,
          },
          '& .MuiSwitch-track': {
            borderRadius: 26 / 2,
            backgroundColor: alpha(palette.text.secondary, 0.3),
            opacity: 1,
          },
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: alpha(palette.background.default, 0.95),
          backdropFilter: 'blur(8px)',
          border: `1px solid ${alpha(palette.primary.main, 0.2)}`,
          fontSize: '0.75rem',
          padding: '8px 12px',
        },
        arrow: {
          color: alpha(palette.background.default, 0.95),
        },
      },
    },
  },
});

export default theme;

